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

import argparse
import os
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from google.genai.types import ThinkingConfig
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    LLMRunFrame,
)
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

from prompt import thriday

load_dotenv(override=True)

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
    stt = CartesiaSTTService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        live_options=LiveOptions(
            model="ink-whisper", language=Language.EN, smart_format=True
        ),
    )

    # Try different voices by uncommenting a voice_id below:
    # voice_id="41f3c367-e0a8-4a85-89e0-c27bae9c9b6d"  # Australian Customer Support Man (current)
    # voice_id="694f9389-aac1-45b6-b726-9d9369183238"  # British Customer Support Woman
    # voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22"  # American Professional Woman
    # voice_id="a0e99841-438c-4a64-b679-ae501e7d6091"  # Conversational American Man
    # voice_id="95856005-0332-41b0-935f-352e296aa0df"  # Friendly American Woman
    # voice_id="fb26447f-308b-471e-8b00-8e9f04284eb5"  # Calm British Man
    # voice_id="421b3369-f63f-4b03-8980-37a44df1d4e8"  # Warm Australian Woman
    # voice_id="726d5ae5-055f-4c3d-8355-d9677de68937"  # Professional Indian Man
    #
    # For voice cloning, you can clone any voice using Cartesia's voice cloning feature.
    # Visit https://play.cartesia.ai to clone voices and get custom voice IDs.

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="41f3c367-e0a8-4a85-89e0-c27bae9c9b6d",  # Australian Customer Support Man
    )

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

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
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
