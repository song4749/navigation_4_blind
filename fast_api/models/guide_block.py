from ultralytics import YOLO

# 점자블록 YOLO 모델 로드
model = YOLO("object_detection/block_best.onnx", task="detect")

def detect_blocks(frame):
    """
    점자블록 탐지 수행 함수
    """
    results = model.predict(frame, imgsz=640, conf=0.5, device=0, stream=True)
    return list(results)
