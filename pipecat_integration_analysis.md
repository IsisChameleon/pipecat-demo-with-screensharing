# Pipecat UI Kit Integration Analysis

This document details how the Pipecat UI kit wires up user audio and screen sharing to the AI agent in the `pipecat-demo-with-screensharing` repository.

## 1. Components Involved

The integration relies on a set of components from `@pipecat-ai/voice-ui-kit` on the frontend and the Pipecat SDK on the backend.

### Frontend (Client)
*   **`PipecatAppBase`** (`client/app/page.tsx`): The top-level provider that initializes the `VoiceClient` and handles the connection logic. It wraps the application and manages the transport (Daily).
*   **`ClientApp`** (`client/app/ClientApp.tsx`): The main UI component that uses hooks to interact with the client state.
*   **`UserAudioControl`**: A pre-built component that manages the user's microphone input, mute state, and visualizer.
*   **`UserScreenControl`**: A pre-built component that triggers the browser's screen sharing dialog (`getDisplayMedia`) and manages the screen share track.
*   **`PipecatClientVideo`**: A component used to render video tracks. It is used to display the user's screen share locally (`trackType="screenVideo"`).
*   **`Conversation`**: Displays the transcript of the conversation.

### Backend (Server)
*   **`bot.py`** (`server/src/bot.py`): The main entry point for the Python bot. It defines the Pipecat pipeline.
*   **`DailyParams`**: Configures the Daily transport, enabling audio/video input and output.
*   **`GeminiLiveLLMService`**: The LLM service (Gemini Multimodal Live) that consumes the audio and video streams.

## 2. How It Works (The Wiring)

The system uses **WebRTC** (via Daily.co) to transmit media. Here is the step-by-step flow:

### A. Connection Establishment
1.  **Frontend**: The `PipecatAppBase` calls the `/api/start` endpoint.
2.  **Backend**: The `/api/start` endpoint proxies a request to the local bot server (`http://localhost:7860/start`), which creates a Daily room and returns the room URL and token.
3.  **Frontend**: `PipecatAppBase` uses these credentials to connect the `VoiceClient` to the Daily room.

### B. Audio Wiring
1.  **User -> Agent**:
    *   The `UserAudioControl` component automatically manages the local microphone track.
    *   When the user joins, this audio track is published to the Daily room.
    *   **Backend**: The bot's transport is configured with `audio_in_enabled=True`. The `GeminiLiveLLMService` in the pipeline receives this audio stream as part of its multimodal input.

### C. Screen Sharing Wiring
1.  **User -> Agent**:
    *   When the user clicks the `UserScreenControl` button, it triggers the browser's screen selection dialog.
    *   The selected screen track is published to the Daily room with a specific track name/tag (typically handled as a "screenVideo" track).
2.  **Agent Subscription (CRITICAL STEP)**:
    *   The bot does *not* automatically see the screen. It must explicitly subscribe to it.
    *   In `server/src/bot.py`, there is an event handler for `on_client_connected`:
        ```python
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, participant):
            # ...
            await transport.capture_participant_video(participant["id"], 1, "screenVideo")
        ```
    *   This code tells the bot to subscribe to the `screenVideo` track of the connected participant.
    *   The video frames are then passed down the pipeline to the `GeminiLiveLLMService`, which analyzes them.

## 3. Events and Callbacks

### Frontend Hooks & Events
*   **`usePipecatClient`**: Provides access to the underlying `VoiceClient` instance.
*   **`usePipecatClientScreenShareControl`**: A hook that exposes `isScreenShareEnabled` state and `toggleScreenShare` function.
*   **`usePipecatConnectionState`**: Tracks whether the client is connected, connecting, or disconnected.
*   **`RTVIEvent`**: The client listens for Real-Time Voice Interface (RTVI) events for coordination (e.g., knowing when the bot is ready).

### Backend Event Handlers (`bot.py`)
*   **`on_client_connected`**:
    *   **Trigger**: Fired when a user joins the Daily room.
    *   **Action**: The bot explicitly calls `capture_participant_video` for both `"camera"` and `"screenVideo"`. This is the "handshake" that enables the vision capabilities.
*   **`on_client_ready`**:
    *   **Trigger**: Fired when the RTVI client reports it is ready.
    *   **Action**: The bot sets itself as ready and queues the initial `LLMRunFrame` to start the conversation.

## Summary for Your `toocan-app` Implementation

To connect your app to a Pipecat cloud agent:

1.  **Frontend**: Use `PipecatAppBase` (or manually setup `VoiceClient` with `DailyTransport`). Ensure you have `UserScreenControl` or a custom button that calls `voiceClient.enableScreenShare(true)`.
2.  **Backend**: Ensure your Pipecat bot has an `on_client_connected` handler that calls `transport.capture_participant_video(participant_id, framerate, "screenVideo")`. Without this, the agent will be in the room but won't "see" the screen.
