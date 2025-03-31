import os
import cv2
import numpy as np
import onnxruntime

# 정확한 ONNX 파일 경로 설정
model_path = os.path.join(os.path.dirname(__file__), "../../road_segmentation/road_segmentation_small.onnx")
model_path = os.path.abspath(model_path)

try:
    seg_model = onnxruntime.InferenceSession(
        model_path,
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    # print("[INFO] ONNX 세그멘테이션 모델 로드 성공")
except Exception as e:
    seg_model = None
    print("[ERROR] ONNX 모델 로드 실패:", e)

# 클래스 매핑 (학습 config 기준)
# 0: alley, 1: bike_lane, 2: braille_guide_blocks, 3: caution_zone, 4: roadway, 5: sidewalk

def preprocess_segmentation_input(image, size=(512, 512)):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
    img = cv2.resize(img, size)
    img = img.transpose(2, 0, 1).astype(np.float32)
    return np.expand_dims(img, axis=0)

def segment_sidewalk_road(image):
    if seg_model is None:
        raise RuntimeError("Segmentation model not loaded.")
    input_tensor = preprocess_segmentation_input(image)
    input_name = seg_model.get_inputs()[0].name
    output = seg_model.run(None, {input_name: input_tensor})[0]
    seg_map = output.argmax(1)[0]
    seg_map = cv2.resize(seg_map.astype(np.uint8), (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    return seg_map
