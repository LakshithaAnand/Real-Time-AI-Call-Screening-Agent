from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
import json
app = FastAPI()

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
    try:
        while True:
            data = await websocket.receive_text()
            json_data = json.loads(data)
            event_type = json_data.get("event")
            if event_type == "start":
                print("Start event received", json.dumps(json_data, indent=2))
                call_sid = json_data["start"]["callSid"]
                log(call_sid, "Start event received")
                stream_sid = json_data["start"]["streamSid"]
            elif event_type == "media":
                # Twilio sends ~50 media frames/sec of base64-encoded 8kHz mu-law audio, 20ms each.
                counter += 1
                if counter % 50 == 0: 
                    print(f"Media frames count received: {counter}")
                    log(call_sid, f"{counter} frames")
                json_media = json_data["media"]
                payload = json_media["payload"]

                # Echo the caller's audio back to test the full pipeline.
                # streamSid is required so Twilio knows which call stream to play it on.
                outbound_message = {
                    "event": "media", 
                    "streamSid": stream_sid,
                    "media": {
                        "payload": payload
                    }
                }
                await websocket.send_text(json.dumps(outbound_message)) 
            elif event_type == "stop":
                print("Event stop")
                log(call_sid, "stop")
                break
            else:
                print(f"Event: {event_type}") 
    except WebSocketDisconnect:
        print("WebSocket disconnected")
        