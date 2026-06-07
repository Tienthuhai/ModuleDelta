# Module truyền thông điều khiển Robot Delta
import socket
from src import config

def send_coordinates_to_robot(class_name, x, y, data_queue=None):
    """
    Gửi dữ liệu qua giao thức TCP tương thích 100% với giaothuc.py.
    Kết nối tới IP:Port cấu hình từ GUI, gửi "Hello robot\n", sau đó đóng kết nối.
    
    Tham số:
        class_name (str): Tên nhãn vật thể (ví dụ: 'xoai')
        x (int): Tọa độ X trên khung hình camera gốc
        y (int): Tọa độ Y trên khung hình camera gốc
        data_queue (queue.Queue, optional): Hàng đợi để gửi thông báo log hiển thị lên Tkinter GUI
    """
    # Không đổi định dạng dữ liệu (single source of truth: Hello robot\n)
    data_string = "Hello robot\n"
    
    # --- 1. Ghi log lên Console và gửi lên Tkinter GUI ---
    log_msg = f"✅ TCP SENDING: {data_string.strip()} to {config.PLC_IP}:{config.PLC_PORT} (X:{int(x)}, Y:{int(y)}, Nhãn:{class_name})"
    if data_queue is not None:
        data_queue.put(("log", log_msg))
    else:
        print(f"[ROBOT_COMM] {log_msg}")
        
    # --- 2. KẾT NỐI VỚI ROBOT QUA TCP (100% tương thích giaothuc.py) ---
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((config.PLC_IP, config.PLC_PORT))
        client.send(data_string.encode())
        client.close()
    except Exception as e:
        err_msg = f"⚠️ Lỗi truyền thông TCP: {e}"
        if data_queue is not None:
            data_queue.put(("log", err_msg))
        else:
            print(f"[ROBOT_COMM] {err_msg}")
