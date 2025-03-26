from transformers import SegformerFeatureExtractor
from optimum.onnxruntime import ORTModelForSemanticSegmentation

# 모델 ID 설정
model_id = "nvidia/segformer-b2-finetuned-cityscapes-1024-1024"

# Feature extractor 로드 및 저장
feature_extractor = SegformerFeatureExtractor.from_pretrained(model_id)
feature_extractor.save_pretrained("segformer_b2_cityscapes_onnx")

# ONNX 모델 변환 및 저장
onnx_model = ORTModelForSemanticSegmentation.from_pretrained(model_id, export=True)
onnx_model.save_pretrained("segformer_b2_cityscapes_onnx")

print("모델이 성공적으로 ONNX 형식으로 변환되어 저장되었습니다.")