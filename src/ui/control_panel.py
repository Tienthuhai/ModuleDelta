import customtkinter as ctk
from tkinter import filedialog

class ControlPanel(ctk.CTkFrame):
    """
    Panel điều khiển các cài đặt AI, chọn nguồn Camera/Video,
    chỉnh thông số Confidence/IoU và kích hoạt chạy/dừng luồng AI.
    """
    def __init__(self, master, on_start_callback, on_stop_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_start_callback = on_start_callback
        self.on_stop_callback = on_stop_callback
        
        self.model_path = ""
        self.video_filepath = ""
        
        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self, 
            text="🧠 ĐIỀU KHIỂN AI & THIẾT LẬP", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)

        # ---------------- 1. KHU VỰC CHỌN NGUỒN PHÁT ----------------
        self.source_group = ctk.CTkFrame(self)
        self.source_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm nguồn phát
        ctk.CTkLabel(
            self.source_group, text="📁 Nguồn Hình Ảnh", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 2), sticky="w")
        
        self.source_var = ctk.IntVar(value=0) # 0 = Camera, 1 = Video
        self.rad_camera = ctk.CTkRadioButton(
            self.source_group, text="Webcam", variable=self.source_var, value=0, command=self.toggle_source
        )
        self.rad_camera.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.rad_video = ctk.CTkRadioButton(
            self.source_group, text="Video File", variable=self.source_var, value=1, command=self.toggle_source
        )
        self.rad_video.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        self.btn_browse_video = ctk.CTkButton(
            self.source_group, text="Chọn Video", command=self.browse_video, height=22, state="disabled"
        )
        self.btn_browse_video.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        self.lbl_video_status = ctk.CTkLabel(
            self.source_group, text="Chưa chọn video...", text_color="gray", font=ctk.CTkFont(size=11)
        )
        self.lbl_video_status.grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        # ---------------- 2. KHU VỰC CẤU HÌNH AI & MODEL ----------------
        self.ai_group = ctk.CTkFrame(self)
        self.ai_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm cấu hình AI
        ctk.CTkLabel(
            self.ai_group, text="⚙️ Cấu Hình YOLO & Device", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 2), anchor="w")
        
        self.btn_load_model = ctk.CTkButton(
            self.ai_group, text="🧠 Nạp Model (.pt)", fg_color="#4CAF50", hover_color="#45a049", command=self.browse_model
        )
        self.btn_load_model.pack(fill=ctk.X, padx=10, pady=5)
        
        self.lbl_model_status = ctk.CTkLabel(
            self.ai_group, text="Chưa nạp model...", text_color="gray", font=ctk.CTkFont(size=11)
        )
        self.lbl_model_status.pack(padx=10, pady=2, anchor="w")
        
        # Chọn thiết bị CPU/GPU
        self.lbl_device = ctk.CTkLabel(self.ai_group, text="Thiết bị phần cứng (Device):")
        self.lbl_device.pack(padx=10, pady=(5, 0), anchor="w")
        
        self.device_segmented = ctk.CTkSegmentedButton(self.ai_group, values=["CPU", "GPU (CUDA)"])
        self.device_segmented.set("CPU")
        self.device_segmented.pack(fill=ctk.X, padx=10, pady=5)

        # ---------------- 3. THANH TRƯỢT THÔNG SỐ (SLIDERS) ----------------
        self.slider_group = ctk.CTkFrame(self)
        self.slider_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm thanh trượt
        ctk.CTkLabel(
            self.slider_group, text="🎛️ Ngưỡng Tin Cậy & Bộ Lọc", font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 2), anchor="w")
        
        # Slider Confidence
        self.lbl_conf = ctk.CTkLabel(self.slider_group, text="Confidence Threshold (Conf): 0.55")
        self.lbl_conf.pack(padx=10, pady=(5, 0), anchor="w")
        
        self.slider_conf = ctk.CTkSlider(self.slider_group, from_=0.1, to=1.0, number_of_steps=18, command=self.update_conf_label)
        self.slider_conf.set(0.55)
        self.slider_conf.pack(fill=ctk.X, padx=10, pady=5)
        
        # Slider IoU
        self.lbl_iou = ctk.CTkLabel(self.slider_group, text="IoU Threshold: 0.45")
        self.lbl_iou.pack(padx=10, pady=(5, 0), anchor="w")
        
        self.slider_iou = ctk.CTkSlider(self.slider_group, from_=0.1, to=1.0, number_of_steps=18, command=self.update_iou_label)
        self.slider_iou.set(0.45)
        self.slider_iou.pack(fill=ctk.X, padx=10, pady=5)
        

        # ---------------- 4. NÚT ĐIỀU KHIỂN CHẠY/DỪNG ----------------
        self.action_group = ctk.CTkFrame(self, fg_color="transparent")
        self.action_group.pack(fill=ctk.X, padx=10, pady=10)
        
        self.btn_start = ctk.CTkButton(
            self.action_group, text="▶️ Bắt Đầu Chạy", fg_color="#2196F3", hover_color="#1976D2", command=self.on_start_callback
        )
        self.btn_start.pack(side=ctk.LEFT, expand=True, fill=ctk.X, padx=(0, 5))
        
        self.btn_stop = ctk.CTkButton(
            self.action_group, text="⏹️ Dừng Hệ Thống", fg_color="#f44336", hover_color="#d32f2f", command=self.on_stop_callback
        )
        self.btn_stop.pack(side=ctk.RIGHT, expand=True, fill=ctk.X, padx=(5, 0))

    def toggle_source(self):
        """Bật/tắt nút browse video khi thay đổi Radiobutton."""
        if self.source_var.get() == 1:
            self.btn_browse_video.configure(state="normal")
        else:
            self.btn_browse_video.configure(state="disabled")

    def browse_video(self):
        """Mở hộp thoại chọn tệp video."""
        file_path = filedialog.askopenfilename(
            title="Chọn file Video mô phỏng", 
            filetypes=[("Video Files", "*.mp4 *.avi")]
        )
        if file_path:
            self.video_filepath = file_path
            # Hiển thị tên file thu gọn
            filename = file_path.split("/")[-1]
            self.lbl_video_status.configure(text=f"Tệp: {filename}", text_color="#2196F3")

    def browse_model(self):
        """Mở hộp thoại chọn tệp mô hình YOLO."""
        file_path = filedialog.askopenfilename(
            title="Chọn file Model YOLO (.pt)", 
            filetypes=[("PyTorch Model", "*.pt")]
        )
        if file_path:
            self.model_path = file_path
            filename = file_path.split("/")[-1]
            self.lbl_model_status.configure(text=f"Nạp: {filename}", text_color="#4CAF50")

    def update_conf_label(self, val):
        """Cập nhật nhãn hiển thị giá trị Conf."""
        self.lbl_conf.configure(text=f"Confidence Threshold (Conf): {val:.2f}")

    def update_iou_label(self, val):
        """Cập nhật nhãn hiển thị giá trị IoU."""
        self.lbl_iou.configure(text=f"IoU Threshold: {val:.2f}")
        
    def get_settings(self):
        """Trả về toàn bộ cấu hình đang được thiết lập."""
        return {
            "source_type": self.source_var.get(),
            "video_path": self.video_filepath,
            "model_path": self.model_path,
            "device": "cuda" if "GPU" in self.device_segmented.get() else "cpu",
            "conf": self.slider_conf.get(),
            "iou": self.slider_iou.get()
        }
