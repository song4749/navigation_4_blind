from ultralytics import YOLO
import cv2
import numpy as np
import onnxruntime

# 🔹 YOLO ONNX 모델 로드
model_1 = YOLO("object_detection/block_best.onnx", task="detect")  # 점자 블록 탐지 모델
model_2 = YOLO("object_detection/obstacle_test.onnx", task="detect")  # 장애물 탐지 모델

# 🔹 깊이 측정 ONNX 모델 로드
depth_model = onnxruntime.InferenceSession("object_depth/midas_small.onnx")

# 🔹 웹캠 열기
cap = cv2.VideoCapture(0)  # 0: 기본 웹캠, 1: 외부 카메라
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def preprocess_depth_image(image, size=(128, 128)):  # 🔹 MiDaS 모델이 요구하는 크기
    """ 깊이 측정 모델 입력을 위한 이미지 전처리 """
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0  # 정규화
    img = cv2.resize(img, size)  # 🔹 모델이 기대하는 크기로 조정
    img = img.transpose(2, 0, 1).astype(np.float32)  # (H, W, C) → (C, H, W)
    img = np.expand_dims(img, axis=0)  # 배치 차원 추가
    return img

def estimate_depth(image):
    """ 깊이 측정 실행 """
    input_tensor = preprocess_depth_image(image)
    input_name = depth_model.get_inputs()[0].name
    depth_map = depth_model.run(None, {input_name: input_tensor})[0]
    depth_map = np.squeeze(depth_map)  # (1, H, W) → (H, W)
    depth_map = cv2.resize(depth_map, (image.shape[1], image.shape[0]))  # 원본 크기로 변환
    return depth_map

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break  # 웹캠이 종료되면 루프 종료

    # 1️⃣ YOLO 점자 블록 탐지 실행
    results_1 = list(model_1.predict(frame, imgsz=640, conf=0.5, stream=True))  # 🔹 입력 크기 416으로 최적화

    # 2️⃣ YOLO 장애물 탐지 실행
    results_2 = list(model_2.predict(frame, imgsz=640, conf=0.5, stream=True))  # 🔹 입력 크기 416으로 최적화

    # 3️⃣ 깊이 측정 모델 실행
    depth_map = estimate_depth(frame)

    # 4️⃣ 깊이 맵을 컬러맵으로 변환하여 시각화
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_map, alpha=255.0 / depth_map.max()), cv2.COLORMAP_INFERNO)

    # 5️⃣ YOLO 감지된 객체를 깊이 맵에 표시
    for r in results_1 + results_2:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])  # 바운딩 박스 좌표
            conf = box.conf[0]  # 신뢰도
            cls_id = int(box.cls[0])  # 클래스 ID

            # 클래스 이름 가져오기
            class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"

            # 모델별 색상 구분
            color = (0, 255, 0) if r in results_1 else (0, 0, 255)  # 초록: model_1, 빨강: model_2

            # 바운딩 박스를 깊이 맵에 그림 (원본 영상 없이!)
            cv2.rectangle(depth_colormap, (x1, y1), (x2, y2), color, 2)
            cv2.putText(depth_colormap, f"{class_name} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # 6️⃣ 깊이 맵만 화면에 출력
    cv2.imshow("YOLO & Depth Map (Live Webcam)", depth_colormap)

    # ESC 키 입력 시 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
