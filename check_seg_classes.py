import os
import cv2
import numpy as np
import onnxruntime

def test_segmentation_video(model_path, video_path, output_path, class_colors):
    """
    ONNX 세그멘테이션 모델을 사용하여 동영상 테스트를 수행하고 결과를 저장합니다. (GPU 사용)

    Args:
        model_path (str): ONNX 모델 경로
        video_path (str): 입력 동영상 경로
        output_path (str): 결과 동영상 저장 경로
        class_colors (dict): 클래스 ID별 색상 (예: {0: (255, 0, 0), 1: (0, 255, 0), ...})
    """
    try:
        session = onnxruntime.InferenceSession(model_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]) # GPU 사용
    except Exception as e:
        print(f"[ERROR] ONNX 모델 로드 실패: {e}")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[ERROR] 동영상 파일을 열 수 없습니다.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width * 2, height))

    frame_count = 0
    all_classes = set()

    print("[INFO] 처리 시작...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        seg_map = get_seg_map(frame, session)
        color_map = colorize_seg_map(seg_map, (width, height), class_colors)

        combined = np.hstack((frame, color_map))
        out.write(combined)

        all_classes.update(np.unique(seg_map))
        frame_count += 1
        if frame_count % 10 == 0:
            print(f"[INFO] {frame_count}프레임 완료 - 현재 감지 클래스: {sorted(all_classes)}")

    cap.release()
    out.release()

    print("\n[✅ 완료] 저장된 파일:", output_path)
    print(f"[총 프레임]: {frame_count}")
    print(f"[감지된 클래스]: {sorted(all_classes)}")

def preprocess(image, size=(512, 512)):
    """이미지를 모델 입력 크기에 맞게 전처리합니다."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
    image = cv2.resize(image, size)
    image = image.transpose(2, 0, 1).astype(np.float32)
    return np.expand_dims(image, axis=0)

def get_seg_map(image, session):
    """이미지를 세그멘테이션하고 세그멘테이션 맵을 반환합니다."""
    input_tensor = preprocess(image)
    input_name = session.get_inputs()[0].name
    output = session.run(None, {input_name: input_tensor})[0]
    return np.argmax(output[0], axis=0)

def colorize_seg_map(seg_map, target_shape, class_colors):
    """세그멘테이션 맵에 색상을 입힙니다."""
    seg_map_resized = cv2.resize(seg_map.astype(np.uint8), target_shape, interpolation=cv2.INTER_NEAREST)

    color_map = np.zeros((target_shape[1], target_shape[0], 3), dtype=np.uint8)
    for cls_id, color in class_colors.items():
        mask = seg_map_resized == cls_id
        color_map[mask] = color
    return cv2.cvtColor(color_map, cv2.COLOR_RGB2BGR)

if __name__ == "__main__":
    model_path = "road_segmentation/road_segmentation_small.onnx"  # ONNX 모델 경로
    video_path = "KakaoTalk_20250331_114905657.mp4"  # 입력 동영상 경로
    output_path = "segmented_output.mp4"  # 결과 동영상 저장 경로

    class_colors = {
        0: (255, 0, 0),     # 빨강
        1: (0, 255, 0),     # 초록
        2: (0, 0, 255),     # 파랑
        3: (255, 255, 0),   # 노랑
        4: (255, 0, 255),   # 보라
        5: (0, 255, 255),   # 하늘
    }

    test_segmentation_video(model_path, video_path, output_path, class_colors)