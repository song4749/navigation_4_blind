# import base64
# import cv2
# import numpy as np
# import onnxruntime
# import time
# import io
# import os
# from fastapi import FastAPI, UploadFile, File
# from fastapi.responses import HTMLResponse, JSONResponse
# from fastapi.staticfiles import StaticFiles
# from ultralytics import YOLO
# from pyngrok import ngrok

# app = FastAPI()

# # 정적 오디오 파일 서빙 경로 등록
# app.mount("/static_audio", StaticFiles(directory="fast_api/mp3"), name="static_audio")

# # 전역 변수
# stop_detected_time = None
# stop_message_displayed = False  # 정지 문구 중복 방지용
# no_block_start_time = None
# stop_hold_seconds = 3
# previous_statuses = {}
# message_counter = {}
# last_display_time = 0
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

# # 우선순위 설정
# priority_order = {
#     "Stop sign detected! Please stop.": 0,
#     "Danger Increasing! Be careful! Move RIGHT to avoid obstacle!": 1,
#     "Danger Increasing! Be careful! Move LEFT to avoid obstacle!": 1,
#     "Turn Left.": 2,
#     "Turn Right.": 2,
#     "Off the guide block. Move left.": 3,
#     "Off the guide block. Move right.": 3,
#     "No guide block detected.": 4
# }

# # 문구별 오디오 파일 매핑
# warning_audio_map = {
#     "Stop sign detected! Please stop.": "정지 블록이 있습니다. 정지하세요.mp3",
#     "Danger Increasing! Be careful! Move RIGHT to avoid obstacle!": "장애물 접근중. 오른쪽으로 피하세요.mp3",
#     "Danger Increasing! Be careful! Move LEFT to avoid obstacle!": "장애물 접근중. 왼쪽으로 피하세요.mp3",
#     "Turn Left.": "좌회전하세요.mp3",
#     "Turn Right.": "우회전하세요.mp3",
#     "Off the guide block. Move left.": "점자블록을 벗어나고 있습니다. 왼쪽으로 이동하세요.mp3",
#     "Off the guide block. Move right.": "점자블록을 벗어나고 있습니다. 오른쪽으로 이동하세요.mp3",
#     "No guide block detected.": "점자블록이 탐지되지 않습니다.mp3"
# }

# # 모델 로드
# model_1 = YOLO("object_detection/block_best.onnx", task="detect")
# model_2 = YOLO("object_detection/obstacle_test.onnx", task="detect")
# depth_model = onnxruntime.InferenceSession(
#     "object_depth\\Depth-Anything-V2\\checkpoints\\depth_anything_v2_vitb.onnx",
#     providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
# )

# def preprocess_depth_image(image, size=(518, 518)):
#     img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) / 255.0
#     img = cv2.resize(img, size)
#     img = img.transpose(2, 0, 1).astype(np.float32)
#     return np.expand_dims(img, axis=0)

# def estimate_depth(image):
#     input_tensor = preprocess_depth_image(image)
#     input_name = depth_model.get_inputs()[0].name
#     depth_map = depth_model.run(None, {input_name: input_tensor})[0]
#     depth_map = np.squeeze(depth_map)
#     depth_map = cv2.resize(depth_map, (image.shape[1], image.shape[0]))
#     depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
#     return depth_map

# def extract_warnings(frame, model_1, model_2, estimate_depth):
#     global stop_detected_time, previous_statuses, no_block_start_time
#     global message_counter, current_display_warnings, last_audio_filename, is_audio_playing
#     global danger_warning_boxes

#     start_time = time.time()
#     temp_warnings = []
#     frame_height, frame_width = frame.shape[:2]

#     # 초기화 (프레임마다)
#     turn_guidance_active["Turn Left."] = False
#     turn_guidance_active["Turn Right."] = False
#     guide_block_off_center["Off the guide block. Move left."] = False
#     guide_block_off_center["Off the guide block. Move right."] = False

#     results_1 = list(model_1.predict(frame, imgsz=640, conf=0.5, device=0, stream=True))
#     results_2 = list(model_2.predict(frame, imgsz=640, conf=0.5, device=0, stream=True))
#     depth_map = estimate_depth(frame)

#     has_block = False
#     skip_other_guidance = False

#     # 점자블록 처리
#     for r in results_1:
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

#     # 3초 경과 후 상태 초기화
#     if stop_detected_time and time.time() - stop_detected_time >= stop_hold_seconds:
#         stop_detected_time = None
#         stop_message_displayed = False
#     elif stop_detected_time:
#         skip_other_guidance = True

#     if not skip_other_guidance:
#         for r in results_1:
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

#     # 장애물 위험도 추적
#     current_box_ids = set()
#     for r in results_2:
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

#     # 점자블록 미탐지 시
#     if not has_block:
#         if no_block_start_time is None:
#             no_block_start_time = time.time()
#         elif time.time() - no_block_start_time >= 1.0:
#             temp_warnings.append("No guide block detected.")
#     else:
#         no_block_start_time = None
#         message_counter.pop("No guide block detected.", None)

#     # 조건 해제 시 카운트 제거
#     for msg in ["Turn Left.", "Turn Right."]:
#         if not turn_guidance_active[msg]:
#             message_counter.pop(msg, None)
#     for msg in ["Off the guide block. Move left.", "Off the guide block. Move right."]:
#         if not guide_block_off_center[msg]:
#             message_counter.pop(msg, None)

#     # 확정된 경고문
#     confirmed_warnings = []
#     for w in temp_warnings:
#         message_counter[w] = message_counter.get(w, 0) + 1
#         if message_counter[w] >= 4:
#             confirmed_warnings.append(w)

#     def get_priority(w): return priority_order.get(w, 99)

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


# @app.get("/")
# async def index():
#     html_content = """
#     <html>
#     <head><title>Mobile Real-Time Test</title></head>
#     <body>
#         <h1>Mobile Camera Stream and Warnings</h1>
#         <video id="video" autoplay playsinline width="640" height="640" style="border:1px solid black;"></video><br>
#         <h2>Warnings:</h2>
#         <div id="warnings" style="font-size:20px; color:red;"></div>
#         <script>
#             const video = document.getElementById("video");
#             const warningsDiv = document.getElementById("warnings");
#             let currentAudio = null;

#             navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 640, facingMode: "environment" } })
#             .then(stream => { video.srcObject = stream; })
#             .catch(err => { console.error("Error accessing camera:", err); });

#             async function sendFrame() {
#                 const tempCanvas = document.createElement("canvas");
#                 tempCanvas.width = 640;
#                 tempCanvas.height = 640;
#                 const tempCtx = tempCanvas.getContext("2d");
#                 tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
#                 tempCanvas.toBlob(async blob => {
#                     const formData = new FormData();
#                     formData.append("file", blob, "frame.jpg");
#                     try {
#                         const start = performance.now();
#                         const response = await fetch("/process_warning", {
#                             method: "POST",
#                             body: formData
#                         });
#                         const data = await response.json();
#                         const end = performance.now();
#                         console.log(`Response Time: ${(end - start).toFixed(1)} ms`);
#                         warningsDiv.innerHTML = data.warnings.join("<br>");
#                         if (data.audio_url) {
#                             if (!currentAudio || currentAudio.ended) {
#                                 currentAudio = new Audio(data.audio_url);
#                                 currentAudio.play();
#                                 currentAudio.onended = () => {
#                                     fetch("/audio_finished");
#                                 }
#                             }
#                         }
#                     } catch (err) {
#                         console.error("Error sending frame:", err);
#                     }
#                 }, "image/jpeg");
#             }

#             setInterval(sendFrame, 200);
#         </script>
#     </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)

# @app.post("/process_warning")
# async def process_warning(file: UploadFile = File(...)):
#     contents = await file.read()
#     np_arr = np.frombuffer(contents, np.uint8)
#     frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
#     warnings, audio_filename = extract_warnings(frame, model_1, model_2, estimate_depth)
#     audio_url = f"/static_audio/{audio_filename}" if audio_filename else None
#     return JSONResponse(content={"warnings": warnings, "audio_url": audio_url})

# @app.get("/audio_finished")
# async def audio_finished():
#     global is_audio_playing
#     is_audio_playing = False
#     return JSONResponse(content={"status": "ok"})

# public_url = ngrok.connect(8000)
# print("Ngrok Public URL:", public_url)
