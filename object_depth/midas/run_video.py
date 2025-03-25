import cv2
import onnxruntime
import numpy as np
import os

# 🔧 설정
onnx_model_path = "object_depth\midas\midas_small.onnx"     # 모델 경로
input_video_path = "short_video.mp4"           # 입력 비디오
output_video_path = "object_depth\midas/depth_midas_output.mp4"  # 출력 비디오
input_size = 128  # midas_small.onnx는 128x128 입력 사용

# ONNX 세션 시작
session = onnxruntime.InferenceSession(onnx_model_path, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# 비디오 로드
cap = cv2.VideoCapture(input_video_path)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# 출력 디렉토리 생성
os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

print("MiDaS-small ONNX로 동영상 변환 시작...")

for frame_idx in range(frame_total):
    ret, frame = cap.read()
    if not ret:
        break

    # 전처리
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) / 255.0
    img = cv2.resize(img, (input_size, input_size))
    input_tensor = img.transpose(2, 0, 1).astype(np.float32)[np.newaxis, ...]

    # 추론
    depth = session.run([output_name], {input_name: input_tensor})[0]
    depth = np.squeeze(depth)
    depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]))

    # 정규화 및 컬러맵
    depth_norm = ((depth - depth.min()) / (depth.max() - depth.min()) * 255.0).astype(np.uint8)
    depth_colormap = cv2.applyColorMap(depth_norm, cv2.COLORMAP_INFERNO)

    # 프레임 합치기
    # combined = cv2.hconcat([frame, depth_colormap])
    out.write(depth_colormap)

    print(f"\rFrame {frame_idx + 1}/{frame_total}", end="")

cap.release()
out.release()
print("\n완료! 저장된 파일:", output_video_path)
