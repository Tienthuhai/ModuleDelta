import customtkinter as ctk
import numpy as np
import os
from tkinter import messagebox, filedialog
from src.calibration.camera_calibration import CameraCalibration
from src.calibration.robot_calibration import RobotCalibration
from src.calibration.calibration_io import CalibrationIO

class CalibrationPanel(ctk.CTkFrame):
    """
    Module hiệu chuẩn hợp nhất dạng cột đứng (Single Column), không sử dụng Camera Preview:
    1. Chessboard Calibration (Không preview ảnh, nhập thư mục và chạy)
    2. Robot Calibration (Nhập tay Pixel X, Y và Robot X, Y)
    Tương thích ngược hoàn toàn với main_window.py.
    """
    def __init__(self, master, on_matrix_changed_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_matrix_changed_callback = on_matrix_changed_callback
        
        # Khởi tạo thuật toán hiệu chuẩn
        self.camera_calib = CameraCalibration()
        self.robot_calib = RobotCalibration()
        
        # Lưu ma trận biến đổi mặc định (tương thích ngược)
        self.matrix = {
            "scale_x": 1.0,
            "scale_y": 1.0,
            "shift_x": 0.0,
            "shift_y": 0.0,
            "rotation": 0.0
        }
        
        self.chessboard_image_paths = []
        
        # Cấu hình Layout cột chính
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- TOP AREA: CHỌN CHẾ ĐỘ CALIBRATION ----------------
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        self.mode_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.mode_frame,
            text="📐 Chế Độ Hiệu Chuẩn",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 2), sticky="w")

        self.calib_mode_var = ctk.IntVar(value=0)  # 0 = Chessboard, 1 = Robot

        self.rad_chessboard = ctk.CTkRadioButton(
            self.mode_frame,
            text="Chessboard",
            variable=self.calib_mode_var,
            value=0,
            command=self.on_tab_change
        )
        self.rad_chessboard.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.rad_robot = ctk.CTkRadioButton(
            self.mode_frame,
            text="Robot Coords",
            variable=self.calib_mode_var,
            value=1,
            command=self.on_tab_change
        )
        self.rad_robot.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Khung chứa nội dung từng chế độ
        self.tab_camera_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_robot_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Khởi tạo UI cho từng chế độ
        self._init_camera_tab_ui()
        self._init_robot_tab_ui()

        # Hiển thị mặc định: Chessboard
        self.tab_camera_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    def on_tab_change(self):
        """Chuyển đổi hiển thị nội dung theo chế độ được chọn (không mất dữ liệu)."""
        if self.calib_mode_var.get() == 0:
            self.tab_robot_frame.grid_forget()
            self.tab_camera_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        else:
            self.tab_camera_frame.grid_forget()
            self.tab_robot_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    # =========================================================================
    # CHẾ ĐỘ 1: CHESSBOARD CALIBRATION (KHÔNG PREVIEW)
    # =========================================================================
    def _init_camera_tab_ui(self):
        self.tab_camera_frame.grid_columnconfigure(0, weight=1)
        self.tab_camera_frame.grid_rowconfigure(2, weight=1) # Danh sách ảnh giãn nở
        
        # 1.1 Cấu hình lưới bàn cờ
        grid_settings = ctk.CTkFrame(self.tab_camera_frame)
        grid_settings.grid(row=0, column=0, padx=5, pady=4, sticky="ew")
        grid_settings.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        ctk.CTkLabel(grid_settings, text="Lưới cờ (Width x Height):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 0))
        
        self.entry_board_w = ctk.CTkEntry(grid_settings, width=45)
        self.entry_board_w.grid(row=1, column=0, padx=5, pady=4, sticky="ew")
        self.entry_board_w.insert(0, "9")
        
        ctk.CTkLabel(grid_settings, text="x").grid(row=1, column=1)
        
        self.entry_board_h = ctk.CTkEntry(grid_settings, width=45)
        self.entry_board_h.grid(row=1, column=2, padx=5, pady=4, sticky="ew")
        self.entry_board_h.insert(0, "6")
        
        self.entry_sq_size = ctk.CTkEntry(grid_settings, placeholder_text="Size (mm)", width=65)
        self.entry_sq_size.grid(row=1, column=3, padx=5, pady=4, sticky="ew")
        self.entry_sq_size.insert(0, "25")

        # 1.2 Các nút thao tác chính
        btn_group = ctk.CTkFrame(self.tab_camera_frame, fg_color="transparent")
        btn_group.grid(row=1, column=0, padx=5, pady=4, sticky="ew")
        
        self.btn_load_images = ctk.CTkButton(
            btn_group, text="📁 Load Images", command=self.load_chessboard_images, fg_color="#3B82F6", hover_color="#2563EB", height=32
        )
        self.btn_load_images.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=2)
        
        self.btn_run_calib = ctk.CTkButton(
            btn_group, text="⚡ Run Calib", command=self.run_chessboard_calibration, fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_run_calib.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=2)

        # 1.3 Danh sách ảnh đã nạp
        self.image_list = ctk.CTkTextbox(self.tab_camera_frame, height=130, font=("Consolas", 10))
        self.image_list.grid(row=2, column=0, padx=5, pady=4, sticky="nsew")
        self.image_list.insert("1.0", "Danh sách ảnh bàn cờ đã nạp:\n[Chưa nạp ảnh]")
        self.image_list.configure(state="disabled")
        
        # 1.4 Hiển thị kết quả Ma trận camera
        result_group = ctk.CTkFrame(self.tab_camera_frame)
        result_group.grid(row=3, column=0, padx=5, pady=4, sticky="ew")
        
        self.lbl_chessboard_status = ctk.CTkLabel(result_group, text="Trạng thái: Chưa hiệu chuẩn", font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_chessboard_status.pack(padx=8, pady=2, anchor="w")
        
        self.txt_camera_matrix = ctk.CTkTextbox(result_group, height=110, font=("Consolas", 10), fg_color="#121212", text_color="#00FF00")
        self.txt_camera_matrix.pack(fill=ctk.X, padx=5, pady=4)
        self.txt_camera_matrix.insert("1.0", "Camera Matrix (K) & Dist (D):\n[Chưa có dữ liệu]")
        self.txt_camera_matrix.configure(state="disabled")
        
        # 1.5 Lưu & Nạp Camera Intrinsic file
        io_group = ctk.CTkFrame(self.tab_camera_frame, fg_color="transparent")
        io_group.grid(row=4, column=0, padx=5, pady=4, sticky="ew")
        
        self.btn_save_intrinsic = ctk.CTkButton(io_group, text="💾 Save Intrinsic", command=self.save_camera_intrinsic, height=32)
        self.btn_save_intrinsic.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=3)
        
        self.btn_load_intrinsic = ctk.CTkButton(io_group, text="📂 Load Intrinsic", command=self.load_camera_intrinsic, height=32)
        self.btn_load_intrinsic.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=3)

    # =========================================================================
    # CHẾ ĐỘ 2: ROBOT COORDINATE CALIBRATION (NHẬP TAY)
    # =========================================================================
    def _init_robot_tab_ui(self):
        self.tab_robot_frame.grid_columnconfigure(0, weight=1)
        self.tab_robot_frame.grid_rowconfigure(1, weight=1) # Bảng dữ liệu điểm giãn nở
        
        # 2.1 Nhập điểm thủ công (Manual Point Inputs)
        entry_group = ctk.CTkFrame(self.tab_robot_frame)
        entry_group.grid(row=0, column=0, padx=5, pady=4, sticky="ew")
        entry_group.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        ctk.CTkLabel(entry_group, text="Nhập tọa độ Pixel (x, y):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 0))
        ctk.CTkLabel(entry_group, text="Nhập tọa độ Robot (Xr, Yr):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=2, columnspan=2, sticky="w", padx=6, pady=(2, 0))
        
        self.entry_pixel_x = ctk.CTkEntry(entry_group, placeholder_text="Pixel X", width=65)
        self.entry_pixel_x.grid(row=1, column=0, padx=3, pady=4, sticky="ew")
        
        self.entry_pixel_y = ctk.CTkEntry(entry_group, placeholder_text="Pixel Y", width=65)
        self.entry_pixel_y.grid(row=1, column=1, padx=3, pady=4, sticky="ew")
        
        self.entry_robot_x = ctk.CTkEntry(entry_group, placeholder_text="Robot X", width=65)
        self.entry_robot_x.grid(row=1, column=2, padx=3, pady=4, sticky="ew")
        
        self.entry_robot_y = ctk.CTkEntry(entry_group, placeholder_text="Robot Y", width=65)
        self.entry_robot_y.grid(row=1, column=3, padx=3, pady=4, sticky="ew")
        
        self.btn_add_pt = ctk.CTkButton(
            entry_group, text="📍 Add Point", command=self.add_point_manually, fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_add_pt.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        # 2.2 Bảng dữ liệu điểm (Point Data Table)
        self.table_frame = ctk.CTkScrollableFrame(self.tab_robot_frame, height=130)
        self.table_frame.grid(row=1, column=0, padx=5, pady=4, sticky="nsew")
        self.table_row_widgets = []
        
        # 2.3 Thuật toán & Tính toán ma trận
        calc_ctrl = ctk.CTkFrame(self.tab_robot_frame)
        calc_ctrl.grid(row=2, column=0, padx=5, pady=4, sticky="ew")
        calc_ctrl.grid_columnconfigure((0, 1), weight=1)
        
        self.opt_algorithm = ctk.CTkOptionMenu(calc_ctrl, values=["Homography", "Affine"], height=32)
        self.opt_algorithm.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.opt_algorithm.set("Homography")
        
        self.btn_calc_matrix = ctk.CTkButton(
            calc_ctrl, text="📊 Calculate Matrix", command=self.calculate_robot_matrix, fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_calc_matrix.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.lbl_points_count = ctk.CTkLabel(calc_ctrl, text="Số lượng điểm: 0 / 9 (Tối thiểu 9 điểm)", font=ctk.CTkFont(size=11))
        self.lbl_points_count.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=1)
        
        self.txt_robot_matrix = ctk.CTkTextbox(calc_ctrl, height=90, font=("Consolas", 10), fg_color="#121212", text_color="#00E5FF")
        self.txt_robot_matrix.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
        self.txt_robot_matrix.insert("1.0", "Robot Matrix:\n[Chưa tính toán]")
        self.txt_robot_matrix.configure(state="disabled")

        # 2.4 Verification Mode (Kiểm chứng thủ công bằng cách nhập Pixel)
        verify_frame = ctk.CTkFrame(self.tab_robot_frame)
        verify_frame.grid(row=3, column=0, padx=5, pady=4, sticky="ew")
        verify_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(verify_frame, text="🔍 KIỂM CHỨNG TỌA ĐỘ (VERIFY)", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 0))
        
        self.entry_verify_px = ctk.CTkEntry(verify_frame, placeholder_text="Pixel X verify", height=28)
        self.entry_verify_px.grid(row=1, column=0, padx=4, pady=3, sticky="ew")
        
        self.entry_verify_py = ctk.CTkEntry(verify_frame, placeholder_text="Pixel Y verify", height=28)
        self.entry_verify_py.grid(row=1, column=1, padx=4, pady=3, sticky="ew")
        
        self.btn_verify_pt = ctk.CTkButton(verify_frame, text="🔍 Verify Point", command=self.verify_manual_point, height=28)
        self.btn_verify_pt.grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="ew")
        
        self.lbl_verify_result = ctk.CTkLabel(verify_frame, text="Robot (X, Y) dự kiến: --, --", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_verify_result.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=1)
        
        self.lbl_verify_error = ctk.CTkLabel(verify_frame, text="Sai số kiểm chứng: -- mm", font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_verify_error.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=1)

        # 2.5 Nút lưu nạp robot calib
        robot_io = ctk.CTkFrame(self.tab_robot_frame, fg_color="transparent")
        robot_io.grid(row=4, column=0, padx=5, pady=4, sticky="ew")
        
        self.btn_save_robot = ctk.CTkButton(robot_io, text="💾 Save Robot", command=self.save_robot_calibration, height=32)
        self.btn_save_robot.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=3)
        
        self.btn_load_robot = ctk.CTkButton(robot_io, text="📂 Load Robot", command=self.load_robot_calibration, height=32)
        self.btn_load_robot.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=3)
        
        # Vẽ bảng điểm ban đầu sau khi tất cả các widget khác đã được khởi tạo
        self._refresh_point_table()

    # =========================================================================
    # LOGIC CHẾ ĐỘ 1: CHESSBOARD CALIBRATION
    # =========================================================================
    def load_chessboard_images(self):
        """Tải danh sách ảnh từ thư mục."""
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa ảnh bàn cờ")
        if not dir_path:
            return
            
        valid_exts = (".jpg", ".jpeg", ".png", ".bmp")
        self.chessboard_image_paths = []
        try:
            for file in os.listdir(dir_path):
                if file.lower().endswith(valid_exts):
                    self.chessboard_image_paths.append(os.path.join(dir_path, file))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc thư mục:\n{e}")
            return
            
        if not self.chessboard_image_paths:
            messagebox.showwarning("Thông báo", "Không tìm thấy ảnh bàn cờ hợp lệ (.jpg, .png...)")
            return
            
        self.image_list.configure(state="normal")
        self.image_list.delete("1.0", ctk.END)
        self.image_list.insert(ctk.END, f"Đã nạp {len(self.chessboard_image_paths)} ảnh từ: {dir_path}\n\n")
        for path in self.chessboard_image_paths:
            self.image_list.insert(ctk.END, f"- {os.path.basename(path)}\n")
        self.image_list.configure(state="disabled")
        
        self.lbl_chessboard_status.configure(text=f"Đã nạp {len(self.chessboard_image_paths)} ảnh bàn cờ. Đợi calib...")

    def run_chessboard_calibration(self):
        """Chạy tính toán thông số nội camera."""
        if not self.chessboard_image_paths:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải ảnh bàn cờ trước khi chạy hiệu chuẩn.")
            return
            
        try:
            w = int(self.entry_board_w.get())
            h = int(self.entry_board_h.get())
            sq = float(self.entry_sq_size.get())
        except ValueError:
            messagebox.showerror("Lỗi nhập liệu", "Tham số lưới cờ và ô vuông không hợp lệ.")
            return
            
        self.camera_calib.set_board_parameters(w, h, sq)
        self.lbl_chessboard_status.configure(text="🔄 Đang xử lý tính toán hiệu chuẩn...")
        self.update()
        
        success, intrinsic, valid_count, rms = self.camera_calib.calibrate_from_images(self.chessboard_image_paths)
        
        if success:
            self.lbl_chessboard_status.configure(
                text=f"Trạng thái: Thành công! RMS = {rms:.4f} px (Hợp lệ {valid_count}/{len(self.chessboard_image_paths)} ảnh)"
            )
            self.txt_camera_matrix.configure(state="normal")
            self.txt_camera_matrix.delete("1.0", ctk.END)
            K = intrinsic.camera_matrix
            D = intrinsic.dist_coeffs
            matrix_text = f"Camera Matrix (K):\n" \
                          f"  [{K[0,0]:.1f}, {K[0,1]:.1f}, {K[0,2]:.1f}]\n" \
                          f"  [{K[1,0]:.1f}, {K[1,1]:.1f}, {K[1,2]:.1f}]\n" \
                          f"  [{K[2,0]:.1f}, {K[2,1]:.1f}, {K[2,2]:.1f}]\n\n" \
                          f"Distortion (D):\n" \
                          f"  [{D[0,0]:.4f}, {D[0,1]:.4f}, {D[0,2]:.4f}, {D[0,3]:.4f}, {D[0,4]:.4f}]"
            self.txt_camera_matrix.insert("1.0", matrix_text)
            self.txt_camera_matrix.configure(state="disabled")
            messagebox.showinfo("Thành công", f"Hiệu chuẩn camera thành công!\nRMS: {rms:.4f} px.")
        else:
            self.lbl_chessboard_status.configure(text="Trạng thái: Hiệu chuẩn thất bại")
            messagebox.showerror("Thất bại", f"Không đủ ảnh tìm thấy góc bàn cờ hợp lệ ({valid_count} ảnh).")

    def save_camera_intrinsic(self):
        """Lưu tệp cấu hình camera intrinsic."""
        if self.camera_calib.intrinsic.camera_matrix is None:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu hiệu chuẩn để lưu.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Lưu camera_intrinsic.json",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="camera_intrinsic.json"
        )
        if file_path:
            success = CalibrationIO.save_camera_intrinsic(file_path, self.camera_calib.intrinsic)
            if success:
                messagebox.showinfo("Thành công", f"Đã lưu ma trận camera intrinsic vào file:\n{file_path}")
            else:
                messagebox.showerror("Thất bại", "Lỗi lưu file.")

    def load_camera_intrinsic(self):
        """Nạp cấu hình camera intrinsic."""
        file_path = filedialog.askopenfilename(
            title="Nạp camera_intrinsic.json",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            intrinsic = CalibrationIO.load_camera_intrinsic(file_path)
            if intrinsic:
                self.camera_calib.intrinsic = intrinsic
                self.lbl_chessboard_status.configure(text=f"Đã nạp ma trận từ tệp. RMS = {intrinsic.rms:.4f} px")
                self.txt_camera_matrix.configure(state="normal")
                self.txt_camera_matrix.delete("1.0", ctk.END)
                K = intrinsic.camera_matrix
                D = intrinsic.dist_coeffs
                matrix_text = f"Camera Matrix (K) [LOADED]:\n" \
                              f"  [{K[0,0]:.1f}, {K[0,1]:.1f}, {K[0,2]:.1f}]\n" \
                              f"  [{K[1,0]:.1f}, {K[1,1]:.1f}, {K[1,2]:.1f}]\n" \
                              f"  [{K[2,0]:.1f}, {K[2,1]:.1f}, {K[2,2]:.1f}]\n\n" \
                              f"Distortion (D):\n" \
                              f"  [{D[0,0]:.4f}, {D[0,1]:.4f}, {D[0,2]:.4f}, {D[0,3]:.4f}, {D[0,4]:.4f}]"
                self.txt_camera_matrix.insert("1.0", matrix_text)
                self.txt_camera_matrix.configure(state="disabled")
                messagebox.showinfo("Thành công", "Đã nạp thông số nội camera từ file JSON!")
            else:
                messagebox.showerror("Thất bại", "Tệp tin không hợp lệ.")

    # =========================================================================
    # LOGIC CHẾ ĐỘ 2: ROBOT CALIBRATION (NHẬP TAY)
    # =========================================================================
    def add_point_manually(self):
        """Thêm cặp điểm nhập tay vào hệ hiệu chuẩn."""
        try:
            px = float(self.entry_pixel_x.get())
            py = float(self.entry_pixel_y.get())
            rx = float(self.entry_robot_x.get())
            ry = float(self.entry_robot_y.get())
        except ValueError:
            messagebox.showerror("Lỗi nhập liệu", "Tọa độ Pixel và Robot phải là số hợp lệ.")
            return
            
        self.robot_calib.add_point(px, py, rx, ry)
        
        # Xóa nội dung nhập
        self.entry_pixel_x.delete(0, ctk.END)
        self.entry_pixel_y.delete(0, ctk.END)
        self.entry_robot_x.delete(0, ctk.END)
        self.entry_robot_y.delete(0, ctk.END)
        
        self._refresh_point_table()

    def _refresh_point_table(self):
        """Vẽ lại bảng dữ liệu các điểm hiệu chuẩn."""
        # Xóa các widget dòng cũ
        for widgets in self.table_row_widgets:
            for w in widgets:
                w.destroy()
        self.table_row_widgets.clear()
        
        # Vẽ tiêu đề cột
        headers = ["No.", "Px", "Py", "Rx", "Ry", "Act"]
        for col_idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(self.table_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"))
            lbl.grid(row=0, column=col_idx, padx=4, pady=2, sticky="ew")
            
        # Vẽ dữ liệu điểm
        for idx, pt in enumerate(self.robot_calib.points):
            r = idx + 1
            lbl_no = ctk.CTkLabel(self.table_frame, text=str(pt.index), font=ctk.CTkFont(size=11))
            lbl_px = ctk.CTkLabel(self.table_frame, text=f"{pt.px:.0f}", font=ctk.CTkFont(size=11))
            lbl_py = ctk.CTkLabel(self.table_frame, text=f"{pt.py:.0f}", font=ctk.CTkFont(size=11))
            lbl_rx = ctk.CTkLabel(self.table_frame, text=f"{pt.rx:.1f}", font=ctk.CTkFont(size=11))
            lbl_ry = ctk.CTkLabel(self.table_frame, text=f"{pt.ry:.1f}", font=ctk.CTkFont(size=11))
            
            btn_del = ctk.CTkButton(
                self.table_frame,
                text="❌",
                width=24,
                height=18,
                fg_color="#F44336",
                hover_color="#D32F2F",
                font=ctk.CTkFont(size=10),
                command=lambda p_idx=pt.index: self.delete_point(p_idx)
            )
            
            lbl_no.grid(row=r, column=0, padx=4, pady=1)
            lbl_px.grid(row=r, column=1, padx=4, pady=1)
            lbl_py.grid(row=r, column=2, padx=4, pady=1)
            lbl_rx.grid(row=r, column=3, padx=4, pady=1)
            lbl_ry.grid(row=r, column=4, padx=4, pady=1)
            btn_del.grid(row=r, column=5, padx=4, pady=1)
            
            self.table_row_widgets.append([lbl_no, lbl_px, lbl_py, lbl_rx, lbl_ry, btn_del])
            
        # Cập nhật số điểm hiển thị
        n = len(self.robot_calib.points)
        self.lbl_points_count.configure(
            text=f"Số lượng điểm: {n} / 9 (Tối thiểu 9 điểm)",
            text_color="#4CAF50" if n >= 9 else ("#FF9800" if n >= 4 else "#F44336")
        )

    def delete_point(self, index):
        """Xóa điểm khỏi bảng."""
        self.robot_calib.delete_point(index)
        self._refresh_point_table()

    def calculate_robot_matrix(self):
        """Tính toán ma trận chuyển đổi tọa độ."""
        method = self.opt_algorithm.get()
        success, matrix, rms = self.robot_calib.calculate_matrix(method)
        
        if success:
            self.txt_robot_matrix.configure(state="normal")
            self.txt_robot_matrix.delete("1.0", ctk.END)
            
            if method == "Homography":
                matrix_text = f"Homography (3x3) [RMS: {rms:.2f} mm]:\n" \
                              f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n" \
                              f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]\n" \
                              f"  [{matrix[2,0]:.4f}, {matrix[2,1]:.4f}, {matrix[2,2]:.4f}]"
            else:
                matrix_text = f"Affine (2x3) [RMS: {rms:.2f} mm]:\n" \
                              f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n" \
                              f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]"
                              
            self.txt_robot_matrix.insert("1.0", matrix_text)
            self.txt_robot_matrix.configure(state="disabled")
            
            # Gửi ma trận legacy cho MainWindow hiển thị
            legacy_matrix = self._export_legacy_matrix(matrix, method)
            if self.on_matrix_changed_callback:
                try:
                    self.on_matrix_changed_callback(legacy_matrix)
                except Exception as e:
                    print(f"Lỗi truyền callback: {e}")
                    
            messagebox.showinfo("Thành công", f"Hiệu chuẩn ma trận Robot thành công!\nRMS: {rms:.2f} mm.")
        else:
            min_req = 4 if method == "Homography" else 3
            messagebox.showerror("Lỗi", f"Thuật toán {method} yêu cầu tối thiểu {min_req} điểm (đang có {len(self.robot_calib.points)}).")

    def _export_legacy_matrix(self, matrix, method):
        """Tính ma trận legacy scale/shift tương thích ngược gửi Dashboard."""
        if method == "Homography":
            scale_x = float(matrix[0, 0])
            scale_y = float(matrix[1, 1])
            shift_x = float(matrix[0, 2])
            shift_y = float(matrix[1, 2])
        else:
            scale_x = float(matrix[0, 0])
            scale_y = float(matrix[1, 1])
            shift_x = float(matrix[0, 2])
            shift_y = float(matrix[1, 2])
            
        return {
            "scale_x": abs(scale_x),
            "scale_y": abs(scale_y),
            "shift_x": shift_x,
            "shift_y": shift_y,
            "rotation": 0.0
        }

    def verify_manual_point(self):
        """Tính toán kiểm chứng từ tọa độ Pixel nhập tay."""
        try:
            px = float(self.entry_verify_px.get())
            py = float(self.entry_verify_py.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Tọa độ Pixel verify phải là số thực hợp lệ.")
            return
            
        rx, ry = self.transform(px, py)
        self.lbl_verify_result.configure(text=f"Robot (X, Y) dự kiến: {rx:.2f}, {ry:.2f}")
        
        # Sai số tham chiếu nếu có điểm gần
        min_dist = float('inf')
        nearest_pt = None
        for pt in self.robot_calib.points:
            dist = np.sqrt((pt.px - px)**2 + (pt.py - py)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_pt = pt
                
        if nearest_pt and min_dist < 30: # 30px
            error = np.sqrt((nearest_pt.rx - rx)**2 + (nearest_pt.ry - ry)**2)
            self.lbl_verify_error.configure(text=f"Sai số so với Điểm {nearest_pt.index}: {error:.2f} mm")
        else:
            self.lbl_verify_error.configure(text="Sai số kiểm chứng: -- mm (Không có điểm đối chiếu gần đó)")

    def save_robot_calibration(self):
        """Lưu cấu hình robot_calibration.json."""
        if self.robot_calib.matrix is None:
            messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu ma trận robot để lưu.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Lưu robot_calibration.json",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="robot_calibration.json"
        )
        if file_path:
            success = CalibrationIO.save_robot_calibration(
                file_path, 
                self.robot_calib.matrix, 
                self.robot_calib.points, 
                self.robot_calib.method,
                self.robot_calib.rms_error
            )
            if success:
                messagebox.showinfo("Thành công", f"Đã lưu ma trận hiệu chuẩn Robot vào:\n{file_path}")
            else:
                messagebox.showerror("Thất bại", "Lỗi lưu file.")

    def load_robot_calibration(self):
        """Nạp cấu hình robot_calibration.json."""
        file_path = filedialog.askopenfilename(
            title="Nạp robot_calibration.json",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            data = CalibrationIO.load_robot_calibration(file_path)
            if data:
                self.robot_calib.matrix = data["matrix"]
                self.robot_calib.method = data.get("method", "Homography")
                self.robot_calib.rms_error = data.get("rms", 0.0)
                self.robot_calib.points = data.get("points", [])
                
                # Cập nhật UI
                self.opt_algorithm.set(self.robot_calib.method)
                self._refresh_point_table()
                
                self.txt_robot_matrix.configure(state="normal")
                self.txt_robot_matrix.delete("1.0", ctk.END)
                matrix = self.robot_calib.matrix
                rms = self.robot_calib.rms_error
                method = self.robot_calib.method
                
                if method == "Homography":
                    matrix_text = f"Homography (3x3) [LOADED - RMS: {rms:.2f} mm]:\n" \
                                  f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n" \
                                  f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]\n" \
                                  f"  [{matrix[2,0]:.4f}, {matrix[2,1]:.4f}, {matrix[2,2]:.4f}]"
                else:
                    matrix_text = f"Affine (2x3) [LOADED - RMS: {rms:.2f} mm]:\n" \
                                  f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n" \
                                  f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]"
                                  
                self.txt_robot_matrix.insert("1.0", matrix_text)
                self.txt_robot_matrix.configure(state="disabled")
                
                # Đồng bộ về MainWindow
                legacy_matrix = self._export_legacy_matrix(matrix, method)
                if self.on_matrix_changed_callback:
                    try:
                        self.on_matrix_changed_callback(legacy_matrix)
                    except Exception as e:
                        print(f"Lỗi gọi callback: {e}")
                        
                messagebox.showinfo("Thành công", "Đã nạp thành công ma trận hiệu chuẩn Robot!")
            else:
                messagebox.showerror("Thất bại", "Tệp tin không hợp lệ.")

    def has_valid_matrix(self) -> bool:
        """Kiểm tra xem đã có ma trận Robot Calibration hợp lệ chưa."""
        return self.robot_calib.matrix is not None

    def transform(self, px_x, px_y):
        """Chuyển đổi tọa độ pixel camera sang tọa độ robot thực tế."""
        return self.robot_calib.transform(px_x, px_y)

    def cleanup(self):
        """Cleanup tài nguyên (nếu có)."""
        pass
