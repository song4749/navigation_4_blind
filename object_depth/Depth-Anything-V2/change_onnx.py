import torch
from depth_anything_v2.dpt import DepthAnythingV2

# 🔧 base 모델 설정 (vitb)
model = DepthAnythingV2(
    encoder='vitb',
    features=128,
    out_channels=[96, 192, 384, 768]
)

# 🔐 체크포인트 로드
ckpt_path = "object_depth/Depth-Anything-V2/checkpoints/depth_anything_v2_vitb.pth"
model.load_state_dict(torch.load(ckpt_path, map_location="cpu"))
model.eval()

# 🧪 더미 입력 (1, 3, 518, 518)
dummy_input = torch.randn(1, 3, 518, 518)

# 💾 ONNX 변환
torch.onnx.export(
    model,
    dummy_input,
    "depth_anything_v2_vitb.onnx",      # base 모델용 출력 파일명
    input_names=["input"],
    output_names=["depth"],
    opset_version=11,
    do_constant_folding=True,
    dynamic_axes={"input": {0: "batch_size"}, "depth": {0: "batch_size"}}
)

print("ONNX 변환 완료: depth_anything_v2_vitb.onnx")
