# Running locally

Don't forget to check .env.local to see if this local front-end is pointing at your local or
at the pipecat cloud

```
# The localhost address will allow you to run locally.
# You can deploy to Pipecat Cloud by setting the BOT_START_URL
# to your agent and then also provide your Pipecat Cloud API key.
BOT_START_URL="http://localhost:7860/start"
BOT_START_PUBLIC_API_KEY=""

# WHen you want to point your localhost client to Pipecat CLoud

# BOT_START_URL="https://api.pipecat.daily.co/v1/public/pipecat-quarterzip/start"
# BOT_START_PUBLIC_API_KEY="pk_c7408073-19fc-4b49-b9f6-e58e3fcdfc16"
```

https://docs.pipecat.ai/getting-started/quickstart
uv run bot.py --transport daily 

```
isabelleredactive@Mac server % uv run ./src/bot.py
2025-11-25 14:42:51.636 | INFO     | pipecat:<module>:14 - ᓚᘏᗢ Pipecat 0.0.90 (Python 3.13.6 (main, Aug 14 2025, 16:07:26) [Clang 20.1.4 ]) ᓚᘏᗢ
2025-11-25 14:43:11.246 | INFO     | __main__:<module>:28 - Loading Local Smart Turn Analyzer V3...
None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
2025-11-25 14:43:12.756 | INFO     | __main__:<module>:31 - ✅ Local Smart Turn Analyzer V3 loaded
2025-11-25 14:43:12.756 | INFO     | __main__:<module>:32 - Loading Silero VAD model...
2025-11-25 14:43:12.757 | INFO     | __main__:<module>:35 - ✅ Silero VAD model loaded
/Users/isabelleredactive/src/pipecat-demo-with-screensharing/server/.venv/lib/python3.13/site-packages/pydub/utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
  warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)

🚀 Bot ready!
   → Open http://localhost:7860/client in your browser

Looking for dist directory at: /Users/isabelleredactive/src/pipecat-demo-with-screensharing/server/.venv/lib/python3.13/site-packages/pipecat_ai_small_webrtc_prebuilt/client/dist
2025-11-25 14:43:31.184 | DEBUG    | pipecat.runner.run:_setup_whatsapp_routes:318 - Missing required environment variables for WhatsApp transport. Keeping it disabled.
INFO:     Started server process [28445]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:7860 (Press CTRL+C to quit)
```


# Deployment with Pipecat Cloud


## login to dockerhub

`docker login`

...

## Configure pcc-deploy.toml

```
agent_name = "pipecat-quarterzip"
image = "isischameleon/pipecat-demo-with-screensharing:0.1"
secret_set = "pipecat-demo-with-screensharing-secrets"
agent_profile = "agent-2x"
enable_krisp = true

[scaling]
	min_agents = 1
```

## Login to pcc 

 uv run pcc auth login

## Add secrets (using the secrets set name from toml file)

! don't put comments in your .env file it creates weird stuff when imported as secrets

uv run pcc secrets set  pipecat-demo-with-screensharing-secrets --file .env

```
(gemini-screen-ui-kit) isabelleredactive@Mac server % uv run pcc secrets set  pipecat-demo-with-screensharing-secrets --file .env
2025-11-23 11:45:53.838 | INFO     | pipecat:<module>:14 - ᓚᘏᗢ Pipecat 0.0.90 (Python 3.13.6 (main, Aug 14 2025, 16:07:26) [Clang 20.1.4 ]) ᓚᘏᗢ
╭─ Secrets to create / modify in set ──────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                  │
│   Key                       Value Preview                                                                                        │
│  ─────────────────────────────────────────                                                                                       │
│   DAILY_SAMPLE_ROOM_URL     https...                                                                                             │
│   DAILY_SAMPLE_ROOM_TOKEN   9c8.....                                                                                             │
│   DAILY_API_KEY             ba252...                                                                                             │
│   GOOGLE_API_KEY            AIzaS...                                                                                             │
│   OPENAI_API_KEY            sk-pr...                                                                                             │
│   CARTESIA_API_KEY          sk_ca...                                                                                             │
│                                                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
? Would you like to proceed with these secrets? Yes
╭─ ᓚᘏᗢ Success ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Secret set 'pipecat-demo-with-screensharing-secrets' created successfully                                                        │
│ Deploy your agent with pcc deploy agent-name --secrets pipecat-demo-with-screensharing-secrets                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Build your agent Dockerfile

```
(gemini-screen-ui-kit) isabelleredactive@Mac server % uv run pcc docker build-push
2025-11-23 11:48:34.026 | INFO     | pipecat:<module>:14 - ᓚᘏᗢ Pipecat 0.0.90 (Python 3.13.6 (main, Aug 14 2025, 16:07:26) [Clang 20.1.4 ]) ᓚᘏᗢ
╭─ Docker Build Configuration ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Agent: pipecat-demo-with-screensharing                                                                                                                                                         │
│ Platform: linux/arm64                                                                                                                                                                          │
│ Tags: isischameleon/pipecat-demo-with-screensharing:0.1, isischameleon/pipecat-demo-with-screensharing:latest                                                                                  │
│ Push: Yes (dockerhub)                                                                                                                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Do you want to proceed with the build? [Y/n]: Y

...
Successfully built image(s): isischameleon/pipecat-demo-with-screensharing:0.1, isischameleon/pipecat-demo-with-screensharing:latest   
```

## Test Dockerfile locally

From root of repo:

```
docker run -it --rm \
  -p 7860:7860 \
  --env-file server/.env \
  isischameleon/pipecat-demo-with-screensharing:latest \
  python bot.py --transport daily 
```

## Deploy to Pipecat Cloud

```
(gemini-screen-ui-kit) isabelleredactive@Mac server % pcc deploy pipecat-quarterzip --secrets pipecat-demo-with-screensharing-secrets 
2025-11-23 11:57:22.812 | INFO     | pipecat:<module>:14 - ᓚᘏᗢ Pipecat 0.0.90 (Python 3.13.6 (main, Aug 14 2025, 16:07:26) [Clang 20.1.4 ]) ᓚᘏᗢ
╭─ ᓚᘏᗢ Error - Attempt to deploy without repository credentials ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Deployments require an image pull secret (--credentials) to securely pull images from private repositories.                                                                                                              │
│ Please provide an image pull secret name or use [--no-credentials] to deploy without one.                                                                                                                                │
╰─ Learn more:https://docs.pipecat.daily.co/agents/secrets#image-pull-secrets ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Actually: https://docs.pipecat.ai/deployment/pipecat-cloud/fundamentals/secrets#image-pull-secrets

`pcc deploy pipecat-quarterzip --secrets pipecat-demo-with-screensharing-secrets --no-credentials`

deployment ID: 7f729bc2-c5f6-4805-9ee4-d3ab3e26988c

Deployment:
│ Agent name: pipecat-quarterzip                                                          
│ Image: isischameleon/pipecat-demo-with-screensharing:0.1     
│ Organization: stormy-badger-olive-971         
│ Secret set:  pipecat-demo-with-screensharing-secrets      
│ Image pull secret:    None   
│ Agent profile: agent-2x    
│ Krisp: Enabled   
│ Managed Keys: Disabled   

`Deployment did not enter ready state within 90 seconds. Please check logs with `pcc agent logs pipecat-quarterzip`

Problemn revealed by logs - missing source code in Dockerfile

--> Tried again, tested docker locally first

Updating deployment for agent 'pipecat-quarterzip'
╭─ ᓚᘏᗢ Success - Update complete ─────────────────────────────────────────────────────────────────────────────╮
│ Agent deployment 'pipecat-quarterzip' is ready        │
│    │
│ Start a session with your new agent by running: 
│ `pcc agent start pipecat-quarterzip` │
│ Note: if you have not already created a public API key (required to start a session), you can do so by running:   
│ `pcc organizations keys create`  


