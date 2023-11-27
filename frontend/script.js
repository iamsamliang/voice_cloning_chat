// Establish a WebSocket connection to the server
let ws = null;
let stream = null;
let mediaRecorder = null;

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        console.log("Stopping recording");
        mediaRecorder.stop();
    }
}

function setupWebSocket() {
    console.log("Setting up websocket");
    ws = new WebSocket(`ws://localhost:8000/ws`); // localhost testing only
    ws.onopen = function(event) {
        console.log('WebSocket connection established');
        startRecording();
    };

    ws.onmessage = async function(event) {
        // handle receiving data from the server via websocket
        await handleServerMessage(event.data);
    };

    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        ws.close()
    };

    ws.onclose = function(event) {
        console.log('WebSocket connection closed:', event);
        stopRecording();
        ws = null;
    };
}

async function handleServerMessage(message) {
    try {
        if (message.type === 'error') {
            console.error('Error from server:', message.message);
        } else if (message instanceof Blob) {
            // play audio bytes from backend
            console.log('Received audio bytes from server');
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await message.arrayBuffer();

            try {
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination); // connect to speakers
                source.start(); // play the audio via speakers
            } catch (e) {
                console.error('Error decoding audio:', e);
            }
        }
    } catch (error) {
        console.error('Error processing message from server:', error);
    }
}

async function startRecording() {
    try {
        console.log("Starting recording");
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // const options = { mimeType: 'audio/webm' };
        mediaRecorder = new MediaRecorder(stream);
        console.log("Microphone enabled");
        // console.log(mediaRecorder.mimeType);
        
        mediaRecorder.addEventListener("dataavailable", event => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                console.log("Sending data over socket");
                // Then, send the audio chunk as binary data
                ws.send(event.data);
                console.log("User voice successfully sent over socket");
            }
        });
        
        mediaRecorder.addEventListener("stop", () => {
            stream.getTracks().forEach(track => track.stop());
            // Optionally, send a message indicating recording end
            // if (ws && ws.readyState === WebSocket.OPEN) {
            //   ws.send(JSON.stringify({ type: 'endOfStream' }));
            // }
        });
        
        mediaRecorder.start(3000); // send data every N seconds over socket
        
    } catch (error) {
        console.error('Error accessing media devices:', error);
    }
}

document.getElementById('start-call-btn').addEventListener('click', function() {
    document.getElementById('start-call-btn').style.display = 'none';
    document.getElementById('end-call-btn').style.display = 'inline-block';
    document.getElementById('user-icon-container').style.display = 'block';

    // Start the call logic here
    setupWebSocket();
});

document.getElementById('end-call-btn').addEventListener('click', function() {
    document.getElementById('end-call-btn').style.display = 'none';
    document.getElementById('start-call-btn').style.display = 'inline-block';
    document.getElementById('user-icon-container').style.display = 'none';

    // End the call logic here
    stopRecording();
    if (ws) {
        ws.close();
        console.log('WebSocket connection closed');
    }
});