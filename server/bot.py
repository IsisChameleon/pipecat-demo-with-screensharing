#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Gemini Bot Implementation.

This module implements a chatbot using Google's Gemini Multimodal Live model.
It includes:

- Real-time audio/video interaction
- Screen sharing analysis for location guessing
- Speech-to-speech model with visual reasoning

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow using Gemini's streaming capabilities.
"""

import os

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
from pipecat.frames.frames import (
    LLMRunFrame,
)
from pipecat.observers.loggers.transcription_log_observer import TranscriptionLogObserver
from pipecat.observers.loggers.user_bot_latency_log_observer import UserBotLatencyLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.stt import CartesiaLiveOptions as LiveOptions
from pipecat.services.cartesia.stt import CartesiaSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, InputParams
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.utils.tracing.setup import setup_tracing

from prompt import thriday

load_dotenv(override=True)

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

SYSTEM_INSTRUCTION = f"""
You are Gemini, and your task is to guess the location (city) of the map I am sharing.
I will screen-share Google Maps without labels and progressively zoom out.
At each zoom level::

1) Give your single best guess of the location (city) of the map.
2) Explain WHY using only visual cues.
3) End with a punchy line like: “I'd drop my pin in Madrid, Spain!”

Keep it concise. If uncertain, commit to your best guess anyway.
When I zoom again, update your guess and reasoning.
When I confirm your guess, celebrate with a punchy line!

When you're wrong you're allowed to ask for a hint.

When the conversation starts, introduce yourself very briefly and summarize your task really briefly.
"""


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Gemini Live multimodal model integration
    - Voice activity detection
    - RTVI event handling
    """
    

    # Initialize the Gemini Multimodal Live model
    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice_id="Charon",  # Aoede, Charon, Fenrir, Kore, Puck
        system_instruction=thriday,
        params=InputParams(thinking=ThinkingConfig(thinking_budget=0)),
    )

    messages = [
        {
            "role": "user",
            "content": "Start by introducing yourself, asking the user to share their screen to start.",
        },
    ]

    # Set up conversation context and management
    # The context aggregator will automatically collect conversation context
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            context_aggregator.user(),
            llm,
            transport.output(),
            context_aggregator.assistant(),
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

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    # Krisp is available when deployed to Pipecat Cloud
    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_filter import KrispFilter

        krisp_filter = KrispFilter()
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
