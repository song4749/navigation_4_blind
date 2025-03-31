import cv2
import numpy as np
from ultralytics import YOLO

# 1. 모델 로드
model = YOLO("road_segmentation/road_segmentation_small.onnx", task="segment")

# 2. 동영상 로드
cap = cv2.VideoCapture("test_video/long_video.mp4")
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# 전체 프레임 수 및 시작 위치 계산 (마지막 30초)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
max_frames = int(fps * 30)
start_frame = max(0, total_frames - max_frames)
cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

# 3. 결과 저장 설정
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("test_video/seg_result_last30s.mp4", fourcc, fps, (width, height))

# 4. 클래스별 색상 고정
class_colors = {
    "sidewalk": (0, 255, 0),
    "road": (0, 0, 255),
    "braille_guide_blocks": (255, 255, 0),
    "caution_zone": (255, 0, 255),
    "alley": (0, 255, 255)
}
default_color = (200, 200, 200)
alpha = 0.4

frame_count = 0

# 5. 프레임별 추론
while cap.isOpened() and frame_count < max_frames:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, imgsz=640, conf=0.4)
    result = results[0]
    seg_vis = frame.copy()

    if result.masks is not None and result.boxes.cls is not None:
        masks = result.masks.data
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        class_names = result.names

        for i, mask in enumerate(masks):
            class_id = class_ids[i]
            class_name = class_names.get(class_id, "unknown")
            color = class_colors.get(class_name, default_color)

            binary_mask = mask.cpu().numpy().astype(np.uint8) * 255
            binary_mask = cv2.resize(binary_mask, (frame.shape[1], frame.shape[0]))

            overlay = np.full_like(frame, color, dtype=np.uint8)
            blended = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
            seg_vis[binary_mask > 0] = blended[binary_mask > 0]

    out.write(seg_vis)

    frame_count += 1
    percent = (frame_count / max_frames) * 100
    print(f"\rProcessing: {frame_count}/{max_frames} frames ({percent:.1f}%)", end='')

cap.release()
out.release()
print("\nSegmentation of last 30 seconds saved to test_video/seg_result_last30s.mp4")
