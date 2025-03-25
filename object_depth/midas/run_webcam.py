import cv2
import numpy as np
import onnxruntime  # ONNX 모델 실행용

# OpenCV 멀티스레딩 설정 (선택)
cv2.setNumThreads(4)

# ONNX 모델 로드
onnx_model_path = "object_depth/midas/midas_small.onnx"  # 경로 구분자 수정
ort_session = onnxruntime.InferenceSession(onnx_model_path)

# 웹캠 열기
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 🔹 ONNX 모델을 이용한 깊이 예측 함수
def run_depth_estimation(image):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
    img = cv2.resize(img, (128, 128))  # 입력 크기
    input_tensor = img.transpose(2, 0, 1).astype(np.float32)
    input_tensor = np.expand_dims(input_tensor, axis=0)

    outputs = ort_session.run(None, {"input": input_tensor})
    depth_map = outputs[0].squeeze()
    return cv2.resize(depth_map, (image.shape[1], image.shape[0]))

# 창 설정
cv2.namedWindow("Webcam & Depth Map", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Webcam & Depth Map", 960, 540)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 깊이 추정
    depth_map_disp = run_depth_estimation(frame)

    # 깊이맵 시각화
    depth_colormap = cv2.applyColorMap(
        cv2.convertScaleAbs(depth_map_disp, alpha=255.0 / depth_map_disp.max()),
        cv2.COLORMAP_INFERNO
    )

    # 원본 & 깊이맵 축소 후 결합
    new_size = (frame.shape[1] // 2, frame.shape[0] // 2)
    frame_resized = cv2.resize(frame, new_size)
    depth_resized = cv2.resize(depth_colormap, new_size)
    combined_output = cv2.hconcat([frame_resized, depth_resized])

    cv2.imshow("Webcam & Depth Map", combined_output)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC 키
        break

cap.release()
cv2.destroyAllWindows()
