import cv2
import numpy as np
import onnxruntime
from PIL import Image
from transformers import SegformerFeatureExtractor

# ✅ 클래스 이름 (Cityscapes 기준, SegFormer 모델 출력 19개 클래스)
class_names = {
    0: "road", 1: "sidewalk", 2: "building", 3: "wall", 4: "fence",
    5: "pole", 6: "traffic light", 7: "traffic sign", 8: "vegetation", 9: "terrain",
    10: "sky", 11: "person", 12: "rider", 13: "car", 14: "truck",
    15: "bus", 16: "train", 17: "motorcycle", 18: "bicycle"
}

# ✅ 고정된 팔레트 색상 (각 클래스 ID마다 RGB)
cityscapes_palette = np.array([
    [128, 64,128],  [244, 35,232],  [ 70, 70, 70],  [102,102,156],  [190,153,153],
    [153,153,153],  [250,170, 30],  [220,220,  0],  [107,142, 35],  [152,251,152],
    [ 70,130,180],  [220, 20, 60],  [255,  0,  0],  [  0,  0,142],  [  0,  0, 70],
    [  0, 60,100],  [  0, 80,100],  [  0,  0,230],  [119, 11, 32]
], dtype=np.uint8)

# ✅ 모델 경로 및 로딩
onnx_path = "road_segmentation/segformer_b2_cityscapes_onnx/model.onnx"
session = onnxruntime.InferenceSession(
    onnx_path,
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
extractor = SegformerFeatureExtractor.from_pretrained("road_segmentation/segformer_b2_cityscapes_onnx")

# ✅ 비디오 로딩
video_path = "long_video.mp4"
cap = cv2.VideoCapture(video_path)

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or np.isnan(fps):
    fps = 30

# ✅ 1분 테스트용
max_frames = int(fps * 60)

out = cv2.VideoWriter("output_segmented.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))

frame_index = 0
while cap.isOpened() and frame_index < max_frames:
    ret, frame = cap.read()
    if not ret:
        break

    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    inputs = extractor(images=image, return_tensors="np")
    onnx_inputs = {session.get_inputs()[0].name: inputs["pixel_values"]}
    outputs = session.run(None, onnx_inputs)

    logits = outputs[0]  # (1, 19, h, w)
    seg = np.argmax(np.squeeze(logits), axis=0)  # (h, w)
    seg_resized = cv2.resize(seg.astype(np.uint8), (frame_width, frame_height), interpolation=cv2.INTER_NEAREST)

    # ✅ 컬러 마스크 생성
    color_seg = cityscapes_palette[seg_resized]

    # ✅ 프레임과 합성
    frame_resized = cv2.resize(frame, (frame_width, frame_height))
    blended = cv2.addWeighted(frame_resized, 0.5, color_seg, 0.5, 0)

    # ✅ 클래스 이름 표시 (영역 중심에)
    for cls_id, class_name in class_names.items():
        mask = (seg_resized == cls_id).astype(np.uint8)
        if np.sum(mask) > 1000:  # 클래스 픽셀이 충분히 있을 때만 표시
            M = cv2.moments(mask)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(blended, class_name, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 2, cv2.LINE_AA)

    # ✅ 저장
    out.write(blended)
    print(f"\r[INFO] Processing frame {frame_index}", end="")
    frame_index += 1

# ✅ 마무리
cap.release()
out.release()
cv2.destroyAllWindows()
print("\nDone: Segmented video with labels saved.")
