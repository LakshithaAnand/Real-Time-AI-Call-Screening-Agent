from fastapi import FastAPI, Response
app = FastAPI()

@app.post("/voice")
async def voice_endpoint():
    # Set the response content type to audio/mpeg
    
    # Here you would generate or retrieve your audio data
    # For demonstration, we'll just return a simple byte string
    xml = """<?xml version="1.0" encoding="UTF-8"?>
   <Response><Say>Hey, this is my AI twin. It is alive.</Say></Response>"""
    
    return Response(content=xml, media_type="application/xml")
