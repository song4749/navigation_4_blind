from ultralytics import YOLO

# YOLO 모델 로드
model = YOLO("object_detection/best.onnx")  # 또는 사용자 정의 모델 경로

# 웹캠에서 실시간 객체 감지 수행
model.predict(source=0, show=True)