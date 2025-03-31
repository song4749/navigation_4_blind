from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pyngrok import ngrok
import cv2
import numpy as np
import time
import os

from fast_api.models.guide_block import detect_blocks
from fast_api.models.obstacle_depth import detect_obstacles, estimate_depth
from fast_api.utils.audio_map import warning_audio_map, priority_order
from fast_api.utils.state_manager_test import extract_warnings, reset_audio_status, is_audio_playing, set_audio_playing

app = FastAPI()
app.mount("/static_audio", StaticFiles(directory="fast_api/mp3"), name="static_audio")

@app.get("/")
async def index():
    html_content = """
    <html>
    <head><title>Mobile Real-Time Test</title></head>
    <body>
        <h1>Mobile Camera Stream and Warnings</h1>
        <video id=\"video\" autoplay playsinline width=\"640\" height=\"640\" style=\"border:1px solid black;\"></video><br>
        <h2>Warnings:</h2>
        <div id=\"warnings\" style=\"font-size:20px; color:red;\"></div>
        <script>
            const video = document.getElementById("video");
            const warningsDiv = document.getElementById("warnings");
            let currentAudio = null;

            navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 640, facingMode: "environment" } })
            .then(stream => { video.srcObject = stream; })
            .catch(err => { console.error("Error accessing camera:", err); });

            async function sendFrame() {
                const tempCanvas = document.createElement("canvas");
                tempCanvas.width = 640;
                tempCanvas.height = 640;
                const tempCtx = tempCanvas.getContext("2d");
                tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
                tempCanvas.toBlob(async blob => {
                    const formData = new FormData();
                    formData.append("file", blob, "frame.jpg");
                    try {
                        const start = performance.now();
                        const response = await fetch("/process_warning", {
                            method: "POST",
                            body: formData
                        });
                        const data = await response.json();
                        const end = performance.now();
                        console.log(`Response Time: ${(end - start).toFixed(1)} ms`);
                        warningsDiv.innerHTML = data.warnings.join("<br>");
                        if (data.audio_url) {
                            if (!currentAudio || currentAudio.ended) {
                                currentAudio = new Audio(data.audio_url);
                                currentAudio.play();
                                currentAudio.onended = () => {
                                    fetch("/audio_finished");
                                }
                            }
                        }
                    } catch (err) {
                        console.error("Error sending frame:", err);
                    }
                }, "image/jpeg");
            }

            setInterval(sendFrame, 200);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/process_warning")
async def process_warning(file: UploadFile = File(...)):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    block_results = detect_blocks(frame)
    obstacle_results = detect_obstacles(frame)
    depth_map = estimate_depth(frame)

    warnings, audio_filename = extract_warnings(frame, block_results, obstacle_results, depth_map)
    audio_url = f"/static_audio/{audio_filename}" if audio_filename else None
    return JSONResponse(content={"warnings": warnings, "audio_url": audio_url})

@app.get("/audio_finished")
async def audio_finished():
    reset_audio_status()
    return JSONResponse(content={"status": "ok"})

public_url = ngrok.connect(8000)
print("Ngrok Public URL:", public_url)
