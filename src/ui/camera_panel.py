import customtkinter as ctk
from src.lang import get_texts

class CameraPanel(ctk.CTkFrame):
    """
    Panel hiển thị luồng hình ảnh Camera hoặc Video trực quan,
    kèm theo các thông tin giám sát như FPS và độ trễ xử lý.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._texts = get_texts()

        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self,
            text=self._texts["cam_title"],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)

        # Khung chứa nhãn hiển thị video (Nền đen)
        self.view_container = ctk.CTkFrame(self, fg_color="black")
        self.view_container.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Nhãn hiển thị hình ảnh chính
        self.video_label = ctk.CTkLabel(
            self.view_container,
            text=self._texts["cam_no_signal"],
            text_color="gray60",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.video_label.pack(fill=ctk.BOTH, expand=True)

        # Khung thanh trạng thái phụ
        self.status_bar = ctk.CTkFrame(self, height=25, fg_color="transparent")
        self.status_bar.pack(fill=ctk.X, side=ctk.BOTTOM, padx=5, pady=2)

        self.fps_label = ctk.CTkLabel(
            self.status_bar,
            text=self._texts["cam_fps_default"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4CAF50"
        )
        self.fps_label.pack(side=ctk.LEFT, padx=5)

        self.latency_label = ctk.CTkLabel(
            self.status_bar,
            text=self._texts["cam_latency_default"],
            font=ctk.CTkFont(size=11)
        )
        self.latency_label.pack(side=ctk.LEFT, padx=15)

        self.resolution_label = ctk.CTkLabel(
            self.status_bar,
            text=self._texts["cam_resolution"],
            font=ctk.CTkFont(size=11)
        )
        self.resolution_label.pack(side=ctk.RIGHT, padx=5)

    def apply_lang(self, texts: dict):
        """Cập nhật toàn bộ text theo ngôn ngữ mới."""
        self._texts = texts
        self.title_label.configure(text=texts["cam_title"])
        self.latency_label.configure(text=texts["cam_latency_default"])
        self.fps_label.configure(text=texts["cam_fps_default"])
        self.resolution_label.configure(text=texts["cam_resolution"])

    def update_image(self, pil_image):
        """Cập nhật frame ảnh mới lên màn hình."""
        width, height = pil_image.size
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(width, height))
        self.video_label.configure(image=ctk_image, text="")
        self.video_label.imgtk = ctk_image  # Tránh Garbage Collector giải phóng hình ảnh

    def update_fps(self, fps):
        """Cập nhật chỉ số khung hình/giây."""
        self.fps_label.configure(text=self._texts["cam_fps_fmt"].format(fps=fps))

    def update_latency(self, ms):
        """Cập nhật chỉ số độ trễ tính toán."""
        self.latency_label.configure(text=self._texts["cam_latency_fmt"].format(ms=ms))

    def reset_view(self):
        """Đặt lại trạng thái màn hình khi dừng hệ thống."""
        self.video_label.configure(
            image="",
            text=self._texts["cam_stopped"]
        )
        self.fps_label.configure(text=self._texts["cam_fps_default"])
        self.latency_label.configure(text=self._texts["cam_latency_default"])
