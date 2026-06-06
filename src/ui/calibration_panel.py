import customtkinter as ctk
import json
from tkinter import messagebox, filedialog

class CalibrationPanel(ctk.CTkFrame):
    """
    Panel hỗ trợ việc hiệu chuẩn hệ tọa độ giữa Camera (Pixel) và Robot Delta (Millimeter).
    Cung cấp chu trình Wizard 9 điểm và lưu/nạp cấu hình ma trận chuyển đổi.
    """
    def __init__(self, master, on_matrix_changed_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_matrix_changed_callback = on_matrix_changed_callback
        
        # Ma trận chuyển đổi mặc định (identity)
        self.matrix = {
            "scale_x": 1.0, "scale_y": 1.0,
            "shift_x": 0.0, "shift_y": 0.0,
            "rotation": 0.0
        }
        
        # Trạng thái tiến trình hiệu chuẩn
        self.calib_step = 0 # 0 = Chưa bắt đầu, 1-9 = Điểm thứ x
        self.captured_camera_points = []
        self.captured_robot_points = []

        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self, 
            text="📐 HIỆU CHUẨN CAMERA - ROBOT (9 ĐIỂM)", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)
        
        # ---------------- 1. CÁC NÚT ĐIỀU KHIỂN HIỆU CHUẨN ----------------
        self.ctrl_group = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_group.pack(fill=ctk.X, padx=10, pady=5)
        
        self.btn_start_wizard = ctk.CTkButton(
            self.ctrl_group, text="🎯 Bắt Đầu Hiệu Chuẩn", fg_color="#FF9800", hover_color="#F57C00", command=self.start_wizard
        )
        self.btn_start_wizard.pack(fill=ctk.X, pady=5)
        
        # Trạng thái hướng dẫn từng bước
        self.lbl_wizard_guide = ctk.CTkLabel(
            self.ctrl_group, 
            text="Trạng thái: Chưa hiệu chuẩn.", 
            text_color="gray", 
            justify="left",
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_wizard_guide.pack(fill=ctk.X, pady=5)
        
        # Khung thu thập dữ liệu (ẩn/hiện trong chế độ wizard)
        self.wizard_frame = ctk.CTkFrame(self.ctrl_group, fg_color="transparent")
        
        # Ô nhập tọa độ thực tế của robot tại điểm đang hiệu chuẩn
        self.lbl_robot_coord = ctk.CTkLabel(self.wizard_frame, text="Nhập tọa độ Robot thực tế:")
        self.lbl_robot_coord.pack(pady=2, anchor="w")
        
        self.entry_frame = ctk.CTkFrame(self.wizard_frame, fg_color="transparent")
        self.entry_frame.pack(fill=ctk.X, pady=2)
        
        ctk.CTkLabel(self.entry_frame, text="Xr:").pack(side=ctk.LEFT, padx=2)
        self.entry_xr = ctk.CTkEntry(self.entry_frame, width=50)
        self.entry_xr.pack(side=ctk.LEFT, padx=5)
        
        ctk.CTkLabel(self.entry_frame, text="Yr:").pack(side=ctk.LEFT, padx=2)
        self.entry_yr = ctk.CTkEntry(self.entry_frame, width=50)
        self.entry_yr.pack(side=ctk.LEFT, padx=5)
        
        self.btn_capture = ctk.CTkButton(
            self.wizard_frame, text="📍 Ghi Điểm Này", command=self.capture_point
        )
        self.btn_capture.pack(fill=ctk.X, pady=5)

        # ---------------- 2. NHẬP/XUẤT MA TRẬN CALIBRATION ----------------
        self.io_group = ctk.CTkFrame(self)
        self.io_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm IO
        ctk.CTkLabel(
            self.io_group, text="💾 Lưu & Nạp Ma Trận", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 2), anchor="w")
        
        self.btn_load_calib = ctk.CTkButton(
            self.io_group, text="📂 Nạp File Calib", command=self.load_from_file
        )
        self.btn_load_calib.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=5, pady=5)
        
        self.btn_save_calib = ctk.CTkButton(
            self.io_group, text="💾 Lưu File Calib", command=self.save_to_file
        )
        self.btn_save_calib.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=5, pady=5)

        # ---------------- 3. HIỂN THỊ MA TRẬN ----------------
        self.matrix_group = ctk.CTkFrame(self)
        self.matrix_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm Matrix
        ctk.CTkLabel(
            self.matrix_group, text="📊 Ma Trận Chuyển Đổi Hiện Tại", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 2), anchor="w")
        
        self.lbl_matrix_val = ctk.CTkLabel(
            self.matrix_group, 
            text="Scale X: 1.0000 | Scale Y: 1.0000\nShift X: 0.0000 | Shift Y: 0.0000\nRotation: 0.00°", 
            justify="left",
            font=ctk.CTkFont(family="Consolas", size=10)
        )
        self.lbl_matrix_val.pack(padx=10, pady=10)

    def start_wizard(self):
        """Bắt đầu chu trình hiệu chuẩn 9 điểm."""
        self.calib_step = 1
        self.captured_camera_points = []
        self.captured_robot_points = []
        self.btn_start_wizard.configure(state="disabled")
        self.wizard_frame.pack(fill=ctk.X, pady=5)
        self.update_wizard_ui()
        
    def update_wizard_ui(self):
        """Cập nhật giao diện hướng dẫn."""
        if 1 <= self.calib_step <= 9:
            self.lbl_wizard_guide.configure(
                text=f"👉 Điểm {self.calib_step}/9:\n1. Chọn tâm vật thể trên màn hình Camera.\n2. Di chuyển Robot gắp chạm đúng vật thể.\n3. Nhập tọa độ Robot Xr, Yr vào ô bên dưới.",
                text_color="#FF9800"
            )
            # Giả lập gợi ý tọa độ nhập
            self.entry_xr.delete(0, ctk.END)
            self.entry_xr.insert(0, f"{100 + self.calib_step * 20}")
            self.entry_yr.delete(0, ctk.END)
            self.entry_yr.insert(0, f"{-50 + self.calib_step * 10}")
        else:
            # Hoàn thành hoặc bị hủy
            self.lbl_wizard_guide.configure(text="Trạng thái: Hiệu chuẩn thành công!", text_color="#4CAF50")
            self.wizard_frame.pack_forget()
            self.btn_start_wizard.configure(state="normal")
            self.calib_step = 0

    def capture_point(self):
        """Ghi nhận dữ liệu tọa độ ảnh và tọa độ robot tương ứng tại điểm đó."""
        try:
            xr = float(self.entry_xr.get())
            yr = float(self.entry_yr.get())
        except ValueError:
            messagebox.showerror("Lỗi nhập liệu", "Tọa độ Robot phải là số thực hợp lệ.")
            return

        # Trong ứng dụng thực tế, tọa độ camera (xc, yc) được lấy từ việc người dùng nhấn chuột lên viewport camera.
        # Ở đây chúng ta giả lập tọa độ camera tương ứng với điểm đang gắp:
        xc = 320 + (self.calib_step - 5) * 50
        yc = 180 + (self.calib_step - 5) * 30
        
        self.captured_camera_points.append((xc, yc))
        self.captured_robot_points.append((xr, yr))
        
        if self.calib_step < 9:
            self.calib_step += 1
            self.update_wizard_ui()
        else:
            # Đã thu thập đủ 9 điểm -> Tính toán ma trận
            self.calculate_matrix()
            self.calib_step = 0
            self.update_wizard_ui()

    def calculate_matrix(self):
        """Tính toán ma trận dịch chuyển cơ bản giữa tọa độ Camera (px) và Robot (mm)."""
        # Đây là thuật toán giả lập tương quan giữa 2 tập điểm
        # Ở môi trường thực tế, ta sử dụng cv2.findHomography hoặc cv2.estimateAffine2D để tìm ma trận chuẩn xác.
        # Ở đây ta giả lập tính tỉ lệ trung bình (scale), dịch chuyển (shift) cơ bản.
        avg_xc = sum(pt[0] for pt in self.captured_camera_points) / 9.0
        avg_yc = sum(pt[1] for pt in self.captured_camera_points) / 9.0
        avg_xr = sum(pt[0] for pt in self.captured_robot_points) / 9.0
        avg_yr = sum(pt[1] for pt in self.captured_robot_points) / 9.0
        
        # Ước lượng hệ số tỷ lệ cơ bản
        self.matrix = {
            "scale_x": abs(avg_xr / (avg_xc if avg_xc != 0 else 1.0)),
            "scale_y": abs(avg_yr / (avg_yc if avg_yc != 0 else 1.0)),
            "shift_x": avg_xr - avg_xc * 0.5,
            "shift_y": avg_yr - avg_yc * 0.5,
            "rotation": 0.0
        }
        
        self.update_matrix_display()
        self.on_matrix_changed_callback(self.matrix)
        messagebox.showinfo("Thành công", "Đã hiệu chuẩn thành công hệ thống camera - robot!")

    def update_matrix_display(self):
        """Hiển thị giá trị ma trận lên giao diện."""
        text = f"Scale X: {self.matrix['scale_x']:.4f} | Scale Y: {self.matrix['scale_y']:.4f}\n" \
               f"Shift X: {self.matrix['shift_x']:.4f} | Shift Y: {self.matrix['shift_y']:.4f}\n" \
               f"Rotation: {self.matrix['rotation']:.2f}°"
        self.lbl_matrix_val.configure(text=text)

    def save_to_file(self):
        """Lưu ma trận hiện tại ra tệp JSON."""
        file_path = filedialog.asksaveasfilename(
            title="Lưu cấu hình Calibration",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.matrix, f, indent=4)
            messagebox.showinfo("Thành công", f"Đã lưu ma trận hiệu chuẩn vào file:\n{file_path}")

    def load_from_file(self):
        """Nạp ma trận từ tệp JSON cũ."""
        file_path = filedialog.askopenfilename(
            title="Nạp cấu hình Calibration",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, "r") as f:
                    self.matrix = json.load(f)
                self.update_matrix_display()
                self.on_matrix_changed_callback(self.matrix)
                messagebox.showinfo("Thành công", "Đã nạp thành công ma trận hiệu chuẩn!")
            except Exception as e:
                messagebox.showerror("Thất bại", f"Không thể nạp tệp hiệu chuẩn:\n{e}")
                
    def transform(self, px_x, px_y):
        """Chuyển đổi tọa độ pixel camera sang tọa độ robot thực tế."""
        # Công thức biến đổi cơ bản
        rx = px_x * self.matrix["scale_x"] + self.matrix["shift_x"]
        ry = px_y * self.matrix["scale_y"] + self.matrix["shift_y"]
        return rx, ry
