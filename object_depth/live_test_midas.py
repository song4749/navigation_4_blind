import cv2
import numpy as np
import onnxruntime  # ONNX 모델 실행용

# OpenCV 멀티스레딩 활성화
cv2.setNumThreads(4)

# ONNX 모델 로드
onnx_model_path = "object_depth\midas_small.onnx"  # 변환된 ONNX 모델 파일 경로
ort_session = onnxruntime.InferenceSession(onnx_model_path)

# 웹캠 열기
cap = cv2.VideoCapture(0)  # 0: 기본 웹캠, 1: 외부 카메라
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 웹캠 FPS 가져오기 (사용 불가능하면 기본 30FPS 적용)
video_fps = cap.get(cv2.CAP_PROP_FPS)
if video_fps == 0:
    video_fps = 30  # 기본값 설정
target_frame_time = 1 / video_fps  # 목표 프레임 간격

# 장애물 감지 임계값
threshold = 100

# 🔹 ONNX 모델을 이용한 깊이 예측 함수
def run_depth_estimation(image):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0  # RGB 변환 및 정규화
    img = cv2.resize(img, (128, 128))  # ONNX 모델 입력 크기로 조정
    input_tensor = img.transpose(2, 0, 1).astype(np.float32)  # (H, W, C) → (C, H, W)
    input_tensor = np.expand_dims(input_tensor, axis=0)  # 배치 차원 추가 (1, 3, 128, 128)

    # ONNX 추론 실행
    outputs = ort_session.run(None, {"input": input_tensor})

    # 깊이 맵 후처리
    depth_map = outputs[0].squeeze()
    return cv2.resize(depth_map, (image.shape[1], image.shape[0]))  # 원본 크기로 확대

# 창 크기 고정
cv2.namedWindow("Webcam & Depth Map", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Webcam & Depth Map", 960, 540)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # ONNX 모델을 이용한 깊이 예측 수행
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

    # 두 개 화면을 좌우로 붙임
    combined_output = cv2.hconcat([frame_resized, depth_colormap_resized])

    # 영상 출력
    cv2.imshow("Webcam & Depth Map", combined_output)

    # ESC 키 입력 시 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()