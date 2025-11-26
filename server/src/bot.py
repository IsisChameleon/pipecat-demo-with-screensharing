#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Gemini Bot Implementation.

This module implements a chatbot using Google's Gemini 2.5 Flash model with
ElevenLabs STT/TTS services in a cascaded pipeline.
It includes:

- Real-time audio/video interaction
- Screen sharing analysis for location guessing
- Cascaded speech-to-speech pipeline (STT -> LLM -> TTS)

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow using Gemini's text-based LLM capabilities.
"""

import os
import time
import aiohttp

from dotenv import load_dotenv
from google.genai.types import ThinkingConfig
from loguru import logger
from pipecat.services.openai.llm import OpenAILLMService

logger.info("Loading Local Smart Turn Analyzer V3...")
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

logger.info("✅ Local Smart Turn Analyzer V3 loaded")
logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, InputImageRawFrame
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.stt import CartesiaLiveOptions as LiveOptions
from pipecat.services.cartesia.stt import CartesiaSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.elevenlabs.stt import ElevenLabsSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, InputParams
from pipecat.services.google.llm import GoogleLLMContext, GoogleLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.utils.tracing.setup import setup_tracing

from prompt import latest_prompt

load_dotenv(override=True)


class ScreenFrameToContext(FrameProcessor):
    """Samples incoming screen frames and injects them into the LLM context."""

    def __init__(
        self,
        *,
        context: OpenAILLMContext,
        source_name: str = "screenVideo",
        min_interval: float = 1.0,
        caption: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._context = context
        self._source = source_name
        self._min_interval = max(min_interval, 0.1)
        self._caption = caption or "Latest shared screen"
        self._last_emit = 0.0
        self._last_image_index: int | None = None
        self._first_frame_sent = False

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        is_screen_frame = (
            isinstance(frame, InputImageRawFrame)
            and frame.transport_source == self._source
            and frame.size
            and frame.image
        )

        if is_screen_frame:
            now = time.monotonic()
            if now - self._last_emit >= self._min_interval:
                frame_format = frame.format or "RGB"
                try:
                    if self._last_image_index is not None:
                        try:
                            self._context.messages.pop(self._last_image_index)
                        except IndexError:
                            logger.debug("Previous screen frame index invalid; resetting")
                        finally:
                            self._last_image_index = None

                    kickoff_frame = not self._first_frame_sent
                    frame_text = (
                        "You can now finally see the user's screen. Please acknowledge and describe the screenshot."
                        if kickoff_frame
                        else self._caption
                    )

                    self._context.add_image_frame_message(
                        format=frame_format,
                        size=frame.size,
                        image=frame.image,
                        text=frame_text,
                    )
                    if kickoff_frame:
                        self._first_frame_sent = True
                        await self.push_frame(LLMRunFrame(), FrameDirection.DOWNSTREAM)
                    self._last_image_index = len(self._context.messages) - 1
                    self._last_emit = now
                    logger.debug(
                        "Captured screen frame (%s, %s) for LLM context",
                        frame_format,
                        frame.size,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to capture screen frame for context: {exc}")

        await self.push_frame(frame, direction)

# Initialize OpenTelemetry tracing if enabled
# Traces will be sent to your OTEL collector (default: localhost:4317)
# The collector should be configured to export traces to your observability backend
# Metrics are logged via UserBotLatencyLogObserver and can also be exported via OTEL collector
if os.getenv("ENABLE_TRACING", "false").lower() == "true":
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    # Default endpoint matches standard OTEL collector gRPC port
    # If your collector uses HTTP/protobuf, change to port 4318
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    console_export = os.getenv("OTLP_CONSOLE_EXPORT", "false").lower() == "true"

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    setup_tracing(
        service_name="pipecat-quarterzip",
        exporter=exporter,
        console_export=console_export,
    )
    logger.info(f"OpenTelemetry tracing enabled (endpoint: {otlp_endpoint})")
    logger.info("Traces will be collected by OTEL collector and can be viewed in Grafana/Jaeger")


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - ElevenLabs STT/TTS services
    - Gemini 2.5 Flash LLM
    - Voice activity detection
    - RTVI event handling
    """

    stt = CartesiaSTTService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        live_options=LiveOptions(
            model="ink-whisper", language=Language.EN, smart_format=True
        ),
    )

    
    # Initialize aiohttp session for ElevenLabs and other services
    # Try different voices by uncommenting a voice_id below:
    # voice_id="41f3c367-e0a8-4a85-89e0-c27bae9c9b6d"  # Australian Customer Support Man (current)
    # voice_id="694f9389-aac1-45b6-b726-9d9369183238"  # British Customer Support Woman
    # voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22"  # American Professional Woman
    # voice_id="a0e99841-438c-4a64-b679-ae501e7d6091"  # Conversational American Man
    # voice_id="95856005-0332-41b0-935f-352e296aa0df"  # Friendly American Woman
    # voice_id="fb26447f-308b-471e-8b00-8e9f04284eb5"  # Calm British Man
    voice_id="421b3369-f63f-4b03-8980-37a44df1d4e8"  # Warm Australian Woman
    # voice_id="726d5ae5-055f-4c3d-8355-d9677de68937"  # Professional Indian Man
    #
    # For voice cloning, you can clone any voice using Cartesia's voice cloning feature.
    # Visit https://play.cartesia.ai to clone voices and get custom voice IDs.

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="41f3c367-e0a8-4a85-89e0-c27bae9c9b6d",  # Australian Customer Support Man
    )


    # Initialize Gemini 2.5 Flash LLM
    llm = GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-2.5-flash",
        system_instruction=latest_prompt,
    )


    messages = [
        {
            "role": "user",
            "content": "Hi! How are you?",
        },
    ]

    # Set up conversation context and management
    # The context aggregator will automatically collect conversation context
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    try:
        screen_frame_interval = float(os.getenv("SCREEN_FRAME_INTERVAL_SECS", "1.0"))
    except ValueError:
        screen_frame_interval = 1.0

    screen_sampler = ScreenFrameToContext(
        context=context,
        source_name="screenVideo",
        min_interval=screen_frame_interval,
    )

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))


    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            screen_sampler,  # Sample screen frames into LLM context
            rtvi,
            stt,  # ElevenLabs STT
            context_aggregator.user(),  # User responses
            llm,  # Gemini 2.5 Flash LLM
            tts,  # ElevenLabs TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    # Set up observers for debugging and monitoring
    observers = [RTVIObserver(rtvi)]
    
    # Add transcription log observer to see what's being transcribed
    if os.getenv("ENABLE_TRANSCRIPTION_LOGS", "true").lower() == "true":
        observers.append(TranscriptionLogObserver())
        logger.info("Transcription logging enabled")
    
    # Add latency observer to see performance metrics (user stopped -> bot started speaking)
    if os.getenv("ENABLE_METRICS_LOGS", "true").lower() == "true":
        observers.append(UserBotLatencyLogObserver())
        logger.info("Latency metrics logging enabled")

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=observers,
        enable_tracing=os.getenv("ENABLE_TRACING", "false").lower() == "true",
        enable_turn_tracking=os.getenv("ENABLE_TRACING", "false").lower() == "true",
        conversation_id="1234567890",
        additional_span_attributes={"username": "isabelle"}

    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        # Start the conversation with initial message
        await task.queue_frames([LLMRunFrame()])

    # screen_share_state: dict[str, str] = {}

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        logger.info(f"Client connected")
        await transport.capture_participant_video(participant["id"], 1, "camera")
        await transport.capture_participant_video(participant["id"], 1, "screenVideo")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    logger.info("Running pipeline with PipelineParams: ", task.params)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    # Krisp is available when deployed to Pipecat Cloud
    logger.info(f"Starting bot with ENV: {os.environ.get('ENV')}, runner args: {runner_args}")
    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter

        krisp_filter = KrispVivaFilter()
        logger.info("✅ Krisp filter enabled!")
    else:
        krisp_filter = None

    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_in_filter=krisp_filter,
            audio_out_enabled=True,
            video_in_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        )
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
