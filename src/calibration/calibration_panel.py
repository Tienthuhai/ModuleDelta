import cv2
import customtkinter as ctk
import numpy as np
import os
from tkinter import messagebox, filedialog
from src.calibration.camera_calibration import CameraCalibration
from src.calibration.robot_calibration import RobotCalibration
from src.calibration.calibration_io import CalibrationIO
from src.lang import get_texts

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
        self._texts = get_texts()

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
        self._table_locked = False  # True khi hệ thống đang chạy
        # Cấu hình Layout cột chính
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- TOP AREA: CHỌN CHẾ ĐỘ CALIBRATION ----------------
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        self.mode_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_calib_mode_title = ctk.CTkLabel(
            self.mode_frame,
            text=self._texts["calib_mode_title"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_calib_mode_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 2), sticky="w")

        self.calib_mode_var = ctk.IntVar(value=0)  # 0 = Chessboard, 1 = Robot

        self.rad_chessboard = ctk.CTkRadioButton(
            self.mode_frame,
            text=self._texts["calib_chess_radio"],
            variable=self.calib_mode_var,
            value=0,
            command=self.on_tab_change
        )
        self.rad_chessboard.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.rad_robot = ctk.CTkRadioButton(
            self.mode_frame,
            text=self._texts["calib_robot_radio"],
            variable=self.calib_mode_var,
            value=1,
            command=self.on_tab_change
        )
        self.rad_robot.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Khung chứa nội dung từng chế độ
        self.tab_camera_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_robot_frame  = ctk.CTkFrame(self, fg_color="transparent")

        # Khởi tạo UI cho từng chế độ
        self._init_camera_tab_ui()
        self._init_robot_tab_ui()

        # Hiển thị mặc định: Chessboard
        self.tab_camera_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    def apply_lang(self, texts: dict):
        """Cập nhật toàn bộ text theo ngôn ngữ mới."""
        self._texts = texts
        # Mode selector
        self.lbl_calib_mode_title.configure(text=texts["calib_mode_title"])
        self.rad_chessboard.configure(text=texts["calib_chess_radio"])
        self.rad_robot.configure(text=texts["calib_robot_radio"])
        # Camera tab
        self.lbl_grid_title.configure(text=texts["calib_grid_label"])
        self.lbl_chessboard_status.configure(text=texts["calib_chess_status_default"])
        # Robot tab
        self.lbl_pixel_label.configure(text=texts["calib_pixel_label"])
        self.lbl_robot_label.configure(text=texts["calib_robot_label"])
        self.lbl_point_table_title.configure(text=texts["calib_point_table_title"])
        self.lbl_affine_method.configure(text=texts["calib_affine_method"])
        self.lbl_verify_title.configure(text=texts["calib_verify_title"])
        self.lbl_verify_result.configure(text=texts["calib_verify_result_default"])
        self.lbl_verify_error.configure(text=texts["calib_verify_error_default"])
        # Refresh count label
        n = len(self.robot_calib.points)
        self.lbl_points_count.configure(
            text=texts["calib_points_count"].format(n=n),
            text_color="#4CAF50" if n >= 3 else "#F44336"
        )

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
        self.tab_camera_frame.grid_rowconfigure(2, weight=1)  # Danh sách ảnh giãn nở

        # 1.1 Cấu hình lưới bàn cờ
        grid_settings = ctk.CTkFrame(self.tab_camera_frame)
        grid_settings.grid(row=0, column=0, padx=5, pady=4, sticky="ew")
        grid_settings.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_grid_title = ctk.CTkLabel(
            grid_settings, text=self._texts["calib_grid_label"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_grid_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 0))

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
            btn_group, text="📁 Load Images",
            command=self.load_chessboard_images,
            fg_color="#3B82F6", hover_color="#2563EB", height=32
        )
        self.btn_load_images.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=2)

        self.btn_run_calib = ctk.CTkButton(
            btn_group, text="⚡ Run Calib",
            command=self.run_chessboard_calibration,
            fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_run_calib.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=2)

        # 1.3 Danh sách ảnh đã nạp
        self.image_list = ctk.CTkTextbox(self.tab_camera_frame, height=130, font=("Consolas", 10))
        self.image_list.grid(row=2, column=0, padx=5, pady=4, sticky="nsew")
        self.image_list.insert("1.0", self._texts["calib_image_list_default"])
        self.image_list.configure(state="disabled")

        # 1.4 Hiển thị kết quả Ma trận camera
        result_group = ctk.CTkFrame(self.tab_camera_frame)
        result_group.grid(row=3, column=0, padx=5, pady=4, sticky="ew")

        self.lbl_chessboard_status = ctk.CTkLabel(
            result_group,
            text=self._texts["calib_chess_status_default"],
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_chessboard_status.pack(padx=8, pady=2, anchor="w")

        self.txt_camera_matrix = ctk.CTkTextbox(
            result_group, height=110, font=("Consolas", 10),
            fg_color="#121212", text_color="#00FF00"
        )
        self.txt_camera_matrix.pack(fill=ctk.X, padx=5, pady=4)
        self.txt_camera_matrix.insert("1.0", self._texts["calib_matrix_default"])
        self.txt_camera_matrix.configure(state="disabled")

        # 1.5 Lưu & Nạp Camera Intrinsic file
        io_group = ctk.CTkFrame(self.tab_camera_frame, fg_color="transparent")
        io_group.grid(row=4, column=0, padx=5, pady=4, sticky="ew")

        self.btn_save_intrinsic = ctk.CTkButton(
            io_group, text="💾 Save Intrinsic",
            command=self.save_camera_intrinsic, height=32
        )
        self.btn_save_intrinsic.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=3)

        self.btn_load_intrinsic = ctk.CTkButton(
            io_group, text="📂 Load Intrinsic",
            command=self.load_camera_intrinsic, height=32
        )
        self.btn_load_intrinsic.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=3)

    # =========================================================================
    # CHẾ ĐỘ 2: ROBOT COORDINATE CALIBRATION (NHẬP TAY)
    # =========================================================================
    def _init_robot_tab_ui(self):
        self.tab_robot_frame.grid_columnconfigure(0, weight=1)
        self.tab_robot_frame.grid_rowconfigure(0, weight=1)

        outer_scroll = ctk.CTkScrollableFrame(self.tab_robot_frame, fg_color="transparent")
        outer_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        outer_scroll.grid_columnconfigure(0, weight=1)
        robot_parent = outer_scroll

        # 2.1 Nhập điểm thủ công (Manual Point Inputs)
        entry_group = ctk.CTkFrame(robot_parent)
        entry_group.grid(row=0, column=0, padx=5, pady=4, sticky="ew")
        entry_group.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_pixel_label = ctk.CTkLabel(
            entry_group, text=self._texts["calib_pixel_label"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_pixel_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 0))

        self.lbl_robot_label = ctk.CTkLabel(
            entry_group, text=self._texts["calib_robot_label"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_robot_label.grid(row=0, column=2, columnspan=2, sticky="w", padx=6, pady=(2, 0))

        self.entry_pixel_x = ctk.CTkEntry(entry_group, placeholder_text="Pixel X", width=65)
        self.entry_pixel_x.grid(row=1, column=0, padx=3, pady=4, sticky="ew")

        self.entry_pixel_y = ctk.CTkEntry(entry_group, placeholder_text="Pixel Y", width=65)
        self.entry_pixel_y.grid(row=1, column=1, padx=3, pady=4, sticky="ew")

        self.entry_robot_x = ctk.CTkEntry(entry_group, placeholder_text="Robot X", width=65)
        self.entry_robot_x.grid(row=1, column=2, padx=3, pady=4, sticky="ew")

        self.entry_robot_y = ctk.CTkEntry(entry_group, placeholder_text="Robot Y", width=65)
        self.entry_robot_y.grid(row=1, column=3, padx=3, pady=4, sticky="ew")

        self.btn_add_pt = ctk.CTkButton(
            entry_group, text="📍 Add Point",
            command=self.add_point_manually,
            fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_add_pt.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        # 2.2 Bảng dữ liệu điểm
        self.lbl_point_table_title = ctk.CTkLabel(
            robot_parent,
            text=self._texts["calib_point_table_title"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFD700"
        )
        self.lbl_point_table_title.grid(row=1, column=0, padx=8, pady=(6, 2), sticky="w")

        self.table_frame = ctk.CTkScrollableFrame(robot_parent, height=160)
        self.table_frame.grid(row=2, column=0, padx=5, pady=(0, 4), sticky="ew")
        self.table_row_widgets = []

        # 2.3 Chỉ dùng Affine (NVKCalibration)
        calc_ctrl = ctk.CTkFrame(robot_parent)
        calc_ctrl.grid(row=3, column=0, padx=5, pady=4, sticky="ew")
        calc_ctrl.grid_columnconfigure((0, 1), weight=1)

        self.lbl_affine_method = ctk.CTkLabel(
            calc_ctrl,
            text=self._texts["calib_affine_method"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00E5FF"
        )
        self.lbl_affine_method.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_calc_matrix = ctk.CTkButton(
            calc_ctrl, text="📊 Calculate Matrix",
            command=self.calculate_robot_matrix,
            fg_color="#10B981", hover_color="#059669", height=32
        )
        self.btn_calc_matrix.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.lbl_points_count = ctk.CTkLabel(
            calc_ctrl,
            text=self._texts["calib_points_count"].format(n=0),
            font=ctk.CTkFont(size=11)
        )
        self.lbl_points_count.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=1)

        self.txt_robot_matrix = ctk.CTkTextbox(
            calc_ctrl, height=80, font=("Consolas", 10),
            fg_color="#121212", text_color="#00E5FF"
        )
        self.txt_robot_matrix.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
        self.txt_robot_matrix.insert("1.0", self._texts["calib_robot_matrix_default"])
        self.txt_robot_matrix.configure(state="disabled")

        # 2.4 Verification Mode
        verify_frame = ctk.CTkFrame(robot_parent)
        verify_frame.grid(row=4, column=0, padx=5, pady=4, sticky="ew")
        verify_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_verify_title = ctk.CTkLabel(
            verify_frame,
            text=self._texts["calib_verify_title"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_verify_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 0))

        self.entry_verify_px = ctk.CTkEntry(verify_frame, placeholder_text="Pixel X verify", height=28)
        self.entry_verify_px.grid(row=1, column=0, padx=4, pady=3, sticky="ew")

        self.entry_verify_py = ctk.CTkEntry(verify_frame, placeholder_text="Pixel Y verify", height=28)
        self.entry_verify_py.grid(row=1, column=1, padx=4, pady=3, sticky="ew")

        self.btn_verify_pt = ctk.CTkButton(
            verify_frame, text="🔍 Verify Point",
            command=self.verify_manual_point, height=28
        )
        self.btn_verify_pt.grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="ew")

        self.lbl_verify_result = ctk.CTkLabel(
            verify_frame,
            text=self._texts["calib_verify_result_default"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_verify_result.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=1)

        self.lbl_verify_error = ctk.CTkLabel(
            verify_frame,
            text=self._texts["calib_verify_error_default"],
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.lbl_verify_error.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=1)

        # 2.5 Nút lưu nạp robot calib
        robot_io = ctk.CTkFrame(robot_parent, fg_color="transparent")
        robot_io.grid(row=5, column=0, padx=5, pady=4, sticky="ew")

        self.btn_save_robot = ctk.CTkButton(
            robot_io, text="💾 Save Robot",
            command=self.save_robot_calibration, height=32
        )
        self.btn_save_robot.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=3)

        self.btn_load_robot = ctk.CTkButton(
            robot_io, text="📂 Load Robot",
            command=self.load_robot_calibration, height=32
        )
        self.btn_load_robot.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=3)

        # Vẽ bảng điểm ban đầu
        self._refresh_point_table()

    # =========================================================================
    # LOGIC CHẾ ĐỘ 1: CHESSBOARD CALIBRATION
    # =========================================================================
    def load_chessboard_images(self):
        """Tải danh sách ảnh từ thư mục."""
        t = self._texts
        dir_path = filedialog.askdirectory(title=t["calib_dlg_load_intrinsic"])
        if not dir_path:
            return

        valid_exts = (".jpg", ".jpeg", ".png", ".bmp")
        self.chessboard_image_paths = []
        try:
            for file in os.listdir(dir_path):
                if file.lower().endswith(valid_exts):
                    self.chessboard_image_paths.append(os.path.join(dir_path, file))
        except Exception as e:
            messagebox.showerror(t["mb_error"], t["calib_mb_dir_error"].format(e=e))
            return

        if not self.chessboard_image_paths:
            messagebox.showwarning(t["mb_warning"], t["calib_mb_no_images"])
            return

        self.image_list.configure(state="normal")
        self.image_list.delete("1.0", ctk.END)
        self.image_list.insert(
            ctk.END,
            t["calib_image_list_loaded"].format(n=len(self.chessboard_image_paths), path=dir_path)
        )
        for path in self.chessboard_image_paths:
            self.image_list.insert(ctk.END, f"- {os.path.basename(path)}\n")
        self.image_list.configure(state="disabled")

        self.lbl_chessboard_status.configure(
            text=t["calib_status_loaded"].format(n=len(self.chessboard_image_paths))
        )

    def run_chessboard_calibration(self):
        """Chạy tính toán thông số nội camera."""
        t = self._texts
        if not self.chessboard_image_paths:
            messagebox.showwarning(t["mb_warning"], t["calib_mb_need_images"])
            return

        try:
            w = int(self.entry_board_w.get())
            h = int(self.entry_board_h.get())
            sq = float(self.entry_sq_size.get())
        except ValueError:
            messagebox.showerror(t["mb_input_error"], t["calib_mb_grid_error"])
            return

        self.camera_calib.set_board_parameters(w, h, sq)
        self.lbl_chessboard_status.configure(text=t["calib_status_running"])
        self.update()

        success, intrinsic, valid_count, rms = self.camera_calib.calibrate_from_images(self.chessboard_image_paths)

        if success:
            self.lbl_chessboard_status.configure(
                text=t["calib_status_success"].format(
                    rms=rms, valid=valid_count, total=len(self.chessboard_image_paths)
                )
            )
            self.txt_camera_matrix.configure(state="normal")
            self.txt_camera_matrix.delete("1.0", ctk.END)
            K = intrinsic.camera_matrix
            D = intrinsic.dist_coeffs
            matrix_text = (f"Camera Matrix (K):\n"
                           f"  [{K[0,0]:.1f}, {K[0,1]:.1f}, {K[0,2]:.1f}]\n"
                           f"  [{K[1,0]:.1f}, {K[1,1]:.1f}, {K[1,2]:.1f}]\n"
                           f"  [{K[2,0]:.1f}, {K[2,1]:.1f}, {K[2,2]:.1f}]\n\n"
                           f"Distortion (D):\n"
                           f"  [{D[0,0]:.4f}, {D[0,1]:.4f}, {D[0,2]:.4f}, {D[0,3]:.4f}, {D[0,4]:.4f}]")
            self.txt_camera_matrix.insert("1.0", matrix_text)
            self.txt_camera_matrix.configure(state="disabled")
            messagebox.showinfo(t["mb_success"], t["calib_mb_success"].format(rms=rms))
        else:
            self.lbl_chessboard_status.configure(text=t["calib_status_fail"])
            messagebox.showerror(t["mb_failed"], t["calib_mb_fail"].format(valid=valid_count))

    def save_camera_intrinsic(self):
        """Lưu tệp cấu hình camera intrinsic."""
        t = self._texts
        if self.camera_calib.intrinsic.camera_matrix is None:
            messagebox.showwarning(t["mb_warning"], t["calib_mb_no_data"])
            return

        file_path = filedialog.asksaveasfilename(
            title=t["calib_dlg_save_intrinsic"],
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="camera_intrinsic.json"
        )
        if file_path:
            success = CalibrationIO.save_camera_intrinsic(file_path, self.camera_calib.intrinsic)
            if success:
                messagebox.showinfo(t["mb_success"], t["calib_mb_save_intrinsic"].format(path=file_path))
            else:
                messagebox.showerror(t["mb_failed"], t["calib_mb_save_fail"])

    def load_camera_intrinsic(self):
        """Nạp cấu hình camera intrinsic."""
        t = self._texts
        file_path = filedialog.askopenfilename(
            title=t["calib_dlg_load_intrinsic"],
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            intrinsic = CalibrationIO.load_camera_intrinsic(file_path)
            if intrinsic:
                self.camera_calib.intrinsic = intrinsic
                self.lbl_chessboard_status.configure(
                    text=t["calib_status_intrinsic_loaded"].format(rms=intrinsic.rms)
                )
                self.txt_camera_matrix.configure(state="normal")
                self.txt_camera_matrix.delete("1.0", ctk.END)
                K = intrinsic.camera_matrix
                D = intrinsic.dist_coeffs
                matrix_text = (f"Camera Matrix (K) [LOADED]:\n"
                               f"  [{K[0,0]:.1f}, {K[0,1]:.1f}, {K[0,2]:.1f}]\n"
                               f"  [{K[1,0]:.1f}, {K[1,1]:.1f}, {K[1,2]:.1f}]\n"
                               f"  [{K[2,0]:.1f}, {K[2,1]:.1f}, {K[2,2]:.1f}]\n\n"
                               f"Distortion (D):\n"
                               f"  [{D[0,0]:.4f}, {D[0,1]:.4f}, {D[0,2]:.4f}, {D[0,3]:.4f}, {D[0,4]:.4f}]")
                self.txt_camera_matrix.insert("1.0", matrix_text)
                self.txt_camera_matrix.configure(state="disabled")
                messagebox.showinfo(t["mb_success"], t["calib_mb_intrinsic_loaded"])
            else:
                messagebox.showerror(t["mb_failed"], t["calib_mb_invalid_file"])

    # =========================================================================
    # LOGIC CHẾ ĐỘ 2: ROBOT CALIBRATION (NHẬP TAY)
    # =========================================================================
    def add_point_manually(self):
        """Thêm cặp điểm nhập tay vào hệ hiệu chuẩn."""
        t = self._texts
        try:
            px = float(self.entry_pixel_x.get())
            py = float(self.entry_pixel_y.get())
            rx = float(self.entry_robot_x.get())
            ry = float(self.entry_robot_y.get())
        except ValueError:
            messagebox.showerror(t["mb_input_error"], t["calib_mb_point_error"])
            return

        self.robot_calib.add_point(px, py, rx, ry)

        self.entry_pixel_x.delete(0, ctk.END)
        self.entry_pixel_y.delete(0, ctk.END)
        self.entry_robot_x.delete(0, ctk.END)
        self.entry_robot_y.delete(0, ctk.END)

        self._refresh_point_table()

    def _refresh_point_table(self):
        """Vẽ lại bảng dữ liệu các điểm hiệu chuẩn (có thể sửa trực tiếp)."""
        for widgets in self.table_row_widgets:
            for w in widgets:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.table_row_widgets.clear()

        headers = ["No.", "Px", "Py", "Rx", "Ry", ""]
        col_widths = [28, 58, 58, 62, 62, 0]
        for col_idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.table_frame, text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=col_widths[col_idx]
            )
            lbl.grid(row=0, column=col_idx, padx=2, pady=(2, 4), sticky="ew")

        for idx, pt in enumerate(self.robot_calib.points):
            r = idx + 1

            lbl_no = ctk.CTkLabel(
                self.table_frame, text=str(pt.index),
                font=ctk.CTkFont(size=11, weight="bold"),
                width=28, text_color="#00E5FF"
            )

            entry_state = "disabled" if self._table_locked else "normal"
            entry_cfg = dict(width=58, height=26, font=ctk.CTkFont(size=11), state=entry_state)

            ent_px = ctk.CTkEntry(self.table_frame, **entry_cfg)
            ent_py = ctk.CTkEntry(self.table_frame, **entry_cfg)
            ent_rx = ctk.CTkEntry(self.table_frame, **{**entry_cfg, "width": 62})
            ent_ry = ctk.CTkEntry(self.table_frame, **{**entry_cfg, "width": 62})

            for ent, val, fmt in [
                (ent_px, pt.px, "{:.0f}"),
                (ent_py, pt.py, "{:.0f}"),
                (ent_rx, pt.rx, "{:.3f}"),
                (ent_ry, pt.ry, "{:.3f}")
            ]:
                if entry_state == "normal":
                    ent.insert(0, fmt.format(val))
                else:
                    ent.configure(state="normal")
                    ent.insert(0, fmt.format(val))
                    ent.configure(state="disabled")

            btn_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")

            btn_save = ctk.CTkButton(
                btn_frame, text="✅",
                width=26, height=24,
                fg_color="#10B981", hover_color="#059669",
                font=ctk.CTkFont(size=11),
                state="disabled" if self._table_locked else "normal",
                command=lambda p_idx=pt.index, epx=ent_px, epy=ent_py, erx=ent_rx, ery=ent_ry:
                    self._save_point_edit(p_idx, epx, epy, erx, ery)
            )
            btn_save.pack(side=ctk.LEFT, padx=(0, 2))

            btn_del = ctk.CTkButton(
                btn_frame, text="❌",
                width=26, height=24,
                fg_color="#F44336", hover_color="#D32F2F",
                font=ctk.CTkFont(size=11),
                state="disabled" if self._table_locked else "normal",
                command=lambda p_idx=pt.index: self.delete_point(p_idx)
            )
            btn_del.pack(side=ctk.LEFT)

            lbl_no.grid(row=r, column=0, padx=2, pady=2, sticky="ew")
            ent_px.grid(row=r, column=1, padx=2, pady=2)
            ent_py.grid(row=r, column=2, padx=2, pady=2)
            ent_rx.grid(row=r, column=3, padx=2, pady=2)
            ent_ry.grid(row=r, column=4, padx=2, pady=2)
            btn_frame.grid(row=r, column=5, padx=2, pady=2)

            self.table_row_widgets.append([lbl_no, ent_px, ent_py, ent_rx, ent_ry, btn_frame])

        n = len(self.robot_calib.points)
        self.lbl_points_count.configure(
            text=self._texts["calib_points_count"].format(n=n),
            text_color="#4CAF50" if n >= 3 else "#F44336"
        )

    def _save_point_edit(self, index, ent_px, ent_py, ent_rx, ent_ry):
        """Lưu giá trị được sửa trực tiếp trong bảng điểm."""
        t = self._texts
        try:
            px = float(ent_px.get())
            py = float(ent_py.get())
            rx = float(ent_rx.get())
            ry = float(ent_ry.get())
        except ValueError:
            messagebox.showerror(t["mb_input_error"], t["calib_mb_edit_error"])
            return
        self.robot_calib.update_point(index, px, py, rx, ry)
        self._refresh_point_table()

    def delete_point(self, index):
        """Xóa điểm khỏi bảng."""
        self.robot_calib.delete_point(index)
        self._refresh_point_table()

    def calculate_robot_matrix(self):
        """Tính toán ma trận Affine (NVKCalibration) từ các điểm đã nhập."""
        t = self._texts
        success, matrix, rms = self.robot_calib.calculate_matrix("Affine")

        if success:
            self.txt_robot_matrix.configure(state="normal")
            self.txt_robot_matrix.delete("1.0", ctk.END)

            matrix_text = (f"Affine NVK (2x3) [RMS: {rms:.4f} mm]:\n"
                           f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n"
                           f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]")

            self.txt_robot_matrix.insert("1.0", matrix_text)
            self.txt_robot_matrix.configure(state="disabled")

            legacy_matrix = self._export_legacy_matrix(matrix, "Affine")
            if self.on_matrix_changed_callback:
                try:
                    self.on_matrix_changed_callback(legacy_matrix)
                except Exception as e:
                    print(f"Lỗi truyền callback: {e}")

            messagebox.showinfo(t["mb_success"], t["calib_mb_affine_success"].format(rms=rms))
        else:
            messagebox.showerror(
                t["mb_error"],
                t["calib_mb_affine_fail"].format(n=len(self.robot_calib.points))
            )

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
        t = self._texts
        try:
            px = float(self.entry_verify_px.get())
            py = float(self.entry_verify_py.get())
        except ValueError:
            messagebox.showerror(t["mb_error"], t["calib_mb_verify_error"])
            return

        rx, ry = self.transform(px, py)
        self.lbl_verify_result.configure(
            text=t["calib_verify_result_fmt"].format(rx=rx, ry=ry)
        )

        min_dist = float('inf')
        nearest_pt = None
        for pt in self.robot_calib.points:
            dist = np.sqrt((pt.px - px)**2 + (pt.py - py)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_pt = pt

        if nearest_pt and min_dist < 30:
            error = np.sqrt((nearest_pt.rx - rx)**2 + (nearest_pt.ry - ry)**2)
            self.lbl_verify_error.configure(
                text=t["calib_verify_error_fmt"].format(idx=nearest_pt.index, error=error)
            )
        else:
            self.lbl_verify_error.configure(text=t["calib_verify_no_ref"])

    def save_robot_calibration(self):
        """Lưu cấu hình robot_calibration.json."""
        t = self._texts
        if self.robot_calib.matrix is None:
            messagebox.showwarning(t["mb_warning"], t["calib_mb_no_robot_matrix"])
            return

        file_path = filedialog.asksaveasfilename(
            title=t["calib_dlg_save_robot"],
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
                messagebox.showinfo(t["mb_success"], t["calib_mb_save_robot"].format(path=file_path))
            else:
                messagebox.showerror(t["mb_failed"], t["calib_mb_save_fail"])

    def load_robot_calibration(self):
        """Nạp cấu hình robot_calibration.json."""
        t = self._texts
        file_path = filedialog.askopenfilename(
            title=t["calib_dlg_load_robot"],
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            data = CalibrationIO.load_robot_calibration(file_path)
            if data:
                self.robot_calib.matrix = data["matrix"]
                self.robot_calib.method = "Affine"
                self.robot_calib.rms_error = data.get("rms", 0.0)
                self.robot_calib.points = data.get("points", [])

                if len(self.robot_calib.points) >= 3:
                    uncalib   = [(pt.px, pt.py) for pt in self.robot_calib.points]
                    calib_pts = [(pt.rx, pt.ry) for pt in self.robot_calib.points]
                    try:
                        from nvk_calibration import NVKCalibration as NVK
                        self.robot_calib._nvk = NVK(uncalib, calib_pts)
                    except Exception:
                        pass

                self._refresh_point_table()

                self.txt_robot_matrix.configure(state="normal")
                self.txt_robot_matrix.delete("1.0", ctk.END)
                matrix = self.robot_calib.matrix
                rms    = self.robot_calib.rms_error

                matrix_text = (f"Affine NVK (2x3) [LOADED - RMS: {rms:.4f} mm]:\n"
                               f"  [{matrix[0,0]:.4f}, {matrix[0,1]:.4f}, {matrix[0,2]:.4f}]\n"
                               f"  [{matrix[1,0]:.4f}, {matrix[1,1]:.4f}, {matrix[1,2]:.4f}]")

                self.txt_robot_matrix.insert("1.0", matrix_text)
                self.txt_robot_matrix.configure(state="disabled")

                legacy_matrix = self._export_legacy_matrix(matrix, "Affine")
                if self.on_matrix_changed_callback:
                    try:
                        self.on_matrix_changed_callback(legacy_matrix)
                    except Exception as e:
                        print(f"Lỗi gọi callback: {e}")

                messagebox.showinfo(t["mb_success"], t["calib_mb_load_robot"])
            else:
                messagebox.showerror(t["mb_failed"], t["calib_mb_invalid_file"])

    def has_valid_matrix(self) -> bool:
        """Kiểm tra xem đã có ma trận Robot Calibration (Affine) hợp lệ chưa."""
        return self.robot_calib.matrix is not None

    def has_valid_intrinsic(self) -> bool:
        """Kiểm tra K, D từ Chessboard Calibration có hợp lệ không (rms > 0)."""
        return self.camera_calib.intrinsic.rms > 0.0

    def get_active_mode(self) -> str:
        """Trả về chế độ calibration đang active theo radio button."""
        return "chessboard" if self.calib_mode_var.get() == 0 else "robot"

    def undistort_point(self, px: float, py: float) -> tuple:
        """Khử méo ống kính cho tọa độ pixel đơn lẻ dùng K, D từ Chessboard."""
        try:
            K = self.camera_calib.intrinsic.camera_matrix
            D = self.camera_calib.intrinsic.dist_coeffs
            pts = np.array([[[float(px), float(py)]]], dtype=np.float32)
            undistorted = cv2.undistortPoints(pts, K, D, P=K)
            return float(undistorted[0, 0, 0]), float(undistorted[0, 0, 1])
        except Exception as e:
            print(f"Lỗi undistort_point: {e}")
            return float(px), float(py)

    def transform(self, px_x, px_y):
        """Chuyển đổi tọa độ pixel camera sang tọa độ robot thực tế (Affine)."""
        return self.robot_calib.transform(px_x, px_y)

    def lock_for_running(self):
        """Khoá toàn bộ controls Calibration khi hệ thống AI đang chạy."""
        self._table_locked = True
        self.rad_chessboard.configure(state="disabled")
        self.rad_robot.configure(state="disabled")
        self.btn_load_images.configure(state="disabled")
        self.btn_run_calib.configure(state="disabled")
        self.btn_save_intrinsic.configure(state="disabled")
        self.btn_load_intrinsic.configure(state="disabled")
        self.btn_add_pt.configure(state="disabled")
        self.btn_calc_matrix.configure(state="disabled")
        self.btn_save_robot.configure(state="disabled")
        self.btn_load_robot.configure(state="disabled")
        self._refresh_point_table()

    def unlock_for_editing(self):
        """Mở khoá toàn bộ controls Calibration khi hệ thống AI dừng lại."""
        self._table_locked = False
        self.rad_chessboard.configure(state="normal")
        self.rad_robot.configure(state="normal")
        self.btn_load_images.configure(state="normal")
        self.btn_run_calib.configure(state="normal")
        self.btn_save_intrinsic.configure(state="normal")
        self.btn_load_intrinsic.configure(state="normal")
        self.btn_add_pt.configure(state="normal")
        self.btn_calc_matrix.configure(state="normal")
        self.btn_save_robot.configure(state="normal")
        self.btn_load_robot.configure(state="normal")
        self._refresh_point_table()

    def cleanup(self):
        """Cleanup tài nguyên (nếu có)."""
        pass
