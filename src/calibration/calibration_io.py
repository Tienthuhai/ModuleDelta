import json
import os
import numpy as np
from src.calibration.calibration_models import CalibrationPoint

class CalibrationIO:
    """
    Lớp quản lý lưu/nạp cấu hình hiệu chuẩn Robot dưới dạng JSON.
    """
    @staticmethod
    def save_robot_calibration(file_path: str, matrix: np.ndarray, points: list, method: str, rms: float) -> bool:
        """Lưu ma trận chuyển đổi và danh sách điểm robot ra file JSON."""
        try:
            # Chuyển đổi ma trận sang danh sách list
            matrix_list = matrix.tolist() if isinstance(matrix, np.ndarray) else matrix
            points_data = [pt.to_dict() for pt in points]
            
            data = {
                "matrix": matrix_list,
                "method": method,
                "rms": float(rms),
                "points": points_data
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu robot calibration: {e}")
            return False

    @staticmethod
    def load_robot_calibration(file_path: str) -> dict:
        """Nạp cấu hình hiệu chuẩn robot từ file JSON."""
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Khôi phục ma trận numpy
            if "matrix" in data and data["matrix"] is not None:
                data["matrix"] = np.array(data["matrix"], dtype=np.float64)
            
            # Khôi phục danh sách điểm
            if "points" in data:
                data["points"] = [CalibrationPoint.from_dict(pt) for pt in data["points"]]
                
            return data
        except Exception as e:
            print(f"Lỗi khi nạp robot calibration: {e}")
            return None
