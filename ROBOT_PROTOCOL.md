# Giao Thức Truyền Thông & Cấu Trúc Lệnh Điều Khiển Delta Robot

Tài liệu này khái quát toàn bộ giao thức truyền thông đang được sử dụng trong hệ thống **Delta Robot AI Vision**. Hệ thống giao tiếp với robot qua cổng nối tiếp (Serial/COM Port). Giao thức được thiết kế dưới dạng truyền chuỗi ký tự ASCII kết thúc bằng ký tự xuống dòng `\n`.

Giao thức được phân chia thành **2 chế độ chính**: **Điều khiển Thủ công (Manual Control)** và **Gửi Tọa độ Tự động (Automatic Crossing Event)**.

---

## 1. Giao Thức Điều Khiển Thủ Công (Manual Mode)

Khi người dùng nhập tọa độ $(X, Y, Z)$ trên giao diện và nhấn nút **Gửi Lệnh Chạy (Manual Control)**, hệ thống sẽ gửi một lệnh điều khiển theo phong cách G-code.

### Cú pháp tin nhắn
```text
G0 X{x} Y{y} Z{z}\n
```

### Chi tiết các tham số
*   `G0`: Lệnh di chuyển nhanh (không nội suy phức tạp).
*   `X{x}`: Tọa độ trục X thực tế của robot (kiểu số thực `float`, định dạng 1 chữ số thập phân, ví dụ: `X100.0`).
*   `Y{y}`: Tọa độ trục Y thực tế của robot (kiểu số thực `float`, định dạng 1 chữ số thập phân, ví dụ: `Y-50.0`).
*   `Z{z}`: Tọa độ trục Z thực tế của robot (kiểu số thực `float`, định dạng 1 chữ số thập phân, ví dụ: `Z220.0`).
*   `\n`: Ký tự kết thúc dòng (Line Feed) để thiết bị nhận biết kết thúc gói tin.

### Ví dụ chuỗi gửi đi
*   `G0 X100.0 Y-50.0 Z220.0\n`
*   `G0 X0.0 Y0.0 Z200.0\n`

### Vị trí code xử lý trong GUI
*   Lệnh này được định cấu hình và gửi đi tại hàm [serial_send_manual](file:///c:/Users/tdo35/Desktop/Codedoanchuyeng/Demo/src/ui/main_window.py#L116-L128) trong file `src/ui/main_window.py`.
```python
def serial_send_manual(self, x, y, z):
    cmd = f"G0 X{x:.1f} Y{y:.1f} Z{z:.1f}"
    # ...
    self.ser.write((cmd + "\n").encode())
```

---

## 2. Giao Thức Gửi Tọa Độ Tự Động (Auto Tracking Mode)

Khi mô hình AI phát hiện vật thể và vật thể đó đi qua vạch kích hoạt (**Trigger Line**), hệ thống tự động tính toán tọa độ gắp thực tế (thông qua ma trận hiệu chuẩn/calibration) và truyền thông tin đối tượng xuống robot.

Hiện tại trong dự án đang tồn tại **2 kiểu định dạng** khác nhau của giao thức này (một kiểu đang chạy trực tiếp trên giao diện và một kiểu được viết mẫu trong thư viện kết nối):

### Kiểu A: Giao thức thực tế đang chạy trên GUI (Khuyên dùng)
Giao thức này có chứa thêm ID định danh để quản lý vật thể, tránh gắp trùng lặp.

#### Cú pháp tin nhắn
```text
ID:{obj_id},NHAN:{cls_name},X:{rx},Y:{ry}\n
```

#### Chi tiết các tham số
*   `ID:{obj_id}`: ID của vật thể do luồng AI Tracking gán (kiểu số nguyên `int`, ví dụ: `ID:5`).
*   `NHAN:{cls_name}`: Tên nhãn lớp của vật thể do YOLO nhận diện (ví dụ: `NHAN:xoai`).
*   `X:{rx}`: Tọa độ X thực tế của điểm gắp sau hiệu chuẩn (kiểu số thực `float`, 1 chữ số thập phân).
*   `Y:{ry}`: Tọa độ Y thực tế của điểm gắp sau hiệu chuẩn (kiểu số thực `float`, 1 chữ số thập phân).

#### Ví dụ chuỗi gửi đi
*   `ID:12,NHAN:xoai,X:150.5,Y:85.2\n`

#### Vị trí code xử lý trong GUI
*   Xử lý tại hàm [update_gui](file:///c:/Users/tdo35/Desktop/Codedoanchuyeng/Demo/src/ui/main_window.py#L228-L238) trong file `src/ui/main_window.py` khi nhận sự kiện `target_crossed`:
```python
# Gửi tọa độ xuống Robot
cmd_to_send = f"ID:{obj_id},NHAN:{cls_name},X:{rx:.1f},Y:{ry:.1f}"
# ...
self.ser.write((cmd_to_send + "\n").encode())
```

---

### Kiểu B: Giao thức mẫu trong thư viện độc lập `communication.py`
Đây là hàm mẫu bổ trợ để test hoặc tích hợp riêng biệt, hiện tại chưa liên kết trực tiếp vào vòng lặp chính của GUI.

#### Cú pháp tin nhắn
```text
NHAN:{class_name},X:{x},Y:{y}\n
```
*(Không chứa trường dữ liệu `ID`, tọa độ `X` và `Y` được làm tròn thành số nguyên `int`)*

#### Ví dụ chuỗi gửi đi
*   `NHAN:xoai,X:150,Y:250\n`

#### Vị trí code xử lý
*   Định nghĩa tại hàm [send_coordinates_to_robot](file:///c:/Users/tdo35/Desktop/Codedoanchuyeng/Demo/src/robot/communication.py#L3-L15) trong file `src/robot/communication.py`.

---

## 3. Hướng Dẫn Cách Chỉnh Sửa Giao Thức Theo Từng Phần

Để sửa giao thức này dễ dàng, bạn có thể thực hiện theo các bước cụ thể dưới đây tùy theo nhu cầu:

### Phần 1: Thay đổi định dạng hoặc thêm bớt các thông số gửi đi (Ví dụ thêm tọa độ Z và Góc xoay Angle)
Nếu bạn muốn gửi thêm độ cao gắp $Z$ cố định (hoặc từ AI) hoặc góc xoay của vật thể $\theta$ để robot xoay giác hút/tay kẹp:

1.  Mở file [src/ui/main_window.py](file:///c:/Users/tdo35/Desktop/Codedoanchuyeng/Demo/src/ui/main_window.py).
2.  Tìm đến hàm `update_gui` (dòng 210-243), tại khối xử lý `elif data_type == "target_crossed":`.
3.  Thay đổi dòng tạo chuỗi tin nhắn `cmd_to_send`. Ví dụ, nếu muốn thêm Z và góc Angle:
    ```python
    # Giả sử cần thêm Z=50.0 và ANGLE=45.0
    cmd_to_send = f"ID:{obj_id},NHAN:{cls_name},X:{rx:.1f},Y:{ry:.1f},Z:50.0,ANG:45.0"
    ```

### Phần 2: Thay đổi ký tự phân cách hoặc ký tự kết thúc tin nhắn
Nếu phần cứng của bạn (Arduino, PLC) sử dụng ký tự phân cách khác (như khoảng trắng, dấu chấm phẩy `;`) hoặc ký tự kết thúc dòng khác (như `\r\n` - CRLF):

*   **Đổi ký tự phân cách**: Sửa trong chuỗi format `cmd_to_send`:
    ```python
    cmd_to_send = f"ID:{obj_id};NHAN:{cls_name};X:{rx:.1f};Y:{ry:.1f}"
    ```
*   **Đổi ký tự kết thúc tin nhắn**: Sửa tại lệnh ghi Serial `.write(...)`:
    ```python
    # Đổi từ \n sang \r\n
    self.ser.write((cmd_to_send + "\r\n").encode())
    ```

### Phần 3: Thêm cơ chế phản hồi (Handshake / Ack) từ Robot
Hiện tại luồng truyền thông chỉ gửi một chiều (GUI gửi xuống Robot mà không đợi Robot phản hồi đã nhận hay đã gắp xong). Để thêm cơ chế xác nhận:
1.  Sau khi gửi lệnh bằng `self.ser.write()`, bạn có thể thêm lệnh đọc phản hồi từ cổng Serial:
    ```python
    if self.ser and self.ser.is_open:
        try:
            self.ser.write((cmd_to_send + "\n").encode())
            
            # Đọc phản hồi (ví dụ Robot trả về chữ "OK\n")
            response = self.ser.readline().decode().strip()
            self.log_panel.log_robot(f"🤖 Phản hồi từ Robot: {response}")
            
            if response == "OK":
                self.statistics_panel.increment_sent()
            else:
                self.statistics_panel.increment_rejected()
        except Exception as e:
            self.log_panel.log_error(f"Lỗi truyền thông: {e}")
    ```
    *(Lưu ý: Đọc Serial đồng bộ `readline()` trực tiếp trên luồng chính GUI có thể gây đơ nhẹ giao diện nếu robot phản hồi quá chậm. Nên cân nhắc cấu hình `timeout` của cổng Serial nhỏ hơn hoặc xử lý đọc trên một luồng nhận riêng biệt).*
