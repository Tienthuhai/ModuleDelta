import customtkinter as ctk
import queue
import threading
import time
from PIL import Image
import serial

from src.ui.camera_panel import CameraPanel
from src.ui.control_panel import ControlPanel
from src.ui.robot_panel import RobotPanel
from src.ui.calibration_panel import CalibrationPanel
from src.ui.statistics_panel import StatisticsPanel
from src.ui.log_panel import LogPanel
from src.ai.worker import run_ai_worker
from src import config

class MainWindow(ctk.CTk):
    """
    Cửa sổ chính điều coordinat hệ thống Dashboard. Sắp xếp bố cục Grid
    gồm 3 cột và thực hiện cập nhật dữ liệu định kỳ từ hàng đợi Queue.
    """
    def __init__(self):
        super().__init__()
        
        # Thiết lập cấu hình cửa sổ
        self.title("DELTA ROBOT AI VISION - CONTROL DASHBOARD")
        self.geometry("1280x760")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Trạng thái chạy luồng AI
        self.is_running = False
        self.data_queue = queue.Queue()
        
        # Quản lý Serial Port
        self.ser = None
        self.matrix_calib = None # Sẽ được cập nhật từ CalibrationPanel

        # Cài đặt Grid hệ thống 3 cột chính
        self.grid_columnconfigure(0, weight=3) # Cột trái: AI & Thiết bị
        self.grid_columnconfigure(1, weight=5) # Cột giữa: Camera & Nhật ký
        self.grid_columnconfigure(2, weight=2) # Cột phải: Thống kê & Hiệu chuẩn
        self.grid_rowconfigure(0, weight=1)

        # ---------------- KHỞI TẠO CÁC PANEL CON ----------------
        
        # Cột 1 (Bên trái): Điều khiển và Kết nối Robot
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.control_panel = ControlPanel(
            self.left_frame, 
            on_start_callback=self.start_system, 
            on_stop_callback=self.stop_system
        )
        self.control_panel.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        
        self.robot_panel = RobotPanel(
            self.left_frame,
            on_connect_callback=self.serial_connect,
            on_disconnect_callback=self.serial_disconnect,
            on_send_manual_callback=self.serial_send_manual
        )
        self.robot_panel.pack(fill=ctk.BOTH, expand=True)

        # Cột 2 (Ở giữa): Live Camera và Nhật ký (Logs)
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.camera_panel = CameraPanel(self.center_frame)
        self.camera_panel.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        
        self.log_panel = LogPanel(self.center_frame)
        self.log_panel.pack(fill=ctk.X, pady=(0, 5))

        # Cột 3 (Bên phải): Thống kê và Hiệu chuẩn tọa độ
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        self.statistics_panel = StatisticsPanel(self.right_frame)
        self.statistics_panel.pack(fill=ctk.X, pady=(0, 10))
        
        self.calibration_panel = CalibrationPanel(
            self.right_frame,
            on_matrix_changed_callback=self.update_calibration_matrix
        )
        self.calibration_panel.pack(fill=ctk.BOTH, expand=True)

        # ---------------- BẬT HÀM CẬP NHẬT ĐỊNH KỲ ----------------
        self.last_fps_time = time.time()
        self.frame_count = 0
        self.update_gui()

    # --- CALLBACK TRUYỀN THÔNG SERIAL ROBOT ---
    def serial_connect(self, port, baudrate):
        """Mở kết nối cổng Serial tới Robot Delta."""
        try:
            self.log_panel.log_robot(f"Đang thử kết nối cổng {port} với baudrate {baudrate}...")
            # Mở cổng Serial thực tế
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.log_panel.log_robot(f"🟢 Kết nối thành công cổng {port}!")
            return True
        except Exception as e:
            msg = f"❌ Kết nối thất bại cổng {port}: {e}"
            self.log_panel.log_error(msg)
            self.log_panel.log_robot(msg)
            return False

    def serial_disconnect(self):
        """Đóng kết nối cổng Serial."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log_panel.log_robot("🔴 Đã ngắt kết nối cổng Serial.")
        self.ser = None

    def serial_send_manual(self, x, y, z):
        """Gửi lệnh di chuyển thủ công (Test) qua Serial."""
        cmd = f"G0 X{x:.1f} Y{y:.1f} Z{z:.1f}"
        self.log_panel.log_robot(f"Gửi lệnh thủ công: {cmd}")
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + "\n").encode())
            except Exception as e:
                self.log_panel.log_error(f"Lỗi gửi lệnh thủ công Serial: {e}")
        else:
            self.log_panel.log_robot("⚠️ Cảnh báo: Serial chưa kết nối! Chỉ hiển thị mô phỏng.")

    def update_calibration_matrix(self, matrix):
        """Cập nhật ma trận hiệu chuẩn tọa độ."""
        self.matrix_calib = matrix
        self.log_panel.log_ai(f"Ma trận hiệu chuẩn cập nhật: ScaleX={matrix['scale_x']:.4f}")

    # --- CALLBACK ĐIỀU KHIỂN CHẠY/DỪNG HỆ THỐNG AI ---
    def start_system(self):
        """Khởi động luồng AI Worker."""
        settings = self.control_panel.get_settings()
        
        if not settings["model_path"]:
            self.log_panel.log_error("⚠️ Lỗi: Vui lòng nạp mô hình YOLOv8 (.pt) trước khi bắt đầu!")
            return
            
        if settings["source_type"] == 1 and not settings["video_path"]:
            self.log_panel.log_error("⚠️ Lỗi: Chọn chế độ phát Video nhưng chưa chọn tệp video!")
            return
            
        if not self.is_running:
            self.is_running = True
            self.statistics_panel.reset_stats()
            self.log_panel.log_ai("Đang khởi động luồng phụ AI Worker...")
            
            # Khởi chạy luồng phụ xử lý AI
            threading.Thread(
                target=run_ai_worker,
                args=(
                    settings["model_path"],
                    settings["source_type"],
                    settings["video_path"],
                    self.data_queue,
                    lambda: self.is_running,
                    settings["conf"],
                    settings["iou"],
                    settings["device"],
                    settings["tracker"]
                ),
                daemon=True
            ).start()
            
            self.control_panel.btn_start.configure(state="disabled")

    def stop_system(self):
        """Dừng luồng AI Worker và đặt lại trạng thái giao diện."""
        self.is_running = False
        self.camera_panel.reset_view()
        self.control_panel.btn_start.configure(state="normal")
        self.log_panel.log_ai("Đã ra lệnh dừng luồng AI Worker.")

    # --- VÒNG LẶP CẬP NHẬT GIAO DIỆN (POLLING QUEUE) ---
    def update_gui(self):
        """Đọc và xử lý toàn bộ các thông báo có trong Queue định kỳ mỗi 10ms."""
        try:
            while True:
                data_type, data_value = self.data_queue.get_nowait()
                
                if data_type == "log":
                    self.log_panel.log_ai(data_value)
                elif data_type == "image":
                    # Nhận frame ảnh đã được xử lý và resize sẵn từ luồng AI
                    pil_img = Image.fromarray(data_value)
                    self.camera_panel.update_image(pil_img)
                    
                    # Tính toán FPS hiển thị
                    self.frame_count += 1
                    curr_time = time.time()
                    elapsed = curr_time - self.last_fps_time
                    if elapsed >= 1.0:
                        fps = self.frame_count / elapsed
                        self.camera_panel.update_fps(fps)
                        self.statistics_panel.update_stats(
                            total=self.statistics_panel.get_stats()["total"],
                            sent=self.statistics_panel.get_stats()["sent"],
                            rejected=self.statistics_panel.get_stats()["rejected"]
                        )
                        # Thêm live FPS vào statistics panel
                        self.statistics_panel.lbl_rejected_title.configure(text=f"Sản Phẩm Bị Loại (Live FPS: {fps:.1f})")
                        
                        self.frame_count = 0
                        self.last_fps_time = curr_time
                        
                elif data_type == "target_crossed":
                    # Kích hoạt khi có vật thể cắt vạch phát hiện
                    cls_name = data_value["class_name"]
                    cx = data_value["x"]
                    cy = data_value["y"]
                    obj_id = data_value["id"]
                    
                    self.statistics_panel.increment_total()
                    
                    # Chuyển đổi tọa độ qua hiệu chuẩn nếu có
                    if self.matrix_calib:
                        rx, ry = self.calibration_panel.transform(cx, cy)
                    else:
                        # Tọa độ mặc định nếu chưa calib (giả lập scale 1:1)
                        rx, ry = float(cx), float(cy)
                        
                    self.log_panel.log_ai(f"🎯 CẮT VẠCH: Vật thể ID {obj_id} ({cls_name}) tại tọa độ ảnh ({cx}, {cy})")
                    
                    # Gửi tọa độ xuống Robot
                    cmd_to_send = f"ID:{obj_id},NHAN:{cls_name},X:{rx:.1f},Y:{ry:.1f}"
                    self.log_panel.log_robot(f"Truyền tọa độ: {cmd_to_send}")
                    
                    if self.ser and self.ser.is_open:
                        try:
                            self.ser.write((cmd_to_send + "\n").encode())
                            self.statistics_panel.increment_sent()
                        except Exception as e:
                            self.log_panel.log_error(f"Lỗi gửi dữ liệu qua Serial: {e}")
                            self.statistics_panel.increment_rejected()
                    else:
                        # Chế độ mô phỏng
                        self.statistics_panel.increment_sent()
                        self.log_panel.log_robot("⚠️ Cảnh báo: Serial chưa kết nối! Chỉ gửi mô phỏng.")
                        
        except queue.Empty:
            pass
        
        # Lặp lại sau 10 mili-giây
        self.after(10, self.update_gui)
