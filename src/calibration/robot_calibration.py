import cv2
import numpy as np
from src.calibration.calibration_models import CalibrationPoint

class RobotCalibration:
    """
    Thực hiện hiệu chuẩn tọa độ Pixel sang Robot (Eye-to-Hand 2D) bằng OpenCV thực.
    Hỗ trợ Homography (3x3) và Affine (2x3).
    """
    def __init__(self):
        self.points = [] # Danh sách các đối tượng CalibrationPoint
        self.matrix = None # Lưu ma trận Numpy hiện tại
        self.method = "Homography" # "Homography" hoặc "Affine"
        self.rms_error = 0.0

    def add_point(self, px: float, py: float, rx: float, ry: float) -> CalibrationPoint:
        """Thêm một cặp điểm hiệu chuẩn mới."""
        index = len(self.points) + 1
        pt = CalibrationPoint(px, py, rx, ry, index)
        self.points.append(pt)
        return pt

    def update_point(self, index: int, px: float, py: float, rx: float, ry: float) -> bool:
        """Cập nhật thông tin của điểm tại index (1-indexed)."""
        for pt in self.points:
            if pt.index == index:
                pt.px = float(px)
                pt.py = float(py)
                pt.rx = float(rx)
                pt.ry = float(ry)
                return True
        return False

    def delete_point(self, index: int) -> bool:
        """Xóa điểm tại index và cập nhật lại số thứ tự."""
        initial_len = len(self.points)
        self.points = [pt for pt in self.points if pt.index != index]
        # Sắp xếp lại thứ tự index
        for i, pt in enumerate(self.points):
            pt.index = i + 1
        return len(self.points) < initial_len

    def clear_all(self):
        """Xóa trắng toàn bộ danh sách điểm."""
        self.points.clear()
        self.matrix = None
        self.rms_error = 0.0

    def calculate_matrix(self, method: str = "Homography") -> tuple:
        """
        Tính toán ma trận chuyển đổi từ hệ điểm hiện có.
        Trả về (success, matrix, rms_error)
        """
        self.method = method
        n_points = len(self.points)
        
        # Kiểm tra điều kiện tối thiểu
        min_required = 4 if method == "Homography" else 3
        if n_points < min_required:
            return False, None, 0.0

        # Trích xuất mảng numpy cho Pixel và Robot
        src_pts = np.array([[pt.px, pt.py] for pt in self.points], dtype=np.float32)
        dst_pts = np.array([[pt.rx, pt.ry] for pt in self.points], dtype=np.float32)

        try:
            if method == "Homography":
                # Tính ma trận Homography (3x3)
                H, status = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if H is None:
                    return False, None, 0.0
                self.matrix = H
            else:
                # Tính ma trận Affine (2x3)
                M, status = cv2.estimateAffine2D(src_pts, dst_pts)
                if M is None:
                    return False, None, 0.0
                self.matrix = M

            # Tính toán sai số RMS (Root Mean Square Error)
            self.rms_error = self.calculate_rms_error()
            return True, self.matrix, self.rms_error

        except Exception as e:
            print(f"Lỗi tính toán ma trận ({method}): {e}")
            return False, None, 0.0

    def calculate_rms_error(self) -> float:
        """Tính sai số RMS thực tế dựa trên khoảng cách Euclidean."""
        if self.matrix is None or len(self.points) == 0:
            return 0.0

        sum_sq_dist = 0.0
        for pt in self.points:
            rx_pred, ry_pred = self.transform(pt.px, pt.py)
            dist_sq = (pt.rx - rx_pred)**2 + (pt.ry - ry_pred)**2
            sum_sq_dist += dist_sq
            
        return float(np.sqrt(sum_sq_dist / len(self.points)))

    def transform(self, px_x: float, px_y: float) -> tuple:
        """Biến đổi tọa độ Pixel sang tọa độ Robot."""
        if self.matrix is None:
            # Nếu chưa có ma trận, trả về tỉ lệ 1:1
            return float(px_x), float(px_y)

        try:
            if self.method == "Homography":
                # Phép chiếu phối cảnh 3x3
                H = self.matrix
                w = H[2, 0] * px_x + H[2, 1] * px_y + H[2, 2]
                w = w if w != 0 else 1.0
                rx = (H[0, 0] * px_x + H[0, 1] * px_y + H[0, 2]) / w
                ry = (H[1, 0] * px_x + H[1, 1] * px_y + H[1, 2]) / w
                return float(rx), float(ry)
            else:
                # Phép biến đổi Affine 2x3
                M = self.matrix
                rx = M[0, 0] * px_x + M[0, 1] * px_y + M[0, 2]
                ry = M[1, 0] * px_x + M[1, 1] * px_y + M[1, 2]
                return float(rx), float(ry)
        except Exception as e:
            print(f"Lỗi khi thực hiện transform: {e}")
            return float(px_x), float(px_y)
