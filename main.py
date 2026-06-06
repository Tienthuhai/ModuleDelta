# File khởi chạy chính và điều phối hệ thống Delta Robot AI Dashboard
import customtkinter as ctk
from src.ui.main_window import MainWindow

def main():
    # 1. Khởi tạo giao diện chính CustomTkinter
    app = MainWindow()
    
    # 2. Hàm xử lý dọn dẹp tài nguyên khi đóng cửa sổ (nhấn nút X)
    def on_closing():
        app.is_running = False  # Ra lệnh dừng luồng AI ngầm
        app.serial_disconnect() # Đóng cổng Serial
        app.destroy()           # Giải phóng tài nguyên cửa sổ
        
    app.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 3. Kích hoạt vòng lặp chạy giao diện chính
    app.mainloop()

if __name__ == "__main__":
    main()
