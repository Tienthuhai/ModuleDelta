import customtkinter as ctk
import time
from src.lang import get_texts

class LogPanel(ctk.CTkFrame):
    """
    Panel hiển thị nhật ký vận hành (Logs) phân loại theo Tabview:
    1. AI Log (Nhận diện, xử lý ảnh)
    2. Robot Log (Truyền lệnh, phản hồi Serial)
    3. Errors Log (Ngoại lệ, mất kết nối)
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._texts = get_texts()

        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self,
            text=self._texts["log_title"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.title_label.pack(pady=(5, 0))

        # Khởi tạo Tabview để phân loại log
        self.tabview = ctk.CTkTabview(self, height=180)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Thêm các thẻ tab
        self.tab_ai    = self.tabview.add(" AI Log ")
        self.tab_robot = self.tabview.add(" Robot Log ")
        self.tab_error = self.tabview.add(" System Errors ")

        # Tạo CTkTextbox cho tab AI Log
        self.txt_ai = ctk.CTkTextbox(
            self.tab_ai, bg_color="#1E1E1E", fg_color="#121212",
            text_color="#00FF00", font=("Consolas", 11)
        )
        self.txt_ai.pack(fill=ctk.BOTH, expand=True)
        self.txt_ai.configure(state="disabled")

        # Tạo CTkTextbox cho tab Robot Log
        self.txt_robot = ctk.CTkTextbox(
            self.tab_robot, bg_color="#1E1E1E", fg_color="#121212",
            text_color="#00E5FF", font=("Consolas", 11)
        )
        self.txt_robot.pack(fill=ctk.BOTH, expand=True)
        self.txt_robot.configure(state="disabled")

        # Tạo CTkTextbox cho tab Errors Log
        self.txt_error = ctk.CTkTextbox(
            self.tab_error, bg_color="#1E1E1E", fg_color="#121212",
            text_color="#FF3D00", font=("Consolas", 11)
        )
        self.txt_error.pack(fill=ctk.BOTH, expand=True)
        self.txt_error.configure(state="disabled")

        # Log khởi tạo ban đầu
        self.log_ai(self._texts["log_init_ai"])
        self.log_robot(self._texts["log_init_robot"])
        self.log_error(self._texts["log_init_error"])

    def apply_lang(self, texts: dict):
        """Cập nhật toàn bộ text theo ngôn ngữ mới."""
        self._texts = texts
        self.title_label.configure(text=texts["log_title"])

    def _append_log(self, textbox, message):
        """Hàm nội bộ nối dòng log mới vào textbox."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        textbox.configure(state="normal")
        textbox.insert(ctk.END, formatted_message)
        textbox.see(ctk.END)  # Cuộn xuống cuối
        textbox.configure(state="disabled")

    def log_ai(self, message):
        """Ghi log sự kiện xử lý AI."""
        self._append_log(self.txt_ai, message)

    def log_robot(self, message):
        """Ghi log lệnh truyền thông robot."""
        self._append_log(self.txt_robot, message)

    def log_error(self, message):
        """Ghi log lỗi hệ thống."""
        self._append_log(self.txt_error, message)

    def clear_logs(self):
        """Xóa trắng nhật ký ở cả 3 tab."""
        for txt in [self.txt_ai, self.txt_robot, self.txt_error]:
            txt.configure(state="normal")
            txt.delete("1.0", ctk.END)
            txt.configure(state="disabled")
