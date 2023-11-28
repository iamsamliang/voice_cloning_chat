import openai

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .pipeline import HT_TTS, whisper_STT, LLM

app = FastAPI()

load_dotenv()

# Mount the directory containing your static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def home() -> FileResponse:
    return FileResponse("frontend/index.html")


async def pipeline(websocket: WebSocket, federer_id: str, thread_id: str) -> None:
    try:
        while True:
            # 1. Receive speech from the client
            client_audio_bytes = await websocket.receive_bytes()
            assert client_audio_bytes is not None
            print("Received bytes from client\n\n")

            # 2. Speech to text
            full_text = whisper_STT(
                client_audio_bytes, "webm"
            )  # note only works on Chrome, workaround OpenAI Whisper API Bug for MediaRecorder files

            # 3. Text to LLM
            LLM_response = await LLM(
                text=full_text, federer_id=federer_id, thread_id=thread_id
            )

            # 4. LLM's Text to speech
            audio_bytes = await HT_TTS(result_text=LLM_response)

            # 5. Send LLM's speech back to client
            print("Sending audio back to user\n\n")
            await websocket.send_bytes(audio_bytes)
    except Exception as e:
        raise Exception(e)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    federer_id = openai.beta.assistants.create(
        instructions="You are Roger Federer. You are having a conversation with your good friend. Interact to him with warmth and as if you're meeting your old buddy. Don't make your sentences too long.",
        name="Roger Federer",
        model="gpt-3.5-turbo",
    ).id
    thread_id = openai.beta.threads.create().id
    try:
        print("websocket accepted")
        intro = await HT_TTS(result_text="Hi I'm Roger.")  # intro speech for LLM
        await websocket.send_bytes(intro)
        await pipeline(websocket, federer_id, thread_id)
    except WebSocketDisconnect:
        print("websocket disconnecting")
        await websocket.close()
    except Exception as e:
        print(f"Error in the backend: {e}")
        error_message = {"type": "error", "message": str(e)}
        await websocket.send_json(error_message)
        await websocket.close()
