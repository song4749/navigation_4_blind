import cv2
import numpy as np
import onnxruntime
import time
import io
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from ultralytics import YOLO
from pyngrok import ngrok

app = FastAPI()

# ─── 전역 변수 및 모델 설정 ─────────────────────────────
stop_detected_time = None
stop_hold_seconds = 1
previous_statuses = {}  # 장애물 박스별 이전 상태 저장
message_counter = {}
last_display_time = 0
current_display_warnings = []

# 모델 로드 (path 변경 필요)
model_1 = YOLO("object_detection/block_best.onnx", task="detect")
model_2 = YOLO("object_detection/obstacle_test.onnx", task="detect")
depth_model = onnxruntime.InferenceSession(
    "object_depth\\Depth-Anything-V2\\checkpoints\\depth_anything_v2_vitb.onnx",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)

def preprocess_depth_image(image, size=(518, 518)):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
    img = cv2.resize(img, size)
    img = img.transpose(2, 0, 1).astype(np.float32)
    return np.expand_dims(img, axis=0)

def estimate_depth(image):
    input_tensor = preprocess_depth_image(image)
    input_name = depth_model.get_inputs()[0].name
    depth_map = depth_model.run(None, {input_name: input_tensor})[0]
    depth_map = np.squeeze(depth_map)
    depth_map = cv2.resize(depth_map, (image.shape[1], image.shape[0]))
    depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
    return depth_map

def extract_warnings(frame):
    global stop_detected_time, previous_statuses
    global message_counter, last_display_time, current_display_warnings

    frame_time = time.time()
    temp_warnings = []
    processed_frame = frame.copy()
    frame_height, frame_width = processed_frame.shape[:2]

    results_1 = list(model_1.predict(processed_frame, imgsz=640, conf=0.5, device=0, stream=True))
    results_2 = list(model_2.predict(processed_frame, imgsz=640, conf=0.5, device=0, stream=True))
    depth_map = estimate_depth(processed_frame)

    block_detected = False
    skip_other_guidance = False

    for r in results_1:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"
            if class_name.lower() == "stop" and y2 > frame_height * 0.95:
                block_detected = True
                if stop_detected_time is None:
                    stop_detected_time = time.time()
                temp_warnings.append("Stop sign detected! Please stop.")
                skip_other_guidance = True

    if stop_detected_time:
        if time.time() - stop_detected_time < stop_hold_seconds:
            skip_other_guidance = True
        else:
            skip_other_guidance = False
            stop_detected_time = None

    if not skip_other_guidance:
        for r in results_1:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"
                if class_name.lower() != "stop":
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    w = x2 - x1
                    h = y2 - y1
                    ratio = w / h if h != 0 else 0
                    left_threshold = int(frame_width * 0.3)
                    right_threshold = int(frame_width * 0.7)
                    if cx < left_threshold:
                        temp_warnings.append("Off the guide block. Move left.")
                    elif cx > right_threshold:
                        temp_warnings.append("Off the guide block. Move right.")
                    if ratio > 1.5 and cy > frame_height * 0.6:
                        if cx < frame_width * 0.5:
                            temp_warnings.append("Turn Left.")
                        else:
                            temp_warnings.append("Turn Right.")

    for r in results_2:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            depth_value = depth_map[cy, cx]
            center_left = int(frame_width * 0.3)
            center_right = int(frame_width * 0.7)
            is_center = center_left <= cx <= center_right

            if depth_value > 0.2:
                current_status = "Danger"
            elif depth_value > 0.1:
                current_status = "Warning"
            else:
                current_status = "Safe"

            box_id = f"{cx//20}_{cy//20}"
            if box_id in previous_statuses:
                prev_status = previous_statuses[box_id]
                if prev_status == "Warning" and current_status == "Danger" and is_center:
                    if cx < frame_width * 0.5:
                        temp_warnings.append("Danger Increasing! Be careful! Move RIGHT to avoid obstacle!")
                    else:
                        temp_warnings.append("Danger Increasing! Be careful! Move LEFT to avoid obstacle!")
                previous_statuses[box_id] = current_status
            else:
                previous_statuses[box_id] = current_status

            temp_warnings.append(current_status + " (Obstacle)")

    if not block_detected:
        temp_warnings.append("No guide block detected.")

    confirmed_warnings = []
    for w in temp_warnings:
        message_counter[w] = message_counter.get(w, 0) + 1
        if message_counter[w] >= 4:
            confirmed_warnings.append(w)

    if confirmed_warnings:
        current_display_warnings = confirmed_warnings
        last_display_time = frame_time
    elif time.time() - last_display_time > 1:
        current_display_warnings = []

    return current_display_warnings

@app.get("/")
async def index():
    html_content = """
    <html>
    <head><title>Mobile Real-Time Test</title></head>
    <body>
        <h1>Mobile Camera Stream and Warnings</h1>
        <video id="video" autoplay playsinline width="640" height="640" style="border:1px solid black;"></video><br>
        <h2>Warnings:</h2>
        <div id="warnings" style="font-size:20px; color:red;"></div>
        <script>
            const video = document.getElementById("video");
            const warningsDiv = document.getElementById("warnings");
            navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 640, facingMode: "environment" } })
            .then(stream => { video.srcObject = stream; })
            .catch(err => { console.error("Error accessing camera:", err); });

            async function sendFrame() {
                const canvas = document.createElement("canvas");
                canvas.width = 640;
                canvas.height = 640;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                canvas.toBlob(async blob => {
                    const formData = new FormData();
                    formData.append("file", blob, "frame.jpg");
                    try {
                        const response = await fetch("/process_warning", {
                            method: "POST",
                            body: formData
                        });
                        const data = await response.json();
                        warningsDiv.innerHTML = data.warnings.join("<br>");
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
    warnings = extract_warnings(frame)
    return JSONResponse(content={"warnings": warnings})

public_url = ngrok.connect(8000)
print("Ngrok Public URL:", public_url)
