from ultralytics import YOLO

# Load a pretrained YOLO11n model
model = YOLO("object_detection\obstacle_detect.onnx")

# Run inference on 'bus.jpg' with arguments
model.predict("test_video\long_video.mp4", save_dir="output/detection_test", save=True, imgsz=640, conf=0.5)