import torch

# MiDaS Small 모델 로드
model_type = "MiDaS_small"
midas = torch.hub.load("intel-isl/MiDaS", model_type)
midas.eval()

# 더 작은 해상도로 변환 (128x128)
dummy_input = torch.randn(1, 3, 128, 128)  # 배치 크기=1, 채널=3, 높이=128, 너비=128

# 모델을 ONNX로 변환
torch.onnx.export(
    midas, 
    dummy_input, 
    "object_depth\midas_small.onnx",  # 저장할 ONNX 모델 파일명
    opset_version=11,  # ONNX 변환 시 사용할 Opset 버전
    input_names=["input"],  # 입력 텐서 이름
    output_names=["output"],  # 출력 텐서 이름
    dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}  # 동적 배치 크기 지원
)

print("MiDaS Small 모델이 ONNX로 변환 완료!")