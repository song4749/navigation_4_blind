from ultralytics import YOLO

# Load a pretrained YOLO11n model
model = YOLO("object_detection/best.onnx")

# Run inference on 'bus.jpg' with arguments
model.predict("KakaoTalk_20250317_094229683.mp4", save=True, imgsz=640, conf=0.5)