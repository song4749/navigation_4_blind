import cv2
import numpy as np
from ultralytics import YOLO

# YOLO-Seg 모델 로드
model = YOLO("road_segmentation/road_segmentation_small.onnx", task="segment")

# 클래스 매핑 (참고용)
# 0: alley, 1: bike_lane, 2: braille_guide_blocks, 3: caution_zone, 4: roadway, 5: sidewalk

def segment_sidewalk_road(image):
    """
    YOLO-Seg 모델을 이용해 세그멘테이션 맵 생성.
    각 픽셀 값은 해당 위치의 클래스 ID로 설정됨.
    """
    results = model.predict(image, imgsz=640)[0]
    seg_map = np.zeros(image.shape[:2], dtype=np.uint8)

    if results.masks is not None and results.boxes.cls is not None:
        masks = results.masks.data.cpu().numpy()  # (N, H, W)
        class_ids = results.boxes.cls.cpu().numpy().astype(int)  # (N,)

        for i, mask in enumerate(masks):
            class_id = class_ids[i]
            seg_map[mask > 0.5] = class_id

    return seg_map

def decode_segmap(seg_map):
    colors = {
        0: (128, 64, 128),  # alley
        1: (0, 255, 255),   # bike_lane
        2: (255, 255, 0),   # braille_guide_blocks
        3: (255, 0, 0),     # caution_zone
        4: (0, 0, 255),     # roadway
        5: (0, 255, 0),     # sidewalk
    }

    h, w = seg_map.shape
    vis = np.zeros((h, w, 3), dtype=np.uint8)
    for class_id, color in colors.items():
        vis[seg_map == class_id] = color
    return vis