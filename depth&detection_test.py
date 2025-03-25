from ultralytics import YOLO
import cv2
import numpy as np
import onnxruntime

# 🔹 YOLO ONNX 모델 로드
model_1 = YOLO("object_detection/block_best.onnx", task="detect")  # 점자 블록 탐지 모델
model_2 = YOLO("object_detection/obstacle_test.onnx", task="detect")  # 장애물 탐지 모델

# 🔹 깊이 측정 ONNX 모델 로드
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

# 🔹 동영상 파일 열기
video_path = "KakaoTalk_20250320_144019708.mp4"  # 사용할 동영상 경로
cap = cv2.VideoCapture(video_path)

# 🔹 비디오 저장 설정
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("output_with_alerts.mp4", fourcc, cap.get(cv2.CAP_PROP_FPS), (int(cap.get(3)), int(cap.get(4))))

# 🔹 출력 창 크기 설정 (비율 유지)
display_scale = 0.5  # 50% 크기로 축소

frame_count = 0
frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    print(f"[INFO] Processing frame {frame_count} / {frame_total}")

    results_1 = list(model_1.predict(frame, imgsz=640, conf=0.5, stream=True))
    results_2 = list(model_2.predict(frame, imgsz=640, conf=0.5, stream=True))

    # 🔹 깊이맵 추정 (화면에는 표시하지 않음)
    depth_map = estimate_depth(frame)

    # 🔹 깊이 컬러맵 생성 (주석처리: 나중에 시각화하고 싶을 때 사용)
    # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_map, alpha=255.0 / depth_map.max()), cv2.COLORMAP_INFERNO)

    for r in results_1 + results_2:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0]
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"

            color = (0, 255, 0) if r in results_1 else (0, 0, 255)
            label_text = f"{class_name} {conf:.2f}"

            # 🔹 깊이 기반 경고 판단 (계속 활성화)
            if r in results_2:
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                depth_value = depth_map[cy, cx]
                # print(f"[DEBUG] {class_name} depth value at ({cx},{cy}): {depth_value:.3f}")
                if depth_value > 500:
                    warning_text = "Danger"
                    color = (0, 0, 255)
                elif depth_value < 100:
                    warning_text = "Warning"
                    color = (0, 165, 255)
                else:
                    warning_text = "Safe"
                    color = (0, 255, 0)
                label_text += f" | {warning_text}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 🔹 결과 프레임 저장
    out.write(frame)

    # 🔹 비율 유지하면서 화면 축소해서 출력 (주석처리: 나중에 실시간으로 보고 싶을 때 해제)
    # resized = cv2.resize(frame, (0, 0), fx=display_scale, fy=display_scale)
    # cv2.imshow("YOLO Object Detection (Video)", resized)

    # if cv2.waitKey(1) & 0xFF == 27:
    #     break

cap.release()
out.release()
cv2.destroyAllWindows()
