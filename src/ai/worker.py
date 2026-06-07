# Module xử lý AI luồng ngầm (YOLOv8, OpenCV, Object Tracking & Line Crossing)
import cv2
import time
from ultralytics import YOLO
from src import config
from src.robot.communication import send_coordinates_to_robot

def run_ai_worker(model_path, source_type, video_filepath, data_queue, is_running_check, conf, iou, device, tracker_type):
    """
    Hàm thực thi luồng phụ xử lý AI:
    - Đọc ảnh từ Camera/Video.
    - Thực hiện dự đoán kèm bám vết (Object Tracking) bằng YOLOv8.
    - Phát hiện sự kiện Line Crossing (Cắt vạch).
    - Tách tác vụ resize và chuyển đổi hệ màu ảnh sang luồng phụ trước khi đẩy về UI.
    """
    data_queue.put(("log", "🧠 Đang khởi tạo mô hình YOLOv8..."))
    try:
        model = YOLO(model_path)
    except Exception as e:
        data_queue.put(("log", f"❌ Lỗi nạp mô hình: {e}"))
        return

    # Xác định nguồn phát (Webcam hoặc Video)
    media_source = config.CAMERA_INDEX if source_type == 0 else video_filepath
    cap = cv2.VideoCapture(media_source)
    
    if source_type == 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    data_queue.put(("log", f"▶️ Đã kết nối nguồn hình ảnh: {media_source}"))
    
    # Tập hợp các ID vật thể đã được xử lý gửi sang robot (để tránh trùng lặp)
    processed_ids = set()
    # Lưu lịch sử tọa độ Y của vật thể để xác định sự kiện cắt vạch (line crossing)
    object_history = {}
    
    # Thiết lập cấu hình tệp tin tracker của YOLO
    tracker_config = "bytetrack.yaml"
    if tracker_type == "BOT-SORT":
        tracker_config = "botsort.yaml"
        
    data_queue.put(("log", f"⚙️ Sử dụng thiết bị: {device.upper()} | Thuật toán bám vết: {tracker_type}"))

    while is_running_check():
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            if source_type == 1:
                # Tự động lặp lại video nếu hết file
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                data_queue.put(("log", "❌ Lỗi: Mất tín hiệu kết nối Camera!"))
                break

        frame_height, frame_width = frame.shape[:2]
        
        # 1. Xác định vạch phát hiện (Trigger Line) chính giữa ảnh
        line_y = frame_height // 2
        
        # 2. Dự đoán và bám vết sử dụng model.track()
        # persist=True để giữ vết ID qua các frame
        try:
            results = model.track(
                source=frame,
                persist=True,
                conf=conf,
                iou=iou,
                device=device,
                tracker=tracker_config,
                verbose=False
            )
        except Exception as e:
            # Ghi nhận lỗi tracker lên UI log để chẩn đoán
            data_queue.put(("log", f"⚠️ Lỗi YOLO track: {e}"))
            results = model.predict(source=frame, conf=conf, iou=iou, device=device, verbose=False)

        annotated_frame = frame.copy()
        
        # Vẽ vạch trigger (Vùng bắt tín hiệu nét liền màu xanh dương)
        # Khi có vật thể đang chạm vạch, đổi sang màu đỏ để trực quan
        line_color = (255, 0, 0) # Mặc định: Xanh dương (BGR)
        
        # Kiểm tra hộp kết quả
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            xyxy = boxes.xyxy.cpu().numpy()
            
            # Đọc danh sách ID được YOLO tracking gán cho mỗi vật thể
            # Nếu không có ID (ví dụ chưa bám vết được), ta lấy mảng None
            ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()
            
            for i, box in enumerate(xyxy):
                x_min, y_min, x_max, y_max = map(int, box)
                center_x = (x_min + x_max) // 2
                center_y = (y_min + y_max) // 2
                
                obj_id = ids[i]
                class_name = model.names[cls_ids[i]]
                confidence = confidences[i]
                
                # --- Thuật toán Line Crossing (Cắt vạch) ---
                # Chỉ kích hoạt sự kiện khi tâm vật thể thực sự cắt qua vạch từ trên xuống dưới
                if obj_id is not None:
                    prev_y = object_history.get(obj_id)
                    object_history[obj_id] = center_y
                    
                    if prev_y is not None:
                        # Hỗ trợ cả hai hướng: Từ trên xuống dưới hoặc từ dưới lên trên
                        is_crossing = (prev_y < line_y and center_y >= line_y) or (prev_y > line_y and center_y <= line_y)
                        if is_crossing and obj_id not in processed_ids:
                            processed_ids.add(obj_id)
                            line_color = (0, 0, 255) # Đổi vạch sang màu đỏ (có vật thể cắt vạch)
                            
                            # Gửi thông tin cắt vạch về luồng UI xử lý tiếp
                            data_queue.put(("target_crossed", {
                                "id": obj_id,
                                "class_name": class_name,
                                "x": center_x,
                                "y": center_y
                            }))
                            
                            # Gọi truyền thông TCP gửi dữ liệu sang Robot (tương thích 100% giaothuc.py)
                            #send_coordinates_to_robot(class_name, center_x, center_y, data_queue)
                        
                    # Giải phóng bộ nhớ khi vật thể đi ra ngoài màn hình (cả biên trên và biên dưới)
                    if center_y > frame_height - 15 or center_y < 15:
                        if obj_id in processed_ids:
                            processed_ids.remove(obj_id)
                        if obj_id in object_history:
                            del object_history[obj_id]
                
                # Thiết lập màu vẽ bounding box: Xanh lá nếu đã gắp/cắt vạch, Cam nếu chưa gắp
                color = (0, 255, 0) if (obj_id in processed_ids) else (0, 165, 255)
                
                # Vẽ bounding box và chấm tâm đối tượng
                cv2.rectangle(annotated_frame, (x_min, y_min), (x_max, y_max), color, 2)
                cv2.circle(annotated_frame, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Hiển thị text: Nhãn, ID bám vết và độ tin cậy
                id_str = f"ID:{obj_id} " if obj_id is not None else ""
                label = f"{id_str}{class_name} ({confidence:.2f})"
                cv2.putText(annotated_frame, label, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Vẽ vạch trigger line lên màn hình camera
        cv2.line(annotated_frame, (0, line_y), (frame_width, line_y), line_color, 3)
        cv2.putText(annotated_frame, "TRIGGER LINE", (10, line_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, line_color, 2)

        # --- TỐI ƯU HÓA HIỆU NĂNG LUỒNG UI CHÍNH ---
        # Resize ảnh hiển thị trực tiếp bằng C++ OpenCV trên luồng phụ
        display_width = 640
        display_height = int(display_width * frame_height / frame_width)
        resized_frame = cv2.resize(annotated_frame, (display_width, display_height))
        
        # Chuyển đổi định dạng màu sang RGB để tương thích Tkinter PIL
        rgb_image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        data_queue.put(("image", rgb_image))
        
        # Tránh phình bộ nhớ cho object_history và processed_ids khi chạy lâu
        if len(object_history) > 1000:
            active_ids = list(object_history.keys())[-500:]
            object_history = {k: object_history[k] for k in active_ids}
            processed_ids = {k for k in processed_ids if k in object_history}
            
        # Kiểm soát tốc độ quét để ổn định CPU
        time.sleep(config.AI_LOOP_DELAY_SEC)

    cap.release()
    data_queue.put(("log", "⏹️ Đã dừng giải phóng Camera."))
