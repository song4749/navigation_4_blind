import cv2
import numpy as np
from ultralytics import YOLO

# 1. 모델 로드 (task="segment"는 세그멘테이션용 YOLO로 처리)
model = YOLO("road_segmentation/road_segmentation_small.onnx", task="segment")

# 2. 동영상 로드
cap = cv2.VideoCapture("test_video/KakaoTalk_20250331_114905657.mp4")
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
out = cv2.VideoWriter("test_video\segmentation_output.mp4", fourcc, fps, (width, height))

# 4. 클래스별 색상 고정 (20개까지)
np.random.seed(42)
color_map = [tuple(np.random.randint(0, 255, size=3).tolist()) for _ in range(20)]
alpha = 0.4

frame_count = 0
all_class_ids = set()

# 5. 프레임별 추론
while cap.isOpened() and frame_count < max_frames:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, imgsz=640, conf=0.4)
    result = results[0]
    seg_vis = frame.copy()

    if result.masks is not None and result.boxes.cls is not None:
        masks = result.masks.data  # [N, H, W]
        class_ids = result.boxes.cls.cpu().numpy().astype(int)  # [N]
        class_names = result.names  # {class_id: name}

        for i, mask in enumerate(masks):
            class_id = class_ids[i]
            all_class_ids.add(class_id)

            color = color_map[class_id % len(color_map)]
            binary_mask = mask.cpu().numpy().astype(np.uint8) * 255
            binary_mask = cv2.resize(binary_mask, (frame.shape[1], frame.shape[0]))

            # 투명도 합성
            overlay = np.full_like(frame, color, dtype=np.uint8)
            blended = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
            seg_vis[binary_mask > 0] = blended[binary_mask > 0]

            # 중심 좌표에 클래스 번호 표시
            ys, xs = np.where(binary_mask > 0)
            if len(xs) > 0 and len(ys) > 0:
                cx, cy = int(np.mean(xs)), int(np.mean(ys))
                label = f"{class_id}"
                cv2.putText(seg_vis, label, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    out.write(seg_vis)
    frame_count += 1
    percent = (frame_count / max_frames) * 100
    print(f"\rProcessing: {frame_count}/{max_frames} frames ({percent:.1f}%)", end='')

cap.release()
out.release()
print("\nSegmentation result saved to: test_video/segmentation_output_numbered.mp4")

# 6. 마지막에 전체 클래스 ID + 이름 출력
print("\n모델이 인식하는 전체 클래스 목록:")
for cls_id, cls_name in model.names.items():
    print(f"  [{cls_id}] {cls_name}")
