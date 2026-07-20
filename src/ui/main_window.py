import customtkinter as ctk
import queue
import threading
import time
from PIL import Image
import serial

from src.ui.camera_panel import CameraPanel
from src.ui.control_panel import ControlPanel
from src.ui.robot_panel import RobotPanel
from src.calibration.calibration_panel import CalibrationPanel
from src.ui.statistics_panel import StatisticsPanel
from src.ui.log_panel import LogPanel
from src.ai.worker import run_ai_worker
from src.robot.tcp_communication import PLCTCPClient
from src import config
from src.lang import get_texts, set_language, current_lang

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

        # Quản lý truyền thông (Serial & TCP)
        self.ser = None
        self.tcp_client = None
        self.connection_mode = None  # "SERIAL" hoặc "TCP"

        self.matrix_calib = None  # Sẽ được cập nhật từ CalibrationPanel

        # Cài đặt Grid — Hàng 0: Toolbar (nhỏ), Hàng 1: Nội dung chính
        self.grid_columnconfigure(0, weight=3)  # Cột trái: AI & Thiết bị
        self.grid_columnconfigure(1, weight=5)  # Cột giữa: Camera & Nhật ký
        self.grid_columnconfigure(2, weight=2)  # Cột phải: Thống kê & Hiệu chuẩn
        self.grid_rowconfigure(0, weight=0)     # Toolbar
        self.grid_rowconfigure(1, weight=1)     # Nội dung chính

        # ---------------- TOOLBAR (HÀNG 0) ----------------
        self.toolbar = ctk.CTkFrame(self, height=36, fg_color="#111827")
        self.toolbar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=0, pady=0)

        self.lbl_app_brand = ctk.CTkLabel(
            self.toolbar,
            text="⚡ DELTA ROBOT AI VISION",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4CAF50"
        )
        self.lbl_app_brand.pack(side=ctk.LEFT, padx=15)

        self.btn_lang = ctk.CTkButton(
            self.toolbar,
            text="🌐 EN",
            width=80,
            height=28,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self.toggle_language
        )
        self.btn_lang.pack(side=ctk.RIGHT, padx=12, pady=4)

        # ---------------- KHỞI TẠO CÁC PANEL CON (HÀNG 1) ----------------

        # Cột 1 (Bên trái): Điều khiển và Kết nối Robot
        self.left_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.control_panel = ControlPanel(
            self.left_frame,
            on_start_callback=self.start_system,
            on_stop_callback=self.stop_system
        )
        self.control_panel.pack(fill=ctk.X, pady=(0, 10))

        self.robot_panel = RobotPanel(
            self.left_frame,
            on_connect_callback=self.handle_connect,
            on_disconnect_callback=self.handle_disconnect,
            on_send_manual_callback=self.serial_send_manual
        )
        self.robot_panel.pack(fill=ctk.X)

        # Cột 2 (Ở giữa): Live Camera và Nhật ký (Logs)
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        self.camera_panel = CameraPanel(self.center_frame)
        self.camera_panel.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))

        self.log_panel = LogPanel(self.center_frame)
        self.log_panel.pack(fill=ctk.X, pady=(0, 5))

        # Cột 3 (Bên phải): Thống kê và Hiệu chuẩn tọa độ
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")

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

    # --- CHUYỂN ĐỔI NGÔN NGỮ ---
    def toggle_language(self):
        """Chuyển đổi ngôn ngữ VI ↔ EN và cập nhật toàn bộ giao diện."""
        new_lang = "en" if current_lang() == "vi" else "vi"
        set_language(new_lang)
        texts = get_texts()
        self.btn_lang.configure(text=texts["lang_btn_switch"])
        self.title(texts["window_title"])
        self._apply_lang_all(texts)

    def _apply_lang_all(self, texts: dict):
        """Gọi apply_lang() trên toàn bộ các panel con."""
        self.control_panel.apply_lang(texts)
        self.robot_panel.apply_lang(texts)
        self.camera_panel.apply_lang(texts)
        self.log_panel.apply_lang(texts)
        self.statistics_panel.apply_lang(texts)
        self.calibration_panel.apply_lang(texts)

    # --- CALLBACK QUẢN LÝ TRUYỀN THÔNG ĐA GIAO THỨC (SERIAL / TCP) ---
    def handle_connect(self, mode, *args):
        """Điều hướng kết nối tương ứng với giao thức được chọn."""
        if mode == "SERIAL":
            port = args[0]
            baudrate = args[1]
            success = self.serial_connect(port, baudrate)
            if success:
                self.connection_mode = "SERIAL"
            return success
        elif mode == "TCP":
            ip = args[0]
            port = args[1]
            success = self.tcp_connect(ip, port)
            if success:
                self.connection_mode = "TCP"
            return success
        return False

    def handle_disconnect(self, mode):
        """Điều hướng ngắt kết nối."""
        if mode == "SERIAL":
            self.serial_disconnect()
        elif mode == "TCP":
            self.tcp_disconnect()
        self.connection_mode = None

    def serial_connect(self, port, baudrate):
        """Mở kết nối cổng Serial tới Robot Delta."""
        try:
            self.log_panel.log_robot(f"Đang thử kết nối cổng {port} với baudrate {baudrate}...")
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

    def tcp_connect(self, ip, port):
        """Mở kết nối TCP Client tới PLC."""
        try:
            config.PLC_IP = ip
            config.PLC_PORT = port
            self.log_panel.log_robot(f"Đang thiết lập kết nối TCP tới PLC {ip}:{port}...")
            self.tcp_client = PLCTCPClient(ip, port, log_queue=self.data_queue)
            success = self.tcp_client.connect()
            return success
        except Exception as e:
            msg = f"❌ Lỗi khởi chạy kết nối TCP: {e}"
            self.log_panel.log_error(msg)
            self.log_panel.log_robot(msg)
            return False

    def tcp_disconnect(self):
        """Đóng kết nối TCP Client."""
        if self.tcp_client:
            self.tcp_client.disconnect()
        self.tcp_client = None

    def serial_send_manual(self, x, y, z):
        """Gửi lệnh di chuyển thủ công (Test) qua Serial hoặc TCP."""
        cmd = f"G0 X{x:.1f} Y{y:.1f} Z{z:.1f}"
        self.log_panel.log_robot(f"Gửi lệnh thủ công: {cmd}")

        if self.connection_mode == "SERIAL" and self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + "\n").encode())
            except Exception as e:
                self.log_panel.log_error(f"Lỗi gửi lệnh thủ công Serial: {e}")
        elif self.connection_mode == "TCP" and self.tcp_client and self.tcp_client.is_connected:
            try:
                self.tcp_client.send_data(cmd)
            except Exception as e:
                self.log_panel.log_error(f"Lỗi gửi lệnh thủ công TCP: {e}")
        else:
            self.log_panel.log_robot("⚠️ Cảnh báo: Chưa kết nối truyền thông! Chỉ hiển thị mô phỏng.")

    def update_calibration_matrix(self, matrix):
        """Cập nhật ma trận hiệu chuẩn tọa độ."""
        self.matrix_calib = matrix
        self.log_panel.log_ai(f"✅ Ma trận Robot Calibration đã được nạp: ScaleX={matrix['scale_x']:.4f} | ScaleY={matrix['scale_y']:.4f}")
        self.log_panel.log_ai("🟢 Hệ thống sẽ tự động áp dụng Calibration khi gửi tọa độ sang Robot.")

    # --- CALLBACK ĐIỀU KHIỂN CHẠY/DỪNG HỆ THỐNG AI ---
    def start_system(self):
        """Khởi động luồng AI Worker."""
        settings = self.control_panel.get_settings()

        if not settings["model_path"]:
            self.log_panel.log_error("⚠️ Lỗi: Vui lòng nạp mô hình YOLO (.pt) trước khi bắt đầu!")
            return

        if settings["source_type"] == 1 and not settings["video_path"]:
            self.log_panel.log_error("⚠️ Lỗi: Chọn chế độ phát Video nhưng chưa chọn tệp video!")
            return

        if not self.is_running:
            self.is_running = True
            self.statistics_panel.reset_stats()
            self.log_panel.log_ai("Đang khởi động luồng phụ AI Worker...")

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
                    settings["device"]
                ),
                daemon=True
            ).start()

            self.control_panel.btn_start.configure(state="disabled")
            self.calibration_panel.lock_for_running()
            self.log_panel.log_ai("🔒 Calibration đã bị khoá. Dừng hệ thống để thay đổi.")

    def stop_system(self):
        """Dừng luồng AI Worker và đặt lại trạng thái giao diện."""
        self.is_running = False
        self.camera_panel.reset_view()
        self.control_panel.btn_start.configure(state="normal")
        self.log_panel.log_ai("Dã ra lệnh dừng luồng AI Worker.")
        self.calibration_panel.unlock_for_editing()
        self.log_panel.log_ai("🔓 Calibration đã được mở khoá. Có thể thay đổi ma trận.")

    # --- VÒNG LẶP CẬP NHẬT GIAO DIỆN (POLLING QUEUE) ---
    def update_gui(self):
        """Đọc và xử lý toàn bộ các thông báo có trong Queue định kỳ mỗi 10ms."""
        try:
            while True:
                data_type, data_value = self.data_queue.get_nowait()

                if data_type == "log":
                    self.log_panel.log_ai(data_value)
                elif data_type == "image":
                    pil_img = Image.fromarray(data_value)
                    self.camera_panel.update_image(pil_img)

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
                        # Cập nhật nhãn KPI với Live FPS theo ngôn ngữ hiện tại
                        texts = get_texts()
                        self.statistics_panel.lbl_rejected_title.configure(
                            text=texts["stat_rejected_fps"].format(fps=fps)
                        )

                        self.frame_count = 0
                        self.last_fps_time = curr_time

                elif data_type == "target_crossed":
                    cls_name = data_value["class_name"]
                    cx = data_value["x"]
                    cy = data_value["y"]
                    obj_id = data_value["id"]

                    self.statistics_panel.increment_total()

                    if self.calibration_panel.has_valid_matrix():
                        rx, ry = self.calibration_panel.transform(cx, cy)
                        coord_mode = "[AFFINE]"
                    else:
                        rx, ry = float(cx), float(cy)
                        coord_mode = "[RAW PIXEL]"

                    self.log_panel.log_ai(f"🎯 CẮT VẠCH {coord_mode}: Vật thể ID {obj_id} ({cls_name}) tại ảnh ({cx}, {cy}) → Robot ({rx:.1f}, {ry:.1f})")

                    cmd_to_send = f"ID:{obj_id},NHAN:{cls_name},X:{rx:.1f},Y:{ry:.1f}"

                    if self.connection_mode == "SERIAL" and self.ser and self.ser.is_open:
                        try:
                            self.log_panel.log_robot(f"Truyền tọa độ (Serial): {cmd_to_send}")
                            self.ser.write((cmd_to_send + "\n").encode())
                            self.statistics_panel.increment_sent()
                        except Exception as e:
                            self.log_panel.log_error(f"Lỗi gửi dữ liệu qua Serial: {e}")
                            self.statistics_panel.increment_rejected()
                    elif self.connection_mode == "TCP" and self.tcp_client and self.tcp_client.is_connected:
                        try:
                            self.log_panel.log_robot(f"Truyền tọa độ (TCP): {cmd_to_send}")
                            self.tcp_client.send_data(cmd_to_send)
                            self.statistics_panel.increment_sent()
                        except Exception as e:
                            self.log_panel.log_error(f"Lỗi gửi dữ liệu qua TCP: {e}")
                            self.statistics_panel.increment_rejected()
                    else:
                        self.statistics_panel.increment_sent()
                        self.log_panel.log_robot(f"⚠️ Mô phỏng gửi tọa độ ({self.connection_mode or 'Chưa kết nối'}): {cmd_to_send}")

        except queue.Empty:
            pass

        # Lặp lại sau 10 mili-giây
        self.after(10, self.update_gui)
