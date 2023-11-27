from http import client
import os
import json
import websockets
import openai
import requests
import asyncio
from dotenv import load_dotenv

from pydub import AudioSegment
from pydub.playback import play
from deepgram import Deepgram
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai._base_client import HttpxBinaryResponseContent

app = FastAPI()

load_dotenv()

# Mount the directory containing your static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def home() -> FileResponse:
    return FileResponse("frontend/index.html")


async def say_to_ai(
    text: str,
) -> bytes:
    ## pass user input to an LLM

    PROMPT_MESSAGES = [
        {"role": "system", "content": "You are Roger Federer"},
        {"role": "user", "content": text},
    ]

    result = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=PROMPT_MESSAGES, max_tokens=300  # type: ignore
    )
    result_text = result.choices[0].message.content

    url = "https://api.play.ht/api/v2/cloned-voices"

    headers = {
        "accept": "application/json",
        "AUTHORIZATION": f"{os.getenv('PLAYHT_API_KEY')}",
        "X-USER-ID": "z11PAfQU1ggfNt99HRZ7GyWSPat1",
    }

    response = requests.get(url, headers=headers)

    clone_id = response.json()[0]["id"]

    url = "https://api.play.ht/api/v2/tts/stream"

    payload = {
        "text": result_text,
        "voice": clone_id,
        "output_format": "mp3",
        "emotion": "male_happy",
        "voice_engine": "PlayHT2.0-turbo",
    }
    headers = {
        "accept": "audio/mpeg",
        "content-type": "application/json",
        "AUTHORIZATION": f"{os.getenv('PLAYHT_API_KEY')}",
        "X-USER-ID": "z11PAfQU1ggfNt99HRZ7GyWSPat1",
    }

    # Byte audio stream
    audio = requests.post(url, json=payload, headers=headers)

    return audio.content


async def send_keepalive(
    dg_websocket: websockets.WebSocketClientProtocol, interval: int = 8
) -> None:
    keepalive_message = json.dumps({"type": "KeepAlive"})
    while True:
        await asyncio.sleep(interval)
        await dg_websocket.send(keepalive_message)


# Deepgram WebSocket streaming function
async def stream_to_deepgram(websocket: WebSocket) -> None:
    uri = "wss://api.deepgram.com/v1/listen?model=nova-2-conversationalai&language=en-US&smart_format=true&endpointing=3000"
    headers = {"Authorization": f"token {os.getenv('DEEPGRAM_API_KEY')}"}

    print("establishing connection with Deepgram")
    try:
        async with websockets.connect(uri, extra_headers=headers) as dg_websocket:
            full_transcription = ""
            print("established connection with Deepgram\n\n")
            while True:
                # keepalive_task = asyncio.create_task(send_keepalive(dg_websocket))
                print("waiting to receive bytes from client")
                # receive binary audio data from client
                client_audio_bytes = await websocket.receive_bytes()
                assert client_audio_bytes is not None
                print("received bytes from client")

                # # Save the audio bytes to a file
                # audio_stream = io.BytesIO(client_audio_bytes)
                # audio = AudioSegment.from_file(
                #     audio_stream, format="m4a"
                # )  # Replace 'wav' with the correct format of your audio

                # # Play the audio
                # play(audio)

                # Stream the audio bytes to Deepgram
                await dg_websocket.send(client_audio_bytes)

                # Receive real-time transcription from Deepgram
                response = await dg_websocket.recv()
                transcription = json.loads(response)
                print(
                    f'Transcription from DG: {transcription["channel"]["alternatives"][0]["transcript"]}\n\n'
                )

                # check for the 'speech_final' flag or equivalent in Deepgram's response
                is_final = transcription["speech_final"]
                text = transcription["channel"]["alternatives"][0]["transcript"]
                full_transcription += text

                if is_final:
                    print("Processing full transcript")
                    print(f"\nFull transcription from DG: {full_transcription}\n\n")
                    # Process the complete transcription and get AI response
                    audio_bytes = await say_to_ai(text=full_transcription)

                    # Send AI audio and text response back to your WebSocket client
                    print("Sending audio back to user\n\n")
                    await websocket.send_bytes(audio_bytes)

                    # Reset the full transcription for the next speaking segment
                    full_transcription = ""
    except websockets.exceptions.InvalidStatusCode as e:
        # If the request fails, print both the error message and the request ID from the HTTP headers
        print(f'ERROR: Could not connect to Deepgram! {e.headers.get("dg-error")}')
        print(
            f'Please contact Deepgram Support with request ID {e.headers.get("dg-request-id")}'
        )
    except Exception as e:
        # keepalive_task.cancel()
        raise Exception(e)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        print("websocket accepted")
        await stream_to_deepgram(websocket)
        print("finished sending audio back to user")
    except WebSocketDisconnect:
        print("disconnecting")
        await websocket.close()
    except Exception as e:
        print(f"Error in the backend: {e}")
        error_message = {"type": "error", "message": str(e)}
        await websocket.send_json(error_message)
        await websocket.close()


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     deepgram = Deepgram(os.getenv("DEEPGRAM_API_KEY"))  # type: ignore
#     try:
#         deepgramLive = await deepgram.transcription.live(
#             {
#                 "interim_results": False,
#                 "language": "en-US",
#                 "model": "2-conversationalai",
#                 "tier": "nova",
#                 "numerals": True,
#                 "punctuate": True,
#             }
#         )

#         # Listen for the connection to close
#         deepgramLive.register_handler(
#             deepgramLive.event.CLOSE,
#             lambda c: print(f"Connection closed with code {c}."),
#         )

#         # Listen for any transcripts received from Deepgram and write them to the console
#         deepgramLive.register_handler(deepgramLive.event.TRANSCRIPT_RECEIVED, print)

#         while True:
#             # receive the binary audio data from frontend as bytes
#             audio_data = await websocket.receive_bytes()
#             if audio_data:
#                 deepgramLive.send(audio_data)

#             print("processing audio data and returning AI output as speech")
#             response, text = await say_to_ai(file=audio_data)
#             ai_audio = await response.aread()
#             await websocket.send_bytes(ai_audio)
#             await websocket.send_text(json.dumps({"type": "text", "data": text}))
#             print("finished")
#     except WebSocketDisconnect:
#         print("disconnecting")
#         await websocket.close()
#     except Exception as e:
#         error_message = {"type": "error", "message": str(e)}
#         await websocket.send_json(error_message)
