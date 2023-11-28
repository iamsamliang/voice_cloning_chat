import requests
import os
import tempfile
import subprocess
import openai


async def LLM(text: str, federer_id: str, thread_id: str) -> str:
    """OpenAI GPT-3.5-Turbo LLM with Assistants API. Pass client's text into here."""

    openai.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=federer_id,
    )

    while (
        openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id).status
        != "completed"
    ):
        continue

    run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    messages = openai.beta.threads.messages.list(thread_id=thread_id, limit=1)

    result_text = messages.data[0].content[0].text.value  # type: ignore

    print(f"GPT response: {result_text}\n\n")

    return result_text


async def HT_TTS(result_text: str) -> bytes:
    """PlayHT's Text to Speech with Roger Federer Voice Clone. Pass LLM's text into here."""

    print("HT start processing")

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
    print("HT done processing\n\n")

    return audio.content


def whisper_STT(input_bytes: bytes, input_format: str) -> str:
    """Speech to Text using OpenAI's Whisper. This function contains a workaround for an OpenAI Whisper API bug for MediaRecorder files. Pass client's speech into here."""

    input_file = f"tempinputfile.{input_format}"
    with open(input_file, "wb") as f:
        f.write(input_bytes)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
        output_audio = temp_mp3.name

    # Use ffmpeg to convert the webm file to mp3
    # command = f"ffmpeg -y -i {input_file} -vn -ar 16000 -ac 1 {output_audio}"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_audio,
    ]
    subprocess.call(command)

    # subprocess.call(command, shell=True)
    # Transcribe the audio
    audio_file = open(output_audio, "rb")
    full_text = openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="en",
        response_format="text",
    )

    # Close and remove the temporary MP3 file
    audio_file.close()
    os.remove(output_audio)
    os.remove(input_file)

    print(f"Transcription complete: {full_text}\n\n")

    return full_text  # type: ignore


# Deepgram WebSocket streaming function
# async def DG_STT(websocket: WebSocket) -> None:
#     uri = "wss://api.deepgram.com/v1/listen?model=nova-2-conversationalai&language=en-US&smart_format=true&endpointing=3000"
#     headers = {"Authorization": f"token {os.getenv('DEEPGRAM_API_KEY')}"}
#     keepalive_task = None

#     try:
#         async with websockets.connect(uri, extra_headers=headers) as dg_websocket:
#             # full_transcription = ""

#             print("established connection with Deepgram\n\n")
#             keepalive_task = asyncio.create_task(send_keepalive(dg_websocket))

#             while True:
#                 print("waiting to receive bytes from client")
#                 # receive binary audio data from client
#                 client_audio_bytes = await websocket.receive_bytes()
#                 assert client_audio_bytes is not None
#                 print("received bytes from client")

#                 # play_audio(client_audio_bytes)  # testing purposes only

#                 # Stream the audio bytes to Deepgram
#                 await dg_websocket.send(client_audio_bytes)

#                 # Receive real-time transcription from Deepgram
#                 response = await dg_websocket.recv()
#                 transcription = json.loads(response)
#                 full_text = transcription["channel"]["alternatives"][0]["transcript"]

#                 print(f"Transcription from DG: {full_text}\n\n")

#                 # check for the 'speech_final' flag or equivalent in Deepgram's response
#                 # is_final = transcription["speech_final"]
#                 # full_transcription += text

#                 print("Processing full transcript")
#                 audio_bytes = await say_to_ai(text=full_text)

#                 # Send AI audio and text response back to your WebSocket client
#                 print("Sending audio back to user\n\n")
#                 await websocket.send_bytes(audio_bytes)

#                 # if is_final:
#                 #     print("Processing full transcript")
#                 #     print(f"\nFull transcription from DG: {full_transcription}\n\n")
#                 #     # Process the complete transcription and get AI response
#                 #     audio_bytes = await say_to_ai(text=full_transcription)

#                 #     # Send AI audio and text response back to your WebSocket client
#                 #     print("Sending audio back to user\n\n")
#                 #     await websocket.send_bytes(audio_bytes)

#                 #     # Reset the full transcription for the next speaking segment
#                 #     full_transcription = ""
#     except websockets.exceptions.InvalidStatusCode as e:
#         # If the request fails, print both the error message and the request ID from the HTTP headers
#         print(f'ERROR: Could not connect to Deepgram! {e.headers.get("dg-error")}')
#         print(
#             f'Please contact Deepgram Support with request ID {e.headers.get("dg-request-id")}'
#         )
#     except Exception as e:
#         raise Exception(e)
#     finally:
#         if keepalive_task:
#             keepalive_task.cancel()
#             await keepalive_task  # await to ensure it's properly closed
