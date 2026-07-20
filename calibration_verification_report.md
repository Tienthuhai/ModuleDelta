# Kiểm Chứng Kết Quả Hiệu Chuẩn (Calibration Verification)

## 1. Tổng Quan

Sau khi tính toán thành công ma trận biến đổi Affine 2D từ tập hợp các cặp điểm hiệu chuẩn, hệ thống cung cấp module **Kiểm Chứng (Verification)** nhằm đánh giá độ chính xác và tính đúng đắn của ma trận đã tính. Người dùng nhập một tọa độ pixel bất kỳ từ camera vào giao diện, hệ thống sẽ:

1. Ánh xạ tọa độ pixel sang tọa độ robot dự đoán thông qua ma trận Affine đã hiệu chuẩn.
2. Tìm điểm hiệu chuẩn gần nhất trong tập dữ liệu để làm điểm tham chiếu.
3. Tính sai số Euclidean giữa tọa độ robot dự đoán và tọa độ robot thực tế (đã biết).

---

## 2. Cơ Sở Lý Thuyết

### 2.1 Phép Biến Đổi Affine 2D (Forward Transform)

Ma trận Affine 2D được biểu diễn dưới dạng ma trận $\mathbf{M}$ kích thước $2 \times 3$:

$$\mathbf{M} = \begin{bmatrix} m_{00} & m_{01} & t_x \\ m_{10} & m_{11} & t_y \end{bmatrix}$$

Phép ánh xạ từ tọa độ pixel $(p_x,\, p_y)$ sang tọa độ robot $(r_x,\, r_y)$ được thực hiện theo công thức:

$$\begin{cases} r_x = m_{00} \cdot p_x + m_{01} \cdot p_y + t_x \\ r_y = m_{10} \cdot p_x + m_{11} \cdot p_y + t_y \end{cases}$$

### 2.2 Tính Sai Số Kiểm Chứng (Verification Error)

Để đánh giá sai số tại một điểm kiểm chứng cụ thể, hệ thống tìm điểm tham chiếu $k$ trong tập dữ liệu hiệu chuẩn thỏa mãn khoảng cách pixel nhỏ nhất:

$$k = \arg\min_{i} \sqrt{(p_x - p_{x_i})^2 + (p_y - p_{y_i})^2}$$

Điều kiện để điểm tham chiếu hợp lệ: khoảng cách pixel $d_{\text{pixel}} < 30\,\text{px}$.

Sai số kiểm chứng tại điểm $k$ được tính bằng khoảng cách Euclidean trong không gian tọa độ robot (đơn vị mm):

$$e_k = \sqrt{(r_{x_k} - \hat{r}_x)^2 + (r_{y_k} - \hat{r}_y)^2}$$

Trong đó:
- $(r_{x_k},\, r_{y_k})$: Tọa độ robot thực tế đã biết của điểm tham chiếu $k$.
- $(\hat{r}_x,\, \hat{r}_y)$: Tọa độ robot dự đoán từ ma trận Affine.

### 2.3 Sai Số Toàn Cục RMSE (Root Mean Square Error)

Chỉ số RMSE được tính toán sau mỗi lần hiệu chuẩn và phản ánh độ chính xác tổng thể của mô hình trên toàn bộ $n$ điểm hiệu chuẩn:

$$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} \left[(r_{x_i} - \hat{r}_{x_i})^2 + (r_{y_i} - \hat{r}_{y_i})^2\right]}$$

---

## 3. Luồng Xử Lý

```
Người dùng nhập (Pixel X, Pixel Y)
           │
           ▼
  Áp dụng ma trận Affine M
  → Tính (Robot X̂, Robot Ŷ) dự đoán
           │
           ▼
  Hiển thị kết quả dự đoán lên giao diện
           │
           ▼
  Tìm điểm tham chiếu gần nhất trong tập dữ liệu
  (khoảng cách pixel < 30 px)
           │
      ┌────┴────┐
  Có tham chiếu       Không có tham chiếu
      │                      │
      ▼                      ▼
  Tính sai số e_k     Hiển thị "Không có điểm tham chiếu"
  Hiển thị lên UI
```

---

## 4. Triển Khai Phần Mềm

Module Verification được triển khai trong lớp `CalibrationPanel` thuộc file `src/calibration/calibration_panel.py`. Phương thức chính thực hiện kiểm chứng là `verify_manual_point()`:

```python
def verify_manual_point(self):
    """Tính toán kiểm chứng từ tọa độ Pixel nhập tay."""
    px = float(self.entry_verify_px.get())
    py = float(self.entry_verify_py.get())

    # Bước 1: Ánh xạ Pixel → Robot bằng ma trận Affine
    rx, ry = self.transform(px, py)

    # Bước 2: Tìm điểm tham chiếu gần nhất (trong phạm vi 30 px)
    min_dist = float('inf')
    nearest_pt = None
    for pt in self.robot_calib.points:
        dist = np.sqrt((pt.px - px)**2 + (pt.py - py)**2)
        if dist < min_dist:
            min_dist = dist
            nearest_pt = pt

    # Bước 3: Tính và hiển thị sai số kiểm chứng
    if nearest_pt and min_dist < 30:
        error = np.sqrt((nearest_pt.rx - rx)**2 + (nearest_pt.ry - ry)**2)
```

Phép biến đổi Affine 2D được thực hiện thông qua lớp `NVKCalibration` trong `nvk_calibration.py`:

```python
def transform(self, point):
    """Ánh xạ tiến: Pixel Camera → Tọa độ Robot."""
    x, y = point
    x_pred = self.m00 * x + self.m01 * y + self.tr_x
    y_pred = self.m10 * x + self.m11 * y + self.tr_y
    return (x_pred, y_pred)
```

---

## 5. Giao Diện Người Dùng

Phần Verification được bố cục trong khung `verify_frame` của giao diện hiệu chuẩn, bao gồm các thành phần:

| Thành phần | Mô tả |
|:--|:--|
| **Entry "Pixel X verify"** | Ô nhập tọa độ pixel X cần kiểm chứng |
| **Entry "Pixel Y verify"** | Ô nhập tọa độ pixel Y cần kiểm chứng |
| **Nút "🔍 Verify Point"** | Kích hoạt tính toán kiểm chứng |
| **Nhãn kết quả** | Hiển thị tọa độ robot dự đoán $(r_x, r_y)$ |
| **Nhãn sai số** | Hiển thị chỉ số điểm tham chiếu và sai số $e_k$ (mm) |

---

## 6. Điều Kiện Sử Dụng

> **Lưu ý:** Chức năng Verification chỉ hoạt động chính xác khi:
> 1. Đã nhập **tối thiểu 3 cặp điểm** hiệu chuẩn.
> 2. Đã bấm nút **"📊 Calculate Matrix"** để tính toán ma trận Affine thành công.
> 3. Giá trị RMSE sau hiệu chuẩn đạt yêu cầu độ chính xác (khuyến nghị RMSE < 2 mm).

---

## 7. Ý Nghĩa Kết Quả

| Giá trị sai số $e_k$ | Đánh giá |
|:--|:--|
| $e_k < 1\,\text{mm}$ | ✅ Xuất sắc — Hệ thống đạt độ chính xác cao |
| $1\,\text{mm} \leq e_k < 3\,\text{mm}$ | ✅ Tốt — Đáp ứng yêu cầu hầu hết ứng dụng công nghiệp |
| $3\,\text{mm} \leq e_k < 5\,\text{mm}$ | ⚠️ Chấp nhận được — Cân nhắc thêm điểm hiệu chuẩn |
| $e_k \geq 5\,\text{mm}$ | ❌ Cần hiệu chuẩn lại — Kiểm tra chất lượng dữ liệu đầu vào |
