# Module truyền thông điều khiển Robot Delta

def send_coordinates_to_robot(class_name, x, y, data_queue=None):
    """
    Đóng gói dữ liệu tọa độ vật thể và gửi cho Robot Delta (không sử dụng ID).
    
    Tham số:
        class_name (str): Tên nhãn vật thể (ví dụ: 'xoai')
        x (int): Tọa độ X trên khung hình camera gốc
        y (int): Tọa độ Y trên khung hình camera gốc
        data_queue (queue.Queue, optional): Hàng đợi để gửi thông báo log hiển thị lên Tkinter GUI
    """
    # Đóng gói dữ liệu dạng chuỗi ký tự (Không chứa ID)
    data_string = f"NHAN:{class_name},X:{int(x)},Y:{int(y)}"
    
    # --- 1. Ghi log lên Console và gửi lên Tkinter GUI ---
    log_msg = f"✅ ĐÃ QUA VẠCH: {data_string}"
    if data_queue is not None:
        data_queue.put(("log", log_msg))
    else:
        print(f"[ROBOT_COMM] {log_msg}")
        
    # --- 2. KẾT NỐI VỚI ROBOT THỰC TẾ (MỞ RỘNG TỰ CHỌN) ---
    # try:
    #     # import serial
    #     # ser = serial.Serial('COM3', 9600, timeout=1)
    #     # ser.write((data_string + "\n").encode())
    # except Exception as e:
    #     if data_queue is not None:
    #         data_queue.put(("log", f"⚠️ Lỗi truyền thông Robot: {e}"))
