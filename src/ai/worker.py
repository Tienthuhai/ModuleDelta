# Module xử lý AI luồng ngầm (YOLOv8 predict + Centroid Counting - Không dùng Tracking)
import cv2
import time
import math
from ultralytics import YOLO
from src import config
from src.robot.communication import send_coordinates_to_robot


# ---------------------------------------------------------------------------
# CentroidCounter — Đếm vật thể qua vạch không dùng tracking ID
#
# Nguyên lý hoạt động:
#   - Mỗi frame: model.predict() → danh sách bounding box không có ID
#   - Ghép box frame-hiện-tại với box frame-trước bằng khoảng cách tâm
#   - Nếu một vật thể (tâm) đã đi qua vạch: đánh dấu để không đếm lại
#   - Mỗi vật thể "mới" (không khớp với track nào cũ) được gán ID nội bộ tăng dần
# ---------------------------------------------------------------------------
class CentroidCounter:
    MAX_LOST   = 30   # Số frame giữ track sau khi không thấy (tránh mất khi bị che 1-2 frame)
    MAX_DIST   = 300  # Khoảng cách pixel tối đa để ghép detection với track cũ

    def __init__(self):
        self._next_id   = 1
        self._tracks    = {}   # id -> {"cx": int, "cy": int, "lost": int, "crossed": bool}

    def update(self, detections, line_y):
        """
        Cập nhật tracks với danh sách detection mới.
        detections: list of (cx, cy, class_name, confidence)
        Trả về: list of (stable_id, cx, cy, class_name, confidence, just_crossed)
        """
        # Bước 1: Đánh dấu tất cả track hiện có là "chưa thấy trong frame này"
        for t in self._tracks.values():
            t["seen"] = False

        results_out = []

        # Bước 2: Ghép mỗi detection với track gần nhất
        unmatched = list(detections)
        for det in unmatched:
            cx, cy, cls_name, conf = det
            best_id, best_dist = None, self.MAX_DIST

            for tid, t in self._tracks.items():
                d = math.hypot(cx - t["cx"], cy - t["cy"])
                if d < best_dist:
                    best_dist = d
                    best_id = tid

            if best_id is not None:
                # Khớp với track cũ → cập nhật vị trí
                t = self._tracks[best_id]
                prev_y = t["cy"]
                t["cx"], t["cy"] = cx, cy
                t["seen"] = True
                t["lost"] = 0

                # Kiểm tra cắt vạch
                just_crossed = False
                if not t["crossed"]:
                    crossed = (prev_y < line_y and cy >= line_y) or (prev_y > line_y and cy <= line_y)
                    if crossed:
                        t["crossed"] = True
                        just_crossed = True

                results_out.append((best_id, cx, cy, cls_name, conf, just_crossed))
            else:
                # Không khớp track nào → tạo track mới
                new_id = self._next_id
                self._next_id += 1
                self._tracks[new_id] = {
                    "cx": cx, "cy": cy,
                    "seen": True, "lost": 0,
                    "crossed": False
                }
                results_out.append((new_id, cx, cy, cls_name, conf, False))

        # Bước 3: Tăng bộ đếm lost cho track không thấy; xóa nếu quá già
        to_delete = []
        for tid, t in self._tracks.items():
            if not t["seen"]:
                t["lost"] += 1
                if t["lost"] > self.MAX_LOST:
                    to_delete.append(tid)
        for tid in to_delete:
            del self._tracks[tid]

        return results_out

    def clear(self):
        self._tracks.clear()
        self._next_id = 1


def run_ai_worker(model_path, source_type, video_filepath, data_queue, is_running_check, conf, iou, device):
    """
    Hàm thực thi luồng phụ xử lý AI:
    - Đọc ảnh từ Camera/Video.
    - Phát hiện đối tượng bằng model.predict() (không tracking).
    - Đếm vật thể qua vạch bằng CentroidCounter.
    """
    data_queue.put(("log", "🧠 Đang khởi tạo mô hình YOLOv8..."))
    try:
        model = YOLO(model_path)
    except Exception as e:
        data_queue.put(("log", f"❌ Lỗi nạp mô hình: {e}"))
        return

    # Xác định nguồn phát
    media_source = config.CAMERA_INDEX if source_type == 0 else video_filepath
    cap = cv2.VideoCapture(media_source)

    if source_type == 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    data_queue.put(("log", f"▶️ Đã kết nối nguồn hình ảnh: {media_source}"))
    data_queue.put(("log", f"⚙️ Sử dụng thiết bị: {device.upper()} | Chế độ: Phát hiện + Đếm vạch (Không tracking)"))

    counter = CentroidCounter()

    while is_running_check():
        frame_start = time.time()  # Bắt đầu đồng hồ mỗi frame
        ret, frame = cap.read()
        if not ret:
            if source_type == 1:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                counter.clear()
                continue
            else:
                data_queue.put(("log", "❌ Lỗi: Mất tín hiệu kết nối Camera!"))
                break

        frame_height, frame_width = frame.shape[:2]
        line_y = frame_height // 2

        # --- Phát hiện đối tượng (không tracking) ---
        try:
            results = model.predict(
                source=frame,
                conf=conf,
                iou=iou,
                device=device,
                verbose=False
            )
        except Exception as e:
            data_queue.put(("log", f"⚠️ Lỗi YOLO predict: {e}"))
            time.sleep(config.AI_LOOP_DELAY_SEC)
            continue

        # Chuyển kết quả predict thành danh sách (cx, cy, class_name, confidence)
        detections = []
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            xyxy        = boxes.xyxy.cpu().numpy()
            cls_ids     = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()
            for i, box in enumerate(xyxy):
                x_min, y_min, x_max, y_max = map(int, box)
                cx = (x_min + x_max) // 2
                cy = (y_min + y_max) // 2
                detections.append((cx, cy, model.names[cls_ids[i]], float(confidences[i])))

        # --- Cập nhật counter, lấy kết quả ---
        tracked = counter.update(detections, line_y)

        # --- Vẽ kết quả lên frame ---
        annotated_frame = frame.copy()
        line_color = (255, 0, 0)  # Xanh dương mặc định

        for (obj_id, cx, cy, cls_name, conf_val, just_crossed) in tracked:
            # Lấy lại bbox từ danh sách detections theo khoảng cách tâm gần nhất
            # (vẽ bounding box từ results gốc theo index)
            pass

        # Vẽ bounding box từ results gốc (không phụ thuộc vào counter)
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes_raw = results[0].boxes
            xyxy_raw  = boxes_raw.xyxy.cpu().numpy()
            cls_raw   = boxes_raw.cls.cpu().numpy().astype(int)
            conf_raw  = boxes_raw.conf.cpu().numpy()

            for i, box in enumerate(xyxy_raw):
                x_min, y_min, x_max, y_max = map(int, box)
                cx = (x_min + x_max) // 2
                cy = (y_min + y_max) // 2
                cls_name  = model.names[cls_raw[i]]
                conf_val  = conf_raw[i]

                # Tìm stable_id và trạng thái tương ứng từ danh sách tracked
                match_id      = None
                just_crossed  = False
                for (tid, tcx, tcy, tcls, tconf, tcrossed) in tracked:
                    if abs(tcx - cx) < 5 and abs(tcy - cy) < 5:
                        match_id     = tid
                        just_crossed = tcrossed
                        break

                # Màu: xanh lá = đã đếm, cam = chưa qua vạch
                is_crossed = (match_id is not None and
                              match_id in counter._tracks and
                              counter._tracks[match_id]["crossed"])
                color = (0, 255, 0) if is_crossed else (0, 165, 255)

                cv2.rectangle(annotated_frame, (x_min, y_min), (x_max, y_max), color, 3)
                cv2.circle(annotated_frame, (cx, cy), 7, (0, 0, 255), -1)

                id_str   = f"ID:{match_id}" if match_id is not None else "ID:?"
                line1    = f"{id_str}  {cls_name}  {conf_val:.2f}"
                line2    = f"x:{cx} y:{cy}"

                font       = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.65
                thickness  = 2
                pad        = 6

                (w1, h1), _ = cv2.getTextSize(line1, font, font_scale, thickness)
                (w2, h2), _ = cv2.getTextSize(line2, font, font_scale, thickness)
                box_w = max(w1, w2) + pad * 2
                box_h = h1 + h2 + pad * 3

                label_y = max(y_min - box_h - 4, 0)
                overlay = annotated_frame.copy()
                cv2.rectangle(overlay,
                              (x_min, label_y),
                              (x_min + box_w, label_y + box_h),
                              (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.55, annotated_frame, 0.45, 0, annotated_frame)

                cv2.putText(annotated_frame, line1,
                            (x_min + pad, label_y + pad + h1),
                            font, font_scale, color, thickness)
                cv2.putText(annotated_frame, line2,
                            (x_min + pad, label_y + pad * 2 + h1 + h2),
                            font, font_scale, (200, 200, 200), thickness)

                # Gửi sự kiện cắt vạch
                if just_crossed:
                    line_color = (0, 0, 255)
                    data_queue.put(("target_crossed", {
                        "id": match_id,
                        "class_name": cls_name,
                        "x": cx,
                        "y": cy
                    }))
                    # Gọi truyền thông TCP gửi dữ liệu sang Robot (tương thích 100% giaothuc.py)
                    #send_coordinates_to_robot(cls_name, cx, cy, data_queue)

        # Vẽ Trigger Line
        cv2.line(annotated_frame, (0, line_y), (frame_width, line_y), line_color, 3)
        cv2.putText(annotated_frame, "TRIGGER LINE", (10, line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, line_color, 2)

        # Resize + đẩy lên UI
        display_width  = 640
        display_height = int(display_width * frame_height / frame_width)
        resized_frame  = cv2.resize(annotated_frame, (display_width, display_height))
        rgb_image      = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        data_queue.put(("image", rgb_image))

        # Giữ đúng nhịp 30 FPS: chỉ sleep phần thời gian còn lại sau khi xử lý
        elapsed = time.time() - frame_start
        remaining = config.AI_LOOP_DELAY_SEC - elapsed
        if remaining > 0:
            time.sleep(remaining)

    cap.release()
    data_queue.put(("log", "⏹️ Đã dừng giải phóng Camera."))
