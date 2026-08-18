# Real-Time-AI-Call-Screening-Agent

A work-in-progress agent that answers your phone calls and screens them in real time.
Current status: 
**live transcription working** — call the Twilio number, speak, and see your words appear in the terminal within a fraction of a second.

## How it works

```
Caller ──► Twilio ──► ngrok tunnel ──► FastAPI server (this repo) ──► Deepgram
                                              ▲                          │
                                              └── live transcripts ◄─────┘
```

1. A caller dials the Twilio number. Twilio POSTs to `/voice` (via the ngrok URL set as the webhook) asking what to do with the call.
2. `/voice` replies with TwiML telling Twilio to open a media stream to `/ws`.
3. Twilio opens a WebSocket and sends the caller's audio as ~50 frames/sec of
   base64-encoded 8kHz mu-law.
4. On the `start` event, the server opens a **second** WebSocket to Deepgram's
   live-streaming API and forwards every decoded audio frame to it.
5. A background task (`asyncio.create_task`) reads Deepgram's responses
   concurrently and prints interim and final transcripts as the caller speaks.
6. On `stop` (caller hangs up), both sockets are closed cleanly.

## Setup

Requirements: Python 3.13, a Twilio number, a Deepgram API key, ngrok.

```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn websockets
```

Config:
- Put `export DEEPGRAM_API_KEY="..."` in `~/.zshrc` (never in the code).
- Start ngrok on port 8080; set the Twilio voice webhook to
  `https://<your-ngrok-host>/voice` and update the `wss://` URL in the TwiML
  in `server.py` to the same host.

Run:
```bash
uvicorn server:app --reload --port 8080
```

## Results from this run

From a real call:

```
[interim] what are you doing
[FINAL] what are you doing
[FINAL] socket connection to deepgram
```

Latency is sub-second. Accuracy is good but not perfect on 8kHz phone audio
("WebSocket" came through as "helios socket") — switching to Deepgram's
phone-call-tuned model is a likely improvement.
