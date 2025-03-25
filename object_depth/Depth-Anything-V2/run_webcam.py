import cv2
import torch
import numpy as np
import matplotlib.cm as cm
from depth_anything_v2.dpt import DepthAnythingV2

# 설정
input_size = 518
encoder = "vits"  # ✅ 모델 이름 변경
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
grayscale = False

# 모델 설정 (vits용 구조)
model_configs = {
    'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
}

# 모델 로드
depth_anything = DepthAnythingV2(**model_configs[encoder])
depth_anything.load_state_dict(torch.load(f"object_depth\Depth-Anything-V2\checkpoints\depth_anything_v2_{encoder}.pth", map_location=DEVICE))
depth_anything = depth_anything.to(DEVICE).eval()

cmap = cm.get_cmap('Spectral_r')

# 웹캠 열기
cap = cv2.VideoCapture(0)

print("웹캠 열기 완료. ESC 눌러 종료")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 추론
    depth = depth_anything.infer_image(frame, input_size)
    depth = (depth - depth.min()) / (depth.max() - depth.min()) * 255.0
    depth = depth.astype(np.uint8)

    # 시각화
    if grayscale:
        depth_vis = np.repeat(depth[..., np.newaxis], 3, axis=-1)
    else:
        depth_vis = (cmap(depth)[:, :, :3] * 255).astype(np.uint8)[..., ::-1]

    combined = cv2.hconcat([frame, depth_vis])
    cv2.imshow("Depth Anything V2 - 실시간", combined)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
