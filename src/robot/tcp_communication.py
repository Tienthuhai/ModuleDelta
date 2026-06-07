import socket

class PLCTCPClient:
    """
    Quản lý kết nối TCP/IP Client tới PLC/Robot.
    Tương thích 100% với giao thức giaothuc.py (kết nối -> gửi -> đóng).
    """
    def __init__(self, ip="127.0.0.1", port=23, log_queue=None):
        self.ip = ip
        self.port = port
        self.log_queue = log_queue
        self.is_connected = False

    def log(self, message):
        """Ghi nhận log thông qua queue của Main Window hoặc in ra console."""
        if self.log_queue:
            self.log_queue.put(("log", f"[TCP PLC] {message}"))
        else:
            print(f"[TCP PLC] {message}")

    def connect(self):
        """Kiểm tra và kích hoạt chế độ TCP (thử kết nối nhanh để xác nhận server hoạt động)."""
        try:
            # Thử kết nối nhanh để kiểm tra xem Server (Hercules) có đang mở không
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1.5)
            test_socket.connect((self.ip, self.port))
            test_socket.close()
            
            self.is_connected = True
            self.log(f"🟢 Kết nối TCP thành công tới {self.ip}:{self.port}")
            return True
        except Exception as e:
            self.log(f"❌ Không thể kết nối tới {self.ip}:{self.port}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Ngắt chế độ TCP."""
        self.is_connected = False
        self.log("🔌 Đã ngắt kết nối TCP.")

    def send_data(self, data_str):
        """Mở kết nối, gửi dữ liệu và đóng socket ngay lập tức (không duy trì kết nối lâu dài)."""
        if not self.is_connected:
            self.log("⚠️ Cảnh báo: Chưa kết nối TCP! Tin nhắn bị bỏ qua.")
            return

        try:
            # Không thay đổi trình tự gửi nhận (kết nối -> gửi -> đóng)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2.0)
            client_socket.connect((self.ip, self.port))
            
            # Format dữ liệu kết thúc bằng \n như giaothuc.py
            packet = (data_str + "\n").encode('utf-8')
            client_socket.sendall(packet)
            client_socket.close()
            
            self.log(f"📤 Gửi TCP thành công: {data_str}")
        except Exception as e:
            self.log(f"❌ Lỗi gửi dữ liệu qua TCP: {e}")
