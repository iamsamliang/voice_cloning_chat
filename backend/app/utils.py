import websockets
import asyncio
import io

from pydub import AudioSegment
from pydub.playback import play


# For deepgram to keep connection alive
async def send_keepalive(
    dg_websocket: websockets.WebSocketClientProtocol, interval: int = 7
) -> None:
    while True:
        try:
            await dg_websocket.send('{"type": "KeepAlive"}')
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in keepalive task: {e}")
            break


# testing purposes to play audio from client
def play_audio(audio_bytes: bytes) -> None:
    # Save the audio bytes to a file
    audio_stream = io.BytesIO(audio_bytes)
    audio = AudioSegment.from_file(audio_stream, format="webm")

    play(audio)
