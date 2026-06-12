import numpy as np

class NVKCalibration:
    def __init__(self, uncalib_points=None, calib_points=None, weights=None):
        """
        Khởi tạo và tính toán ma trận hiệu chuẩn Affine 2D.
        
        uncalib_points: Danh sách các điểm chưa hiệu chuẩn (ví dụ: pixel camera), định dạng [(x1, y1), (x2, y2), ...]
        calib_points: Danh sách các điểm đã hiệu chuẩn tương ứng (ví dụ: tọa độ robot), định dạng [(x1', y1'), (x2', y2'), ...]
        weights: Danh sách trọng số cho mỗi cặp điểm. Nếu None, mặc định là 1.0 cho tất cả các điểm.
        """
        # Ma trận biến đổi đồng nhất 3x3:
        # | m00  m01  tr_x |
        # | m10  m11  tr_y |
        # |  0    0    1   |
        self.m00 = 0.0
        self.m01 = 0.0
        self.tr_x = 0.0
        
        self.m10 = 0.0
        self.m11 = 0.0
        self.tr_y = 0.0
        
        self.rms = 0.0
        
        self.uncalib_points = []
        self.calib_points = []
        
        if uncalib_points is not None and calib_points is not None:
            self.uncalib_points = [np.array([p[0], p[1]], dtype=float) for p in uncalib_points]
            self.calib_points = [np.array([p[0], p[1]], dtype=float) for p in calib_points]
            
            if len(self.uncalib_points) != len(self.calib_points):
                raise ValueError("Danh sách điểm gốc và điểm đích phải có cùng độ dài!")
            if len(self.uncalib_points) < 3:
                raise ValueError("Cần tối thiểu 3 cặp điểm để thực hiện hiệu chuẩn Affine 2D!")
            
            # Xử lý trọng số (Weights)
            n = len(self.uncalib_points)
            if weights is None:
                weights = [1.0] * n
            elif len(weights) < n:
                # Bù trọng số 1.0 cho các điểm thiếu
                weights = list(weights) + [1.0] * (n - len(weights))
            
            # Tính toán ma trận hiệu chuẩn
            self.compute_affine_homogeneous(weights)

    def compute_affine_homogeneous(self, weights):
        """
        Thuật toán Hồi quy bình phương tối tiểu có trọng số (Weighted Least Squares Regression)
        Giải hệ phương trình: theta = (A^T * W^-1 * A)^-1 * A^T * W^-1 * B
        """
        n = len(self.uncalib_points)
        A = np.zeros((n, 3))
        B = np.zeros((n, 2))
        W = np.eye(n)
        
        for i in range(n):
            A[i, 0] = self.uncalib_points[i][0]
            A[i, 1] = self.uncalib_points[i][1]
            A[i, 2] = 1.0
            
            B[i, 0] = self.calib_points[i][0]
            B[i, 1] = self.calib_points[i][1]
            
            W[i, i] = weights[i]
            
        # Nghịch đảo ma trận trọng số
        W_inv = np.linalg.inv(W)
        
        # Tính toán vế trái: A^T * W^-1 * A
        lhs = A.T @ W_inv @ A
        
        # Kiểm tra tính khả nghịch của ma trận
        if np.abs(np.linalg.det(lhs)) < 1e-9:
            # Nếu ma trận suy biến, trả về các hệ số bằng 0
            self.m00 = self.m01 = self.tr_x = 0.0
            self.m10 = self.m11 = self.tr_y = 0.0
            return
            
        # Giải hệ tìm ma trận theta (kích thước 3x2)
        theta = np.linalg.inv(lhs) @ A.T @ W_inv @ B
        
        # Chuyển vị theta sang 2x3 để dễ trích xuất hệ số tương ứng C#
        theta_T = theta.T
        
        # Hàng 1: a, b, tx
        self.m00 = theta_T[0, 0]
        self.m01 = theta_T[0, 1]
        self.tr_x = theta_T[0, 2]
        
        # Hàng 2: c, d, ty
        self.m10 = theta_T[1, 0]
        self.m11 = theta_T[1, 1]
        self.tr_y = theta_T[1, 2]

    def set_parameter(self, m00, m01, m10, m11, tr_x, tr_y):
        """Cho phép gán trực tiếp các tham số ma trận đã biết trước đó."""
        self.m00 = m00
        self.m01 = m01
        self.m10 = m10
        self.m11 = m11
        self.tr_x = tr_x
        self.tr_y = tr_y

    def get_affine_params(self):
        """
        Phân rã ma trận hiệu chuẩn thành các tham số hình học vật lý thực tế.
        """
        a, b, tx = self.m00, self.m01, self.tr_x
        c, d, ty = self.m10, self.m11, self.tr_y
        
        # Tính toán tỉ lệ co giãn (Scale factors)
        scale_x = np.sqrt(a**2 + c**2)
        scale_y = np.sqrt(b**2 + d**2)
        scale = (scale_x + scale_y) / 2.0
        
        # Tính toán góc xoay (Rotation) bằng Độ (Degrees)
        rotation_rad = np.arctan2(c, a)
        rotation_deg = np.degrees(rotation_rad)
        
        # Tỷ lệ trục (Ratio)
        ratio = scale_y / scale_x if scale_x != 0 else 0.0
        
        # Góc xiên (Skew Angle) thể hiện sai lệch góc vuông của hệ trục
        skew_rad = np.arctan2(a*b + c*d, scale_x**2) if scale_x != 0 else 0.0
        skew_deg = np.degrees(skew_rad)
        
        # Tính toán sai số RMSE (Root Mean Square Error)
        sum_sq_error = 0.0
        n = len(self.uncalib_points)
        for i in range(n):
            ux, uy = self.uncalib_points[i]
            cx, cy = self.calib_points[i]
            
            # Dự đoán tọa độ sau hiệu chuẩn
            x_pred = a * ux + b * uy + tx
            y_pred = c * ux + d * uy + ty
            
            dx = x_pred - cx
            dy = y_pred - cy
            sum_sq_error += dx**2 + dy**2
            
        rmse = np.sqrt(sum_sq_error / n) if n > 0 else 0.0
        self.rms = rmse
        
        return {
            'translation_x': tx,
            'translation_y': ty,
            'scale_x': scale_x,
            'scale_y': scale_y,
            'scale': scale,
            'rotation_deg': rotation_deg,
            'ratio': ratio,
            'skew_deg': skew_deg,
            'rmse': rmse
        }

    def transform(self, point):
        """
        Ánh xạ tiến (Forward Transform): Chuyển điểm (x, y) từ hệ tọa độ gốc sang hệ tọa độ đích.
        Ví dụ: Từ pixel tọa độ ảnh (Camera) -> Tọa độ thực tế (Robot)
        """
        x, y = point
        x_pred = self.m00 * x + self.m01 * y + self.tr_x
        y_pred = self.m10 * x + self.m11 * y + self.tr_y
        return (x_pred, y_pred)
        
    def inverse(self, point):
        """
        Ánh xạ ngược (Inverse Transform): Chuyển điểm (x', y') từ hệ tọa độ đích về hệ tọa độ gốc.
        Ví dụ: Từ tọa độ thực tế (Robot) -> Tọa độ màn hình (Camera/Pixel)
        """
        det = self.m00 * self.m11 - self.m10 * self.m01
        if np.abs(det) < 1e-9:
            raise ValueError("Ma trận suy biến, không thể thực hiện ánh xạ ngược!")
            
        # Ma trận nghịch đảo
        ia = self.m11 / det
        ib = -self.m01 / det
        ic = -self.m10 / det
        id = self.m00 / det
        
        # Phần tịnh tiến nghịch đảo
        tx_inv = (self.m01 * self.tr_y - self.m11 * self.tr_x) / det
        ty_inv = (self.m10 * self.tr_x - self.m00 * self.tr_y) / det
        
        x_prime, y_prime = point
        x_orig = ia * x_prime + ib * y_prime + tx_inv
        y_orig = ic * x_prime + id * y_prime + ty_inv
        return (x_orig, y_orig)

    def map_angle_deg(self, angle_deg):
        """Ánh xạ một góc xoay (độ) từ hệ tọa độ gốc sang hệ tọa độ đích."""
        angle_rad = np.radians(angle_deg)
        mapped_rad = self.map_angle_rad(angle_rad)
        return np.degrees(mapped_rad)

    def map_angle_rad(self, angle_rad):
        """Ánh xạ một góc xoay (radian) từ hệ tọa độ gốc sang hệ tọa độ đích."""
        vx = np.cos(angle_rad)
        vy = np.sin(angle_rad)
        
        vx2 = self.m00 * vx + self.m01 * vy
        vy2 = self.m10 * vx + self.m11 * vy
        
        return np.arctan2(vy2, vx2)


# ==========================================
# HƯỚNG DẪN SỬ DỤNG VÀ CHẠY THỬ (DEMO):
# ==========================================
if __name__ == "__main__":
    # Giả lập dữ liệu hiệu chuẩn gồm 5 điểm mẫu
    # uncalib: tọa độ Pixel trên camera (x, y)
    # calib: tọa độ thực tế robot tương ứng (x', y')
    uncalib = [
        (100, 150),
        (200, 160),
        (150, 250),
        (300, 300),
        (250, 100)
    ]
    
    calib = [
        (12.3, 24.5),
        (32.1, 26.1),
        (22.0, 44.2),
        (51.8, 53.9),
        (42.5, 14.8)
    ]
    
    # 1. Khởi tạo đối tượng hiệu chuẩn
    calibrator = NVKCalibration(uncalib, calib)
    
    # 2. Lấy các thông số hình học sau khi tính toán
    params = calibrator.get_affine_params()
    print("--- THÔNG SỐ HIỆU CHUẨN ---")
    print(f"Dịch chuyển X (Tx): {params['translation_x']:.4f}")
    print(f"Dịch chuyển Y (Ty): {params['translation_y']:.4f}")
    print(f"Tỷ lệ co giãn (Scale): {params['scale']:.4f} (Sx: {params['scale_x']:.4f}, Sy: {params['scale_y']:.4f})")
    print(f"Góc xoay lệch (Rotation): {params['rotation_deg']:.4f} độ")
    print(f"Sai số RMS hiệu chuẩn (RMSE): {params['rmse']:.6f}")
    
    # 3. Thử nghiệm ánh xạ thuận (Pixel camera -> Tọa độ robot)
    test_pixel = (180, 200)
    robot_coord = calibrator.transform(test_pixel)
    print("\n--- TEST ÁNH XẠ THUẬN ---")
    print(f"Pixel Camera: {test_pixel} ===> Tọa độ Robot: ({robot_coord[0]:.3f}, {robot_coord[1]:.3f})")
    
    # 4. Thử nghiệm ánh xạ nghịch (Tọa độ robot -> Pixel camera)
    back_to_pixel = calibrator.inverse(robot_coord)
    print("\n--- TEST ÁNH XẠ NGHỊCH ---")
    print(f"Tọa độ Robot: ({robot_coord[0]:.3f}, {robot_coord[1]:.3f}) ===> Trở lại Pixel: ({back_to_pixel[0]:.1f}, {back_to_pixel[1]:.1f})")
    
    # 5. Thử nghiệm biến đổi góc xoay
    cam_angle = 30.0 # camera thấy vật xoay 30 độ
    robot_angle = calibrator.map_angle_deg(cam_angle)
    print("\n--- TEST BIẾN ĐỔI GÓC ---")
    print(f"Vật xoay trong Camera: {cam_angle} độ ===> Robot cần xoay góc: {robot_angle:.3f} độ")
