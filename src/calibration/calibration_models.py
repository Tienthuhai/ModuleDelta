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
