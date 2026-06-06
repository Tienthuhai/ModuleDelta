import customtkinter as ctk

class StatisticsPanel(ctk.CTkFrame):
    """
    Panel hiển thị thống kê năng suất hoạt động của hệ thống dưới dạng thẻ KPI lớn.
    Bao gồm: Tổng số sản phẩm, Số sản phẩm gửi robot, Số sản phẩm bị loại.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self, 
            text="📊 THỐNG KÊ VẬN HÀNH (KPI)", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)
        
        # ---------------- 1. THẺ: TỔNG SỐ VẬT THỂ DÒ TÌM ----------------
        self.card_total = ctk.CTkFrame(self, fg_color="#1E1E1E", border_width=1, border_color="#333333")
        self.card_total.pack(fill=ctk.X, padx=10, pady=5)
        
        self.lbl_total_title = ctk.CTkLabel(self.card_total, text="Tổng Số Sản Phẩm", font=ctk.CTkFont(size=11))
        self.lbl_total_title.pack(pady=(5, 0))
        
        self.lbl_total_val = ctk.CTkLabel(
            self.card_total, text="0", text_color="#2196F3", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.lbl_total_val.pack(pady=(0, 5))
        
        # ---------------- 2. THẺ: SỐ VẬT THỂ ĐÃ GỬI ROBOT GẮP ----------------
        self.card_sent = ctk.CTkFrame(self, fg_color="#1E1E1E", border_width=1, border_color="#333333")
        self.card_sent.pack(fill=ctk.X, padx=10, pady=5)
        
        self.lbl_sent_title = ctk.CTkLabel(self.card_sent, text="Đã Gửi Lệnh Robot", font=ctk.CTkFont(size=11))
        self.lbl_sent_title.pack(pady=(5, 0))
        
        self.lbl_sent_val = ctk.CTkLabel(
            self.card_sent, text="0", text_color="#4CAF50", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.lbl_sent_val.pack(pady=(0, 5))
        
        # ---------------- 3. THẺ: SỐ VẬT THỂ BỊ LOẠI (REJECTED) ----------------
        self.card_rejected = ctk.CTkFrame(self, fg_color="#1E1E1E", border_width=1, border_color="#333333")
        self.card_rejected.pack(fill=ctk.X, padx=10, pady=5)
        
        self.lbl_rejected_title = ctk.CTkLabel(self.card_rejected, text="Sản Phẩm Bị Loại", font=ctk.CTkFont(size=11))
        self.lbl_rejected_title.pack(pady=(5, 0))
        
        self.lbl_rejected_val = ctk.CTkLabel(
            self.card_rejected, text="0", text_color="#f44336", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.lbl_rejected_val.pack(pady=(0, 5))

    def update_stats(self, total, sent, rejected):
        """Cập nhật các số liệu thống kê lên màn hình."""
        self.lbl_total_val.configure(text=str(total))
        self.lbl_sent_val.configure(text=str(sent))
        self.lbl_rejected_val.configure(text=str(rejected))
        
    def reset_stats(self):
        """Đặt lại toàn bộ các bộ đếm về 0."""
        self.lbl_total_val.configure(text="0")
        self.lbl_sent_val.configure(text="0")
        self.lbl_rejected_val.configure(text="0")
        
    def increment_total(self):
        """Tăng số lượng tổng sản phẩm lên 1."""
        curr = int(self.lbl_total_val.cget("text"))
        self.lbl_total_val.configure(text=str(curr + 1))
        
    def increment_sent(self):
        """Tăng số lượng sản phẩm đã gửi đi lên 1."""
        curr = int(self.lbl_sent_val.cget("text"))
        self.lbl_sent_val.configure(text=str(curr + 1))
        
    def increment_rejected(self):
        """Tăng số lượng sản phẩm bị loại lên 1."""
        curr = int(self.lbl_rejected_val.cget("text"))
        self.lbl_rejected_val.configure(text=str(curr + 1))
        
    def get_stats(self):
        """Trả về dữ liệu thống kê hiện tại."""
        return {
            "total": int(self.lbl_total_val.cget("text")),
            "sent": int(self.lbl_sent_val.cget("text")),
            "rejected": int(self.lbl_rejected_val.cget("text"))
        }
