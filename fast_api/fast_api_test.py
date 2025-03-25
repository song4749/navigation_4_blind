from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import onnxruntime
from ultralytics import YOLO
from io import BytesIO
import base64
import uvicorn

app = FastAPI()

# 정적 파일 (JS/HTML) 제공용
app.mount("/static", StaticFiles(directory="static"), name="static")

# 모델 로딩
model_1 = YOLO("object_detection/block_best.onnx", task="detect")
model_2 = YOLO("object_detection/obstacle_test.onnx", task="detect")
depth_model = onnxruntime.InferenceSession("object_depth/midas_small.onnx")

def preprocess_depth_image(image, size=(128, 128)):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
    img = cv2.resize(img, size)
    img = img.transpose(2, 0, 1).astype(np.float32)
    img = np.expand_dims(img, axis=0)
    return img

def estimate_depth(image):
    input_tensor = preprocess_depth_image(image)
    input_name = depth_model.get_inputs()[0].name
    depth_map = depth_model.run(None, {input_name: input_tensor})[0]
    depth_map = np.squeeze(depth_map)
    depth_map = cv2.resize(depth_map, (image.shape[1], image.shape[0]))
    return depth_map

def process_frame(frame: np.ndarray) -> np.ndarray:
    results_1 = list(model_1.predict(frame, imgsz=640, conf=0.5, stream=True))
    results_2 = list(model_2.predict(frame, imgsz=640, conf=0.5, stream=True))
    depth_map = estimate_depth(frame)
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_map, alpha=255.0 / depth_map.max()), cv2.COLORMAP_INFERNO)

    for r in results_1 + results_2:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0]
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"
            color = (0, 255, 0) if r in results_1 else (0, 0, 255)
            cv2.rectangle(depth_colormap, (x1, y1), (x2, y2), color, 2)
            cv2.putText(depth_colormap, f"{class_name} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return depth_colormap

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/process_frame")
async def process_frame_api(request: Request):
    data = await request.json()
    img_data = data["image"].split(",")[1]  # "data:image/jpeg;base64,..."
    img_bytes = base64.b64decode(img_data)
    npimg = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    processed_image = process_frame(frame)
    _, buffer = cv2.imencode(".jpg", processed_image)
    return {"image": base64.b64encode(buffer).decode("utf-8")}

# 실행 명령 예시: uvicorn yolo_depth_fastapi:app --reload
