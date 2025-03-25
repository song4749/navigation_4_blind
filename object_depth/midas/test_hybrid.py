import torch
import cv2
import numpy as np
import os

# 📌 설정
input_video_path = "short_video.mp4"
output_video_path = "depth_output_midas_hybrid.mp4"

# 🔹 모델 로드
model_type = "DPT_Hybrid"
midas = torch.hub.load("intel-isl/MiDaS", model_type)
midas.to("cpu")
midas.eval()

# 🔹 공식 전처리
transform = torch.hub.load("intel-isl/MiDaS", "transforms").dpt_transform

# 🔹 비디오 열기
cap = cv2.VideoCapture(input_video_path)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# 🔹 출력 비디오 설정
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

print("MiDaS Hybrid로 영상 처리 시작...")

# 🔹 프레임 반복 처리
for frame_idx in range(frame_total):
    ret, frame = cap.read()
    if not ret:
        break

    print(f"\rFrame {frame_idx + 1}/{frame_total}", end="")

    # 깊이 추론
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    input_tensor = transform(img).to("cpu")

    with torch.no_grad():
        depth = midas(input_tensor)

    depth_map = depth.squeeze().cpu().numpy()
    depth_map = cv2.resize(depth_map, (frame.shape[1], frame.shape[0]))

    # 정규화 및 컬러맵
    depth_norm = ((depth_map - depth_map.min()) / (depth_map.max() - depth_map.min()) * 255.0).astype(np.uint8)
    depth_colormap = cv2.applyColorMap(depth_norm, cv2.COLORMAP_INFERNO)

    # 처리된 프레임만 저장 (원본 없이)
    out.write(depth_colormap)

cap.release()
out.release()
print("\n완료! 저장된 파일:", output_video_path)
