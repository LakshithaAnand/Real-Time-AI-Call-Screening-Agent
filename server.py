from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
import json
import os
import base64
import asyncio
import websockets

DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&interim_results=true"
)

app = FastAPI()

DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]

# Reads the audio from twilio and transcribes it using Deepgram. The transcriptions are printed to the console.
async def read_deepgram(deepgram_websocket):
    # Runs concurrently with the Twilio loop, printing transcripts as they arrive.
    async for message in deepgram_websocket:
        response = json.loads(message)
        if response.get("type") != "Results":
            continue
        transcript = response["channel"]["alternatives"][0]["transcript"]
        if transcript:
            tag = "FINAL" if response.get("is_final") else "interim"
            print(f"[{tag}] {transcript}")

def log(call_sid, msg):
    print(f"Call SID: {call_sid} - {msg}")

@app.post("/voice")
async def voice_endpoint():
    # TwiML that tells Twilio to open a media stream to our /ws endpoint.
    # The wss host matches the current ngrok tunnel (and so should the Twilio webhook URL. Both should be the same.)
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response><Connect><Stream url="wss://sandbar-onboard-reorder.ngrok-free.dev/ws" /></Connect></Response>"""
    
    return Response(content=xml, media_type="application/xml")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    counter = 0
    stream_sid = None
    call_sid = None
    deepgram_websocket = None
    try:
        while True:
            data = await websocket.receive_text()
            json_data = json.loads(data)
            event_type = json_data.get("event")
            if event_type == "start":
                print("Start event received", json.dumps(json_data, indent=2))
                call_sid = json_data["start"]["callSid"]
                stream_sid = json_data["start"]["streamSid"]
                log(call_sid, "Call Started")

                # NEW: dial out to Deepgram and start listening to its replies
                deepgram_websocket = await websockets.connect(
                    DEEPGRAM_URL,
                    additional_headers={
                        "Authorization": f"Token {DEEPGRAM_API_KEY}"
                    },
                )
                asyncio.create_task(read_deepgram(deepgram_websocket))

            elif event_type == "media":
                # Twilio sends ~50 media frames/sec of base64-encoded 8kHz mu-law audio, 20ms each.
                counter += 1
                if counter % 50 == 0: 
                    print(f"Media frames count received: {counter}")
                    log(call_sid, f"{counter} frames")
                json_media = json_data["media"]
                payload = json_media["payload"]

                 # Twilio gives base64 text and Deepgram wants the raw bytes so we decode it first.
                if deepgram_websocket:
                    await deepgram_websocket.send(base64.b64decode(payload))

            elif event_type == "stop":
                print("Event stop")
                log(call_sid, "stop")
                break
            else:
                print(f"Event: {event_type}") 
    except WebSocketDisconnect:
        print("WebSocket disconnected")

    finally:
        if deepgram_websocket:
            await deepgram_websocket.close()   # hang up the Deepgram line too



