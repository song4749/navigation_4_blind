import cv2
import numpy as np
import onnxruntime
from ultralytics import YOLO

# 🔹 ONNX 모델 로드
depth_model = onnxruntime.InferenceSession("object_depth/midas_small.onnx")  # 깊이 측정 모델
yolo_model = YOLO("object_detection/best.onnx")  # 장애물 탐지 모델

# 🔹 웹캠 설정
cap = cv2.VideoCapture(0)  # 기본 웹캠
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 🔹 장애물 감지 거리 임계값 (이 값 이하이면 경고)
depth_threshold = 100

# 🔹 클래스 목록 (예시, data.yaml 참고)
classes = ['barricade', 'bench', 'bicycle', 'bollard', 'bus', 'car', 'carrier', 'chair', 'dog', 'fire_hydrant', 'kiosk', 'motorcycle', 'movable_signage', 'parking_meter', 'person', 'pole', 'potted_plant', 'scooter', 'stop', 'stroller', 'table', 'traffic_light', 'traffic_sign', 'tree_trunk', 'truck', 'wheelchair']

def preprocess_image(image, size=(128, 128)):
    """ MiDaS ONNX 모델 입력을 위한 이미지 전처리 """
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0  # 정규화
    img = cv2.resize(img, size)
    img = img.transpose(2, 0, 1).astype(np.float32)  # (H, W, C) → (C, H, W)
    img = np.expand_dims(img, axis=0)  # 배치 차원 추가
    return img

def estimate_depth(image):
    """ 깊이 측정 실행 """
    input_tensor = preprocess_image(image)
    input_name = depth_model.get_inputs()[0].name
    depth_map = depth_model.run(None, {input_name: input_tensor})[0]
    depth_map = np.squeeze(depth_map)  # (1, H, W) → (H, W)
    depth_map = cv2.resize(depth_map, (image.shape[1], image.shape[0]))  # 원본 크기로 변환
    return depth_map

# 🔹 실시간 실행
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 1️⃣ YOLO 장애물 감지 실행
    results = yolo_model.predict(frame)

    # 2️⃣ MiDaS 깊이 측정 실행
    depth_map = estimate_depth(frame)

    # 3️⃣ 깊이 맵을 컬러맵으로 변환
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_map, alpha=255.0 / depth_map.max()), cv2.COLORMAP_INFERNO)

    # 4️⃣ 장애물 감지된 객체 표시
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0]
            cls_id = int(box.cls[0])

            if conf > 0.5:  # 신뢰도 필터링
                label = classes[cls_id] if cls_id < len(classes) else "Unknown"
                color = (0, 255, 0) if label == "person" else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # 5️⃣ 장애물 거리 경고
                obstacle_region = depth_map[y1:y2, x1:x2]
                min_depth = np.min(obstacle_region)  # 해당 영역에서 가장 가까운 깊이값

                if min_depth < depth_threshold:
                    cv2.putText(frame, "⚠️ WARNING: Obstacle Close!", (50, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3, cv2.LINE_AA)

    # 6️⃣ 원본 영상과 깊이 맵을 나란히 배치하여 표시
    new_size = (frame.shape[1] // 2, frame.shape[0] // 2)
    frame_resized = cv2.resize(frame, new_size)
    depth_colormap_resized = cv2.resize(depth_colormap, new_size)
    combined_output = cv2.hconcat([frame_resized, depth_colormap_resized])

    cv2.imshow("Obstacle Detection & Depth Map", combined_output)

    # ESC 키 입력 시 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
