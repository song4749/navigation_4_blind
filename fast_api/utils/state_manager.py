import time
import numpy as np
from fast_api.utils.audio_map import warning_audio_map, priority_order
from fast_api.models.segmentation import segment_sidewalk_road

# === 상태 변수들 ===
no_block_start_time = None
previous_statuses = {}
message_counter = {}
current_display_warnings = []
last_audio_filename = None
is_audio_playing = False
danger_warning_boxes = {}

def reset_audio_status():
    global is_audio_playing
    is_audio_playing = False

def set_audio_playing():
    global is_audio_playing
    is_audio_playing = True

def extract_warnings(frame, block_results, obstacle_results, depth_map):
    global no_block_start_time
    global message_counter, current_display_warnings, last_audio_filename
    global is_audio_playing, previous_statuses, danger_warning_boxes

    start_time = time.time()
    temp_warnings = []
    frame_height, frame_width = frame.shape[:2]

    has_block = False
    stop_box = None

    # === 점자블록 판단 ===
    for r in block_results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id].lower()

            if class_name in ["stop", "go_forward"]:
                has_block = True
            if class_name == "stop" and y2 > frame_height * 0.9:
                stop_box = (x1, y1, x2, y2)

    # === 정지 블록 기반 방향 안내 ===
    if stop_box:
        x1_s, y1_s, x2_s, y2_s = stop_box
        stop_center_x = (x1_s + x2_s) / 2
        stop_center_y = (y1_s + y2_s) / 2

        left, right, above, below = False, False, False, False

        for r in block_results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                class_name = r.names[cls_id].lower()

                if class_name == "go_forward":
                    cx_g = (x1 + x2) / 2
                    cy_g = (y1 + y2) / 2

                    if cx_g < stop_center_x - 30:
                        left = True
                    elif cx_g > stop_center_x + 30:
                        right = True
                    if cy_g < stop_center_y - 30:
                        above = True
                    elif cy_g > stop_center_y + 30:
                        below = True

        if left and not right and not above and not below:
            temp_warnings.append("Turn Left.")
        elif right and not left and not above and not below:
            temp_warnings.append("Turn Right.")
        elif above and not left and not right and not below:
            temp_warnings.append("Pause at the stop block.")
        elif below and not left and not right and not above:
            temp_warnings.append("Stop sign detected! Please stop.")
        elif not left and not right and not above and not below:
            temp_warnings.append("Stop sign detected! Please stop.")
        else:
            temp_warnings.append("Pause and decide direction at stop block.")

    # === 점자블록 중심 벗어남 판단 ===
    for r in block_results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            class_name = r.names[cls_id].lower()
            if class_name == "go_forward":
                cx = int((x1 + x2) / 2)
                if cx < frame_width * 0.3:
                    temp_warnings.append("Off the guide block. Move left.")
                elif cx > frame_width * 0.7:
                    temp_warnings.append("Off the guide block. Move right.")

    # === 장애물 위험 판단 ===
    current_box_ids = set()
    for r in obstacle_results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            depth_value = depth_map[cy, cx]
            is_center = frame_width * 0.4 <= cx <= frame_width * 0.6
            box_id = f"{cx//20}_{cy//20}"
            current_box_ids.add(box_id)

            current_status = "Danger" if depth_value > 0.2 else "Warning" if depth_value > 0.1 else "Safe"

            if box_id in previous_statuses:
                prev_status = previous_statuses[box_id]
                if prev_status == "Warning" and current_status == "Danger" and is_center:
                    text = "RIGHT" if cx < frame_width * 0.5 else "LEFT"
                    msg = f"Danger Increasing! Be careful! Move {text} to avoid obstacle!"
                    temp_warnings.append(msg)
                    danger_warning_boxes[box_id] = (msg, time.time())

            previous_statuses[box_id] = current_status

            if box_id in danger_warning_boxes and not is_center:
                del danger_warning_boxes[box_id]

    for box_id, (msg, _) in list(danger_warning_boxes.items()):
        if box_id not in current_box_ids:
            del danger_warning_boxes[box_id]
        elif msg not in temp_warnings:
            temp_warnings.append(msg)

    # === 점자블록 미탐지 시 세그멘테이션 기반 경고 ===
    if not has_block:
        if no_block_start_time is None:
            no_block_start_time = time.time()
        elif time.time() - no_block_start_time >= 1.0:
            temp_warnings.append("No guide block detected.")
    else:
        no_block_start_time = None
        message_counter.pop("No guide block detected.", None)

    if "No guide block detected." in temp_warnings:
        seg_map = segment_sidewalk_road(frame)
        h, w = seg_map.shape
        bottom_region = seg_map[int(h * 0.7):, :]

        left_half = bottom_region[:, :w // 2]
        right_half = bottom_region[:, w // 2:]

        ROAD_CLASSES = [0, 4]

        left_ratio = np.mean(np.isin(left_half, ROAD_CLASSES))
        right_ratio = np.mean(np.isin(right_half, ROAD_CLASSES))

        if left_ratio > 0.2 and left_ratio > right_ratio:
            temp_warnings.append("Road detected on the LEFT. Move right to stay on the sidewalk.")
        elif right_ratio > 0.2 and right_ratio > left_ratio:
            temp_warnings.append("Road detected on the RIGHT. Move left to stay on the sidewalk.")

    # === 경고 카운트 및 출력 확정 ===
    confirmed_warnings = []
    for w in temp_warnings:
        message_counter[w] = message_counter.get(w, 0) + 1
        if message_counter[w] >= 4:
            confirmed_warnings.append(w)

    # 오래된 메시지는 제거
    keys_to_delete = [k for k in message_counter if k not in temp_warnings]
    for k in keys_to_delete:
        del message_counter[k]

    audio_filename = None
    if confirmed_warnings:
        confirmed_warnings.sort(key=lambda w: priority_order.get(w, 99))
        new_warning = confirmed_warnings[0]
        if not current_display_warnings or new_warning != current_display_warnings[0]:
            current_display_warnings = [new_warning]
            if new_warning in warning_audio_map:
                filename = warning_audio_map[new_warning]
                if filename != last_audio_filename and not is_audio_playing:
                    audio_filename = filename
                    last_audio_filename = filename
                    is_audio_playing = True
    else:
        current_display_warnings = []
        last_audio_filename = None
        is_audio_playing = False

    print(f"[DEBUG] Processed in {int((time.time() - start_time)*1000)} ms | Warning: {current_display_warnings}")
    return current_display_warnings, audio_filename
