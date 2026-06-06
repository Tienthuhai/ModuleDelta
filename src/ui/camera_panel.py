import customtkinter as ctk
from PIL import ImageTk

class CameraPanel(ctk.CTkFrame):
    """
    Panel hiển thị luồng hình ảnh Camera hoặc Video trực quan,
    kèm theo các thông tin giám sát như FPS và độ trễ xử lý.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self, 
            text="📺 MÀN HÌNH CAMERA / VIDEO REAL-TIME", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)
        
        # Khung chứa nhãn hiển thị video (Nền đen)
        self.view_container = ctk.CTkFrame(self, fg_color="black")
        self.view_container.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
        
        # Nhãn hiển thị hình ảnh chính
        self.video_label = ctk.CTkLabel(
            self.view_container, 
            text="CHƯA CÓ TÍN HIỆU CAMERA\n(Bấm 'Bắt Đầu Chạy' để khởi động)", 
            text_color="gray60",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.video_label.pack(fill=ctk.BOTH, expand=True)
        
        # Khung thanh trạng thái phụ
        self.status_bar = ctk.CTkFrame(self, height=25, fg_color="transparent")
        self.status_bar.pack(fill=ctk.X, side=ctk.BOTTOM, padx=5, pady=2)
        
        self.fps_label = ctk.CTkLabel(
            self.status_bar, 
            text="FPS: --.-", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4CAF50"
        )
        self.fps_label.pack(side=ctk.LEFT, padx=5)
        
        self.latency_label = ctk.CTkLabel(
            self.status_bar, 
            text="Độ trễ: -- ms", 
            font=ctk.CTkFont(size=11)
        )
        self.latency_label.pack(side=ctk.LEFT, padx=15)
        
        self.resolution_label = ctk.CTkLabel(
            self.status_bar, 
            text="Độ phân giải hiển thị: 640x360", 
            font=ctk.CTkFont(size=11)
        )
        self.resolution_label.pack(side=ctk.RIGHT, padx=5)

    def update_image(self, pil_image):
        """Cập nhật frame ảnh mới lên màn hình."""
        imgtk = ImageTk.PhotoImage(image=pil_image)
        self.video_label.configure(image=imgtk, text="")
        self.video_label.imgtk = imgtk  # Tránh Garbage Collector giải phóng hình ảnh

    def update_fps(self, fps):
        """Cập nhật chỉ số khung hình/giây."""
        self.fps_label.configure(text=f"FPS: {fps:.1f}")
        
    def update_latency(self, ms):
        """Cập nhật chỉ số độ trễ tính toán."""
        self.latency_label.configure(text=f"Độ trễ: {ms} ms")
        
    def reset_view(self):
        """Đặt lại trạng thái màn hình khi dừng hệ thống."""
        self.video_label.configure(
            image="", 
            text="HỆ THỐNG ĐÃ DỪNG\n(Bấm 'Bắt Đầu Chạy' để khởi động lại)"
        )
        self.fps_label.configure(text="FPS: --.-")
        self.latency_label.configure(text="Độ trễ: -- ms")
