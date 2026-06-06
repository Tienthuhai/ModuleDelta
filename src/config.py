# File cấu hình đơn giản hóa cho hệ thống Delta Robot AI

# --- Cấu hình Camera ---
CAMERA_INDEX = 1           # Index của camera ngoài. Thay đổi thành 0 nếu dùng webcam laptop.
CAMERA_WIDTH = 1280        # Chiều rộng frame camera gốc
CAMERA_HEIGHT = 720        # Chiều cao frame camera gốc

# --- Cấu hình Vùng Bắt Tín Hiệu (Trigger Zone) ---
# Vùng bắt tín hiệu nằm ở chính giữa khung hình (trực quan trên toàn ảnh). 
# TRIGGER_OFFSET là khoảng cách (pixel) lên và xuống tính từ đường chia đôi ngang của bức ảnh.
TRIGGER_OFFSET = 10        # Vùng bắt tín hiệu = mid_y - 10 đến mid_y + 10

# --- Logic Điều Khiển ---
# Cooldown thời gian gửi lệnh (giây) để tránh gửi liên tục tọa độ khi vật thể lọt vào vạch
GLOBAL_COOLDOWN_SEC = 1.5

# FPS điều khiển luồng AI (Khoảng thời gian delay giữa các frame)
AI_LOOP_DELAY_SEC = 0.03
