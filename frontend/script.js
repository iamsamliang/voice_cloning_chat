let ws = null;
let mediaRecorder = null;
let shouldSendData = true;
let isRecording = false;
let isDetectTalking = true;
let isWebSocketOpen = false;
let audioChunks = [];

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        shouldSendData = false;
        mediaRecorder.stop();
    }
}

function setupWebSocket() {
    console.log("Setting up websocket");
    ws = new WebSocket(`ws://localhost:8000/ws`); // localhost testing only
    ws.onopen = function(event) {
        console.log('WebSocket connection established');
        isWebSocketOpen = true;
        mediaRecorder = null;
        shouldSendData = true;
        isRecording = false;
        isDetectTalking = true;
        audioChunks = [];
        startVoiceDetection();
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
        isWebSocketOpen = false;
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

            isDetectTalking = false;
            // don't record when audio plays from speaker
            shouldSendData = false;
            if (mediaRecorder && mediaRecorder.state === "recording") {
                console.log("Stopping recording while playing sound from speakers");
                shouldSendData = false;
                mediaRecorder.stop(); // This will set isRecording to false in the onstop event
            }
            audioChunks = [];

            const playContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await message.arrayBuffer();

            try {
                const audioBuffer = await playContext.decodeAudioData(arrayBuffer);

                const source = playContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(playContext.destination); // connect to speakers
                source.onended = () => {
                    isDetectTalking = true;
                    // resume recording after the audio has finished playing
                    if (mediaRecorder && mediaRecorder.state === "inactive") {
                        console.log("Starting recording after playing sound from speakers")
                        mediaRecorder.start();
                        shouldSendData = true;
                    }
                };
                source.start(); // play the audio via speakers
            } catch (e) {
                console.error('Error decoding audio:', e);
            }
        }
    } catch (error) {
        console.error('Error processing message from server:', error);
    }
}

function startVoiceDetection() {
    navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(stream => {
        const options = { mimeType: 'audio/webm' };
        if (MediaRecorder.isTypeSupported(options.mimeType)) {
            mediaRecorder = new MediaRecorder(stream, options);
        } else {
            console.log(options.mimeType + " is not supported, using default settings");
            mediaRecorder = new MediaRecorder(stream);
        }

        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;

        source.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        isRecording = false;
        let timeoutReference = null;

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            isRecording = false;
            isDetectTalking = false;
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];

            if (shouldSendData && ws && ws.readyState === WebSocket.OPEN) {
                console.log("Mime type: ", audioBlob.type);
                ws.send(audioBlob);
                console.log("data sent to backend");
            }

            shouldSendData = true;
        };

        function detectTalking() {
            if (!isDetectTalking) {
                requestAnimationFrame(detectTalking);
                return; // Skip processing if detection is temporarily disabled
            }
            analyser.getByteFrequencyData(dataArray);
            
            let sum = dataArray.reduce((acc, value) => acc + value, 0);

            let average = sum / bufferLength;

            // for optimal quiet conditions
            const startThreshold = 20;
            const stopThreshold = 5;
            const stopDuration = 1500; // 1.5 seconds

            if (average > startThreshold) {
                if (timeoutReference) {
                    clearTimeout(timeoutReference); // clear the timeout if user starts talking again
                    timeoutReference = null;
                }
                if (!isRecording) {
                    console.log("Starting recording");
                    if (mediaRecorder && mediaRecorder.state === "inactive") {
                        mediaRecorder.start();
                    }
                    isRecording = true;
                }
            } else if (average < stopThreshold && isRecording) {
                if (!timeoutReference) {
                    timeoutReference = setTimeout(() => {
                        console.log("Stopping recording");
                        mediaRecorder.stop();
                        isRecording = false;
                        timeoutReference = null;
                    }, stopDuration);
                }
            }
            if (isWebSocketOpen) {
                requestAnimationFrame(detectTalking);
            } else {
                console.log("WebSocket closed, stopping voice detection.");
                return;
            }
        }

        detectTalking();
    })
    .catch(err => {
        console.error('Microphone access was denied', err);
    });
}


document.getElementById('start-call-btn').addEventListener('click', function() {
    document.getElementById('start-call-btn').style.display = 'none';
    document.getElementById('end-call-btn').style.display = 'inline-block';
    document.getElementById('user-icon-container').style.display = 'block';

    // start the call
    setupWebSocket();
});

document.getElementById('end-call-btn').addEventListener('click', function() {
    document.getElementById('end-call-btn').style.display = 'none';
    document.getElementById('start-call-btn').style.display = 'inline-block';
    document.getElementById('user-icon-container').style.display = 'none';

    // end the call
    isWebSocketOpen = false;
    stopRecording();
    if (ws) {
        ws.close();
        console.log('WebSocket connection closed');
    }
});