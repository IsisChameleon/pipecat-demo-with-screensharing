# Voice UI Kit Client

A Next.js application showcasing screensharing with the Voice UI Kit and Gemini Live Multimodal model.

## Features

- **Real-time conversation** with Gemini via Pipecat
- **Screen sharing** (desktop) with resizable panels
- **Device controls** for camera, microphone, and speakers
- **Live transcripts** for both user and bot
- **Audio visualization** of bot responses
- **Event logs panel** with toggle and resize capabilities

## Quick Start

1. **Install dependencies**:

   ```bash
   npm install
   ```

2. **Configure environment**:

   ```bash
   cp env.example .env.local
   # Edit .env.local with your Daily room URL or Pipecat Cloud credentials
   ```

3. **Start development server**:

   ```bash
   npm run dev
   ```

4. **Open** [http://localhost:3000](http://localhost:3000) and click **Connect**

## Configuration

### Local Development

Set your Daily room URL in `.env.local`:

```bash
NEXT_PUBLIC_DAILY_ROOM_URL=https://your-daily-room.daily.co/your-room
```

### Pipecat Cloud Deployment

Set your agent credentials in `.env.local`:

```bash
PCC_START_URL=https://api.pipecat.daily.co/v1/public/<agent-name>/start
PCC_API_KEY=pk_your_api_key_here
```

## Usage

1. **Connect** to establish a session with the bot
2. **Select devices** using the dropdown menus
3. **Share screen** (desktop only) to let Gemini analyze your screen
4. **View transcripts** and **audio visualization** in real-time
5. **Toggle logs** and **resize panels** as needed

## Mobile Support

Screen sharing is disabled on mobile devices. A warning message will be displayed.

## Tech Stack

- **Next.js 15.5.4** with React 19.1.0
- **Pipecat Voice UI Kit** for real-time communication
- **Tailwind CSS 4** for styling
- **Lucide React** for icons
