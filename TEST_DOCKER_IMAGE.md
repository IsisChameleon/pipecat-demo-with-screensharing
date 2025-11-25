# Testing Docker Image Locally

This guide explains how to test the `isischameleon/pipecat-demo-with-screensharing:latest` Docker image locally.

Not sure how good this is - complete LLM work. notes.md is where I put my notes.

## Prerequisites

- Docker installed and running
- A Daily.co account with API key
- A Google Gemini API key
- A Daily room URL (optional, for testing with a specific room)

## Step 1: Pull the Docker Image

```bash
docker pull isischameleon/pipecat-demo-with-screensharing:latest
```

Or if you need to build it locally:

```bash
cd server
docker build -t isischameleon/pipecat-demo-with-screensharing:latest .
```

## Step 2: Prepare Environment Variables

Create a `.env` file in the `server/` directory (or use your existing one) with:

```bash
DAILY_API_KEY=your_daily_api_key
GOOGLE_API_KEY=your_google_gemini_api_key
DAILY_SAMPLE_ROOM_URL=https://yourdomain.daily.co/yourroom  # Optional
DAILY_SAMPLE_ROOM_TOKEN=your_room_token                     # Optional
```

## Step 3: Run the Docker Container

**IMPORTANT**: You must expose port **7860** so the front-end can connect to the bot's FastAPI server.

Run the container with port forwarding and environment variables:

```bash
docker run -it --rm \
  -p 7860:7860 \
  --env-file server/.env \
  -e HOST=0.0.0.0 \
  isischameleon/pipecat-demo-with-screensharing:latest \
  python bot.py --transport daily
```

Or pass environment variables directly:

```bash
docker run -it --rm \
  -p 7860:7860 \
  -e HOST=0.0.0.0 \
  -e DAILY_API_KEY=your_daily_api_key \
  -e GOOGLE_API_KEY=your_google_gemini_api_key \
  -e DAILY_SAMPLE_ROOM_URL=https://yourdomain.daily.co/yourroom \
  isischameleon/pipecat-demo-with-screensharing:latest \
  python bot.py --transport daily
```

**Important**: The `HOST=0.0.0.0` environment variable tells the FastAPI/Uvicorn server to bind to all network interfaces, allowing connections from outside the container. Without this, the server binds to `localhost` and won't accept external connections.

**Note**: The `-p 7860:7860` flag maps port 7860 from the container to port 7860 on your host machine. This allows your front-end (running on `localhost:3000`) to connect to the bot's API at `http://localhost:7860/start`.

## Step 4: Connect to Daily Room

The bot will start and wait for connections. You can:

1. **Use the client app** (recommended):
   ```bash
   cd client
   npm install
   npm run dev
   ```
   Then open `http://localhost:3000` and connect to your Daily room.

2. **Join via Daily.co dashboard**: Navigate to your Daily room URL and join as a participant.

## Step 5: Test Screen Sharing

Once connected:
- Share your screen using the Daily interface
- The bot will analyze the screen content using Gemini's multimodal capabilities
- Have a conversation with the bot

## Troubleshooting

### Container exits immediately
- Check that all required environment variables are set
- Verify API keys are valid
- Check Docker logs: `docker logs <container_id>`

### Front-end can't connect to bot
- **Most common issue**: Make sure port 7860 is forwarded with `-p 7860:7860`
- **Critical**: Set `HOST=0.0.0.0` environment variable so the server binds to all interfaces (not just localhost)
- Verify the bot container is running: `docker ps`
- Check if port 7860 is accessible: `curl -X POST http://localhost:7860/start -H "Content-Type: application/json" -d '{"createDailyRoom": true}'` (should return JSON, not "Empty reply")
- Check Docker logs for errors: `docker logs <container_id>`
- Verify server is binding correctly: logs should show `Uvicorn running on http://0.0.0.0:7860` (not `localhost:7860`)

### Bot doesn't connect to room
- Verify `DAILY_API_KEY` is correct
- Check that `DAILY_SAMPLE_ROOM_URL` is set if using a specific room
- Ensure the room exists and is accessible

### Screen sharing not working
- Verify the bot is using the `agent-2x` profile (for video processing)
- Check that video capture is enabled in Daily room settings
- Ensure you're sharing screen via Daily's interface

### View container logs
```bash
# If running in detached mode
docker logs -f <container_id>

# Or run interactively to see logs directly
docker run -it --rm --env-file server/.env isischameleon/pipecat-demo-with-screensharing:latest python bot.py --transport daily
```

## Advanced: Run with Additional Options

### Enable tracing (OpenTelemetry)
```bash
docker run -it --rm \
  -p 7860:7860 \
  --env-file server/.env \
  -e HOST=0.0.0.0 \
  -e ENABLE_TRACING=true \
  -e OTLP_ENDPOINT=http://host.docker.internal:4317 \
  isischameleon/pipecat-demo-with-screensharing:latest \
  python bot.py --transport daily
```

### Run in detached mode
```bash
docker run -d --name pipecat-bot \
  -p 7860:7860 \
  --env-file server/.env \
  -e HOST=0.0.0.0 \
  isischameleon/pipecat-demo-with-screensharing:latest \
  python bot.py --transport daily
```

### Stop detached container
```bash
docker stop pipecat-bot
docker rm pipecat-bot
```

