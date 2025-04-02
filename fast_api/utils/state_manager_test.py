# import time
# import numpy as np
# from fast_api.utils.audio_map import warning_audio_map, priority_order
# from fast_api.models.segmentation import segment_sidewalk_road

# # === 상태 변수들 ===
# stop_detected_time = None
# stop_message_displayed = False
# no_block_start_time = None
# stop_hold_seconds = 3
# previous_statuses = {}
# message_counter = {}
# current_display_warnings = []
# last_audio_filename = None
# is_audio_playing = False
# danger_warning_boxes = {}
# turn_guidance_active = {
#     "Turn Left.": False,
#     "Turn Right.": False
# }
# guide_block_off_center = {
#     "Off the guide block. Move left.": False,
#     "Off the guide block. Move right.": False
# }

# # === 외부 접근용 상태 함수 ===
# def reset_audio_status():
#     global is_audio_playing
#     is_audio_playing = False

# def set_audio_playing():
#     global is_audio_playing
#     is_audio_playing = True

# def extract_warnings(frame, block_results, obstacle_results, depth_map):
#     global stop_detected_time, stop_message_displayed, no_block_start_time
#     global message_counter, current_display_warnings, last_audio_filename
#     global is_audio_playing, previous_statuses, danger_warning_boxes

#     start_time = time.time()
#     temp_warnings = []
#     frame_height, frame_width = frame.shape[:2]

#     # 초기화
#     turn_guidance_active["Turn Left."] = False
#     turn_guidance_active["Turn Right."] = False
#     guide_block_off_center["Off the guide block. Move left."] = False
#     guide_block_off_center["Off the guide block. Move right."] = False

#     has_block = False
#     skip_other_guidance = False

#     # === 점자블록 판단 ===
#     for r in block_results:
#         for box in r.boxes:
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             cls_id = int(box.cls[0])
#             class_name = r.names[cls_id]

#             if class_name.lower() in ["stop", "go_forward"]:
#                 has_block = True
#             if class_name.lower() == "stop" and y2 > frame_height * 0.95:
#                 if stop_detected_time is None:
#                     stop_detected_time = time.time()
#                     stop_message_displayed = False

#                 if time.time() - stop_detected_time < stop_hold_seconds:
#                     if not stop_message_displayed:
#                         temp_warnings.append("Stop sign detected! Please stop.")
#                         stop_message_displayed = True
#                     skip_other_guidance = True

#     if stop_detected_time and time.time() - stop_detected_time >= stop_hold_seconds:
#         stop_detected_time = None
#         stop_message_displayed = False
#     elif stop_detected_time:
#         skip_other_guidance = True

#     # === 점자블록 기반 회전 유도 ===
#     if not skip_other_guidance:
#         for r in block_results:
#             for box in r.boxes:
#                 x1, y1, x2, y2 = map(int, box.xyxy[0])
#                 cls_id = int(box.cls[0])
#                 class_name = r.names[cls_id]
#                 if class_name.lower() != "stop":
#                     cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
#                     w, h = x2 - x1, y2 - y1
#                     ratio = w / h if h else 0

#                     if cx < frame_width * 0.3:
#                         temp_warnings.append("Off the guide block. Move left.")
#                         guide_block_off_center["Off the guide block. Move left."] = True
#                     elif cx > frame_width * 0.7:
#                         temp_warnings.append("Off the guide block. Move right.")
#                         guide_block_off_center["Off the guide block. Move right."] = True

#                     if ratio > 1.5 and cy > frame_height * 0.6:
#                         if cx < frame_width * 0.5:
#                             temp_warnings.append("Turn Left.")
#                             if class_name.lower() == "go_forward":
#                                 turn_guidance_active["Turn Left."] = True
#                         else:
#                             temp_warnings.append("Turn Right.")
#                             if class_name.lower() == "go_forward":
#                                 turn_guidance_active["Turn Right."] = True

#     # === 장애물 깊이 기반 위험 판단 ===
#     current_box_ids = set()
#     for r in obstacle_results:
#         for box in r.boxes:
#             x1, y1, x2, y2 = map(int, box.xyxy[0])
#             cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
#             depth_value = depth_map[cy, cx]
#             is_center = frame_width * 0.3 <= cx <= frame_width * 0.7
#             box_id = f"{cx//20}_{cy//20}"
#             current_box_ids.add(box_id)

#             current_status = "Danger" if depth_value > 0.2 else "Warning" if depth_value > 0.1 else "Safe"

#             if box_id in previous_statuses:
#                 prev_status = previous_statuses[box_id]
#                 if prev_status == "Warning" and current_status == "Danger" and is_center:
#                     text = "RIGHT" if cx < frame_width * 0.5 else "LEFT"
#                     msg = f"Danger Increasing! Be careful! Move {text} to avoid obstacle!"
#                     temp_warnings.append(msg)
#                     danger_warning_boxes[box_id] = (msg, time.time())
#             previous_statuses[box_id] = current_status

#     for box_id, (msg, _) in list(danger_warning_boxes.items()):
#         if box_id not in current_box_ids:
#             del danger_warning_boxes[box_id]
#         elif msg not in temp_warnings:
#             temp_warnings.append(msg)

#     # === 점자블록 미탐지 시 ===
#     if not has_block:
#         if no_block_start_time is None:
#             no_block_start_time = time.time()
#         elif time.time() - no_block_start_time >= 1.0:
#             temp_warnings.append("No guide block detected.")
#     else:
#         no_block_start_time = None
#         message_counter.pop("No guide block detected.", None)

#     # === 점자블록 미탐지 상태일 때만 세그멘테이션 기반 경고 활성화 ===
#     if "No guide block detected." in temp_warnings:
#         seg_map = segment_sidewalk_road(frame)
#         h, w = seg_map.shape
#         bottom_region = seg_map[int(h * 0.7):, :]

#         left_half = bottom_region[:, :w // 2]
#         right_half = bottom_region[:, w // 2:]

#         ROAD_CLASSES = [0, 4]  # alley, roadway

#         left_ratio = np.mean(np.isin(left_half, ROAD_CLASSES))
#         right_ratio = np.mean(np.isin(right_half, ROAD_CLASSES))

#         if left_ratio > 0.2 and left_ratio > right_ratio:
#             temp_warnings.append("Road detected on the LEFT. Move right to stay on the sidewalk.")
#         elif right_ratio > 0.2 and right_ratio > left_ratio:
#             temp_warnings.append("Road detected on the RIGHT. Move left to stay on the sidewalk.")

#     # === 조건 해제 시 카운트 제거 ===
#     for msg in ["Turn Left.", "Turn Right."]:
#         if not turn_guidance_active[msg]:
#             message_counter.pop(msg, None)
#     for msg in ["Off the guide block. Move left.", "Off the guide block. Move right."]:
#         if not guide_block_off_center[msg]:
#             message_counter.pop(msg, None)

#     # === 확정 경고문 ===
#     confirmed_warnings = []
#     for w in temp_warnings:
#         message_counter[w] = message_counter.get(w, 0) + 1
#         if message_counter[w] >= 4:
#             confirmed_warnings.append(w)

#     def get_priority(w):
#         if w in [
#             "Road detected on the LEFT. Move right to stay on the sidewalk.",
#             "Road detected on the RIGHT. Move left to stay on the sidewalk."
#         ]:
#             return 98
#         return priority_order.get(w, 99)

#     audio_filename = None
#     if confirmed_warnings:
#         confirmed_warnings.sort(key=get_priority)
#         new_warning = confirmed_warnings[0]
#         if not current_display_warnings or new_warning != current_display_warnings[0]:
#             current_display_warnings = [new_warning]
#             if new_warning in warning_audio_map:
#                 filename = warning_audio_map[new_warning]
#                 if filename != last_audio_filename and not is_audio_playing:
#                     audio_filename = filename
#                     last_audio_filename = filename
#                     is_audio_playing = True
#     else:
#         current_display_warnings = []
#         last_audio_filename = None
#         is_audio_playing = False

#     print(f"[DEBUG] Processed in {int((time.time() - start_time)*1000)} ms | Warning: {current_display_warnings}")
#     return current_display_warnings, audio_filename
