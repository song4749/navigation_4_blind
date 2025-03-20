import torch
import cv2
import numpy as np

# MiDaS Hybrid 모델 로드
model_type = "DPT_Hybrid"
midas = torch.hub.load("intel-isl/MiDaS", model_type)
midas.to("cpu")
midas.eval()

# MiDaS 모델의 공식 전처리 적용
transform = torch.hub.load("intel-isl/MiDaS", "transforms").dpt_transform

# 웹캠 열기
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 장애물 감지 임계값
threshold = 100

# MiDaS Hybrid 모델을 이용한 깊이 예측 함수
def run_depth_estimation(image):
    # BGR → RGB 변환
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # 공식 전처리 적용 (이미 배치 차원 포함된 텐서를 반환)
    img = transform(img)
    
    # 디버깅용: 입력 텐서 크기 확인
    print(f"Input Tensor Shape: {img.shape}")  # 예상: torch.Size([1, 3, 384, 512]) 또는 유사 형태
    
    # 모델 실행
    with torch.no_grad():
        depth_map = midas(img)
    
    # 디버깅용: 출력 텐서 크기 확인
    print(f"Output Tensor Shape: {depth_map.shape}")
    
    # 배치(및 채널) 차원 제거 후 numpy 배열로 변환
    depth_map = depth_map.squeeze().cpu().numpy()
    
    # 원본 크기로 리사이즈
    return cv2.resize(depth_map, (image.shape[1], image.shape[0]))

# 창 크기 설정
cv2.namedWindow("Webcam & Depth Map", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Webcam & Depth Map", 960, 540)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 깊이 예측 수행
    depth_map_disp = run_depth_estimation(frame)

    # 깊이 맵을 컬러맵으로 변환
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_map_disp, alpha=255.0 / depth_map_disp.max()), cv2.COLORMAP_INFERNO)

    # 장애물 감지 (중앙 영역 분석)
    h, w = depth_map_disp.shape
    center_region = depth_map_disp[h // 3: 2 * h // 3, w // 3: 2 * w // 3]
    center_min_depth = np.percentile(center_region, 10)

    if center_min_depth < threshold:
        cv2.putText(frame, "WARNING: Obstacle detected!", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3, cv2.LINE_AA)

    # 원본 영상과 깊이 맵 크기를 축소하여 나란히 배치
    new_size = (frame.shape[1] // 2, frame.shape[0] // 2)
    frame_resized = cv2.resize(frame, new_size)
    depth_colormap_resized = cv2.resize(depth_colormap, new_size)

    # 좌우로 결합
    combined_output = cv2.hconcat([frame_resized, depth_colormap_resized])

    # 영상 출력
    cv2.imshow("Webcam & Depth Map", combined_output)

    # ESC 키 입력 시 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
