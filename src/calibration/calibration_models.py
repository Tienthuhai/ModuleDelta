import numpy as np

class CalibrationPoint:
    """
    Lớp dữ liệu lưu trữ một cặp điểm hiệu chuẩn (Pixel ↔ Robot).
    """
    def __init__(self, px: float, py: float, rx: float, ry: float, index: int = 0):
        self.px = float(px)
        self.py = float(py)
        self.rx = float(rx)
        self.ry = float(ry)
        self.index = int(index)

    def to_dict(self):
        return {
            "px": self.px,
            "py": self.py,
            "rx": self.rx,
            "ry": self.ry,
            "index": self.index
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            px=data["px"],
            py=data["py"],
            rx=data["rx"],
            ry=data["ry"],
            index=data.get("index", 0)
        )

class CameraIntrinsic:
    """
    Lớp dữ liệu lưu trữ cấu hình nội của Camera (Matrix K và Distortion Coefficients D).
    """
    def __init__(self, camera_matrix: np.ndarray = None, dist_coeffs: np.ndarray = None, rms: float = 0.0):
        self.camera_matrix = camera_matrix if camera_matrix is not None else np.eye(3, dtype=np.float64)
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((1, 5), dtype=np.float64)
        self.rms = float(rms)

    def to_dict(self):
        return {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
            "rms": self.rms
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            camera_matrix=np.array(data["camera_matrix"], dtype=np.float64),
            dist_coeffs=np.array(data["dist_coeffs"], dtype=np.float64),
            rms=data.get("rms", 0.0)
        )
