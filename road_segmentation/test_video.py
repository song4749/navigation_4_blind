import cv2
import numpy as np
import onnxruntime
from PIL import Image
from transformers import SegformerFeatureExtractor

# ✅ ONNX 모델 경로
onnx_path = "road_segmentation\segformer_b2_cityscapes_onnx\model.onnx"

# ✅ 모델 로딩
session = onnxruntime.InferenceSession(onnx_path)

# ✅ Feature Extractor 로딩
extractor = SegformerFeatureExtractor.from_pretrained("road_segmentation\segformer_b2_cityscapes_onnx")

# ✅ 컬러맵 (클래스 ID → RGB 색)
palette = np.random.randint(0, 255, size=(256, 3), dtype=np.uint8)

# ✅ 비디오 입력 경로
video_path = "long_video.mp4"
cap = cv2.VideoCapture(video_path)

# ✅ 비디오 출력 설정
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
out = cv2.VideoWriter("output_segmented.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))

frame_index = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # ✅ OpenCV BGR → PIL RGB 변환
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # ✅ 전처리
    inputs = extractor(images=image, return_tensors="np")
    onnx_inputs = {session.get_inputs()[0].name: inputs["pixel_values"]}

    # ✅ ONNX 추론
    outputs = session.run(None, onnx_inputs)
    logits = outputs[0]  # (1, num_classes, h, w)
    seg = np.argmax(logits[0], axis=0)  # (h, w)

    # ✅ 컬러 마스크 생성
    color_seg = palette[seg]  # shape: (h, w, 3)

    # ✅ 원본 프레임과 크기 맞추기 + 블렌딩
    frame_resized = cv2.resize(frame, (seg.shape[1], seg.shape[0]))
    blended = cv2.addWeighted(frame_resized, 0.5, color_seg, 0.5, 0)

    # ✅ 저장
    out.write(blended)

    print(f"\r[INFO] Processing frame {frame_index}", end="")
    frame_index += 1

# ✅ 마무리
cap.release()
out.release()
cv2.destroyAllWindows()
print("\nDone: Segmented video saved.")
