import cv2
import numpy as np
import onnxruntime
import time
from ultralytics import YOLO

# 항상 메시지 출력 시간을 위해 시간 보관 모델
stop_detected_time = None
stop_hold_seconds = 3

# ▪️ 모델 로드
model_1 = YOLO("object_detection/block_best.onnx", task="detect")
model_2 = YOLO("object_detection\obstacle_test.onnx", task="detect")

# ▪️ Depth Anything V2 Small ONNX
depth_model = onnxruntime.InferenceSession(
    "object_depth\Depth-Anything-V2\checkpoints\depth_anything_v2_vits.onnx",
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

video_path = "long_video.mp4"
cap = cv2.VideoCapture(video_path)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
# ▪️ 기존: 1분 제한용 max_frames 코드 → 주석 처리
# max_frames = int(fps * 60)

# ▪️ 전체 프레임 개수 가져오기
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("output_video.mp4", fourcc, fps, (frame_width, frame_height))

print("YOLO + Depth Anything v2")

# frame_index = 0
# while frame_index < max_frames:
#     ret, frame = cap.read()
#     if not ret:
#         break

# ▪️ 장애물 상태 추적용
previous_statuses = {}

frame_index = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break

    print(f"\r[INFO] Processing frame {frame_index + 1} / {total_frames}", end='', flush=True)
    frame_index += 1

    results_1 = list(model_1.predict(frame, imgsz=640, conf=0.5, device=0, stream=True))
    results_2 = list(model_2.predict(frame, imgsz=640, conf=0.5, device=0, stream=True))
    depth_map = estimate_depth(frame)

    block_detected = False
    stop_detected = False
    skip_other_guidance = False

    for r in results_1 + results_2:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id] if cls_id < len(r.names) else "Unknown"

            color = (0, 255, 0) if r in results_1 else (0, 0, 255)
            label_text = f"{class_name} {conf:.2f}"

            if r in results_1:
                block_detected = True
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                w = x2 - x1
                h = y2 - y1
                ratio = w / h

                # Stop block 추가
                if class_name.lower() == "stop" and y2 > frame_height * 0.95:
                    stop_detected = True
                    if stop_detected_time is None:
                        stop_detected_time = time.time()

                    cv2.putText(frame, "Stop sign detected! Please stop.",
                                (50, frame_height - 150), cv2.FONT_HERSHEY_SIMPLEX,
                                1.2, (0, 0, 255), 3, cv2.LINE_AA)
                    skip_other_guidance = True

            if stop_detected_time:
                if time.time() - stop_detected_time < stop_hold_seconds:
                    skip_other_guidance = True
                else:
                    skip_other_guidance = False
                    stop_detected_time = None

            if not skip_other_guidance:
                if r in results_1:
                    left_threshold = int(frame_width * 0.3)
                    right_threshold = int(frame_width * 0.7)

                    if cx < left_threshold:
                        cv2.putText(frame, "Off the guide block. Move left.",
                                    (50, frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX,
                                    1.0, (255, 255, 0), 3, cv2.LINE_AA)
                    elif cx > right_threshold:
                        cv2.putText(frame, "Off the guide block. Move right.",
                                    (50, frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX,
                                    1.0, (255, 255, 0), 3, cv2.LINE_AA)

                    if ratio > 1.5 and cy > frame_height * 0.6:
                        if cx < frame_width * 0.5:
                            cv2.putText(frame, "Turn Left",
                                        (50, frame_height - 100), cv2.FONT_HERSHEY_SIMPLEX,
                                        1.2, (0, 0, 255), 3, cv2.LINE_AA)
                        else:
                            cv2.putText(frame, "Turn Right",
                                        (50, frame_height - 100), cv2.FONT_HERSHEY_SIMPLEX,
                                        1.2, (0, 0, 255), 3, cv2.LINE_AA)

                if r in results_2:
                    depth_value = depth_map[cy, cx]

                    # 상태 분류
                    if depth_value > 0.4:
                        current_status = "Danger"
                        color = (0, 0, 255)
                    elif depth_value > 0.2:
                        current_status = "Warning"
                        color = (0, 165, 255)
                    else:
                        current_status = "Safe"
                        color = (0, 255, 0)

                    label_text += f" | {current_status}"

                    # 중심 범위: 30% ~ 70%
                    center_left = int(frame_width * 0.3)
                    center_right = int(frame_width * 0.7)
                    is_center = center_left <= cx <= center_right

                    # 간단한 위치 기반 추적 ID
                    box_id = f"{cx//20}_{cy//20}"

                    # 상태 변화 감지: Warning → Danger + 중심일 때만 경고 출력
                    if box_id in previous_statuses:
                        prev_status = previous_statuses[box_id]
                        if prev_status == "Warning" and current_status == "Danger" and is_center:
                            # 기존 경고 메시지
                            cv2.putText(frame, "Danger Increasing! Be careful!",
                                        (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                        1.2, (0, 0, 255), 3, cv2.LINE_AA)

                            # ➕ 피할 방향 안내
                            if cx < frame_width * 0.5:
                                cv2.putText(frame, "Move RIGHT to avoid obstacle!",
                                            (50, 150), cv2.FONT_HERSHEY_SIMPLEX,
                                            1.0, (0, 0, 255), 3, cv2.LINE_AA)
                            else:
                                cv2.putText(frame, "Move LEFT to avoid obstacle!",
                                            (50, 150), cv2.FONT_HERSHEY_SIMPLEX,
                                            1.0, (0, 0, 255), 3, cv2.LINE_AA)

                    previous_statuses[box_id] = current_status
                    
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    if not block_detected:
        cv2.putText(frame, "No guide block detected",
                    (50, frame_height - 60), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 3, cv2.LINE_AA)

    out.write(frame)

cap.release()
out.release()
print("Done: output saved")
