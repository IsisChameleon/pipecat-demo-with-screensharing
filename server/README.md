# Gemini Bot Server

A Pipecat server implementing Google's Gemini Live Multimodal model for real-time conversation with screen sharing capabilities.

## Features

- **Gemini Live Multimodal** integration with native audio
- **Screen sharing analysis** - bot can see and analyze shared screens
- **Real-time conversation** with voice activity detection
- **RTVI events** for client UI integration
- **Daily transport** for WebRTC communication

## Quick Start

1. **Configure environment**:

   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

2. **Install dependencies** (using local `.venv`):

   ```bash
   # Option 1: Use the helper script (recommended if UV_PROJECT_ENVIRONMENT is set globally)
   ./uv-local.sh sync

   # Option 2: Unset UV_PROJECT_ENVIRONMENT and use uv directly
   unset UV_PROJECT_ENVIRONMENT && uv sync

   # Option 3: If using direnv, it will auto-configure (see .envrc)
   direnv allow && uv sync
   ```

3. **Run the bot**:
   ```bash
   # Use the same approach as above
   ./uv-local.sh run bot.py --transport daily
   # OR
   unset UV_PROJECT_ENVIRONMENT && uv run bot.py --transport daily
   ```

## Required API Keys

Set these in your `.env` file:

```ini
DAILY_API_KEY=your_daily_api_key
GOOGLE_API_KEY=your_google_gemini_api_key
```

### Optional Configuration

```ini
DAILY_SAMPLE_ROOM_URL=https://yourdomain.daily.co/yourroom  # For local dev
DAILY_SAMPLE_ROOM_TOKEN=your_room_token                     # If room requires token
```

## Bot Behavior

The bot is configured to:

- **Analyze shared screens** and guess locations on Google Maps
- **Provide visual reasoning** based on screen content
- **Engage in natural conversation** with voice responses
- **Handle real-time audio/video** streams

## Deployment

This bot is configured for Pipecat Cloud deployment with:

- **agent-2x profile** (required for video processing)
- **Docker containerization**
- **Automatic scaling** configuration

See the main README for deployment instructions.

## Troubleshooting

### SSL Certificate Error (macOS)

If you see SSL certificate errors, install certificates:

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### Dependencies

This bot requires Python 3.10+ and uses `uv` for dependency management.

### Local Virtual Environment

This project is configured to use a local `.venv` directory to avoid conflicts with global `uv` configurations (like those in devcontainers). 

- **Helper script**: Use `./uv-local.sh` instead of `uv` to ensure local venv usage
- **direnv**: If you use direnv, run `direnv allow` to auto-configure
- **Manual**: Unset `UV_PROJECT_ENVIRONMENT` before running `uv` commands:
  ```bash
  unset UV_PROJECT_ENVIRONMENT
  uv sync
  ```
