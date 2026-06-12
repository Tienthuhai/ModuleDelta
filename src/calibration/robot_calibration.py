import numpy as np
from src.calibration.calibration_models import CalibrationPoint
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nvk_calibration import NVKCalibration

class RobotCalibration:
    """
    Thực hiện hiệu chuẩn tọa độ Pixel sang Robot (Eye-to-Hand 2D)
    bằng NVKCalibration (Weighted Least Squares Affine 2D).
    """
    def __init__(self):
        self.points = []      # Danh sách các đối tượng CalibrationPoint
        self.matrix = None    # Ma trận Affine 2x3 numpy
        self.method = "Affine"  # Luôn là Affine
        self.rms_error = 0.0
        self._nvk = None      # Đối tượng NVKCalibration sau khi tính toán

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

    def calculate_matrix(self, method: str = "Affine") -> tuple:
        """
        Tính toán ma trận Affine 2x3 bằng NVKCalibration (WLS).
        Trả về (success, matrix_2x3_numpy, rms_error)
        """
        self.method = "Affine"
        n_points = len(self.points)
        
        # Cần tối thiểu 3 điểm cho Affine 2D
        if n_points < 3:
            return False, None, 0.0

        # Trích xuất danh sách điểm
        uncalib = [(pt.px, pt.py) for pt in self.points]
        calib   = [(pt.rx, pt.ry) for pt in self.points]

        try:
            self._nvk = NVKCalibration(uncalib, calib)
            
            # Kiểm tra ma trận hợp lệ (không suy biến)
            if self._nvk.m00 == 0.0 and self._nvk.m11 == 0.0:
                return False, None, 0.0

            # Đóng gói thành ma trận Affine 2x3 numpy (tương thích với code hiện tại)
            M = np.array([
                [self._nvk.m00, self._nvk.m01, self._nvk.tr_x],
                [self._nvk.m10, self._nvk.m11, self._nvk.tr_y]
            ], dtype=np.float64)
            self.matrix = M

            # Lấy RMSE từ NVKCalibration
            params = self._nvk.get_affine_params()
            self.rms_error = params["rmse"]
            return True, self.matrix, self.rms_error

        except Exception as e:
            print(f"Lỗi tính toán ma trận Affine (NVK): {e}")
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
        """Biến đổi tọa độ Pixel sang tọa độ Robot bằng Affine 2D."""
        if self._nvk is not None:
            # Ưu tiên dùng NVKCalibration.transform() trực tiếp
            try:
                return self._nvk.transform((px_x, px_y))
            except Exception as e:
                print(f"Lỗi NVK transform: {e}")

        if self.matrix is None:
            return float(px_x), float(px_y)

        try:
            # Fallback: dùng ma trận Affine 2x3 trực tiếp
            M = self.matrix
            rx = M[0, 0] * px_x + M[0, 1] * px_y + M[0, 2]
            ry = M[1, 0] * px_x + M[1, 1] * px_y + M[1, 2]
            return float(rx), float(ry)
        except Exception as e:
            print(f"Lỗi khi thực hiện Affine transform: {e}")
            return float(px_x), float(px_y)
