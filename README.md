# Voice Chat w/ Anyone

Web application to chat with tennis legend Roger Federer.

# Structure
Frontend contains JS code for UI and client-side logic. Backend uses FastAPI (Python) and websockets; contains the pipelines and server logic. App uses these models:
1. STT: OpenAI Whisper
2. LLM: OpenAI gpt-3.5-turbo
3. TTS: PlayHT Voice Clone of Roger Federer

You'll need to use your own OpenAI API Key and PlayHT API Key. `rf_speech.mov` contains the audio used to clone Federer's voice which you have to do on PlayHT's website as well.


# To run

1. Go to backend folder and run `poetry install` to install dependencies. 

2. `poetry shell` to activate auto created virtual environment

3. Backend built using FastAPI. To serve it up, run from root of the project and in command line type: `uvicorn backend.app.main:app`. Access from localhost:8000
