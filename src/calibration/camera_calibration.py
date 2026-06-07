import cv2
import numpy as np
import os
from src.calibration.calibration_models import CameraIntrinsic

class CameraCalibration:
    """
    Thực hiện hiệu chuẩn Camera sử dụng bàn cờ Chessboard bằng OpenCV thực.
    """
    def __init__(self, board_width: int = 9, board_height: int = 6, square_size: float = 25.0):
        self.board_size = (int(board_width), int(board_height))
        self.square_size = float(square_size)
        self.intrinsic = CameraIntrinsic()
        
    def set_board_parameters(self, width: int, height: int, square_size: float):
        self.board_size = (int(width), int(height))
        self.square_size = float(square_size)

    def calibrate_from_images(self, image_paths: list) -> tuple:
        """
        Thực hiện tìm góc bàn cờ và tính toán thông số nội Camera từ danh sách ảnh.
        Trả về (success, camera_intrinsic, valid_count, rms_error)
        """
        # Tạo tọa độ 3D thực tế của các góc bàn cờ (X, Y, Z=0)
        objp = np.zeros((self.board_size[0] * self.board_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.board_size[0], 0:self.board_size[1]].T.reshape(-1, 2)
        objp *= self.square_size

        objpoints = [] # Điểm thực tế 3D
        imgpoints = [] # Điểm ảnh 2D

        valid_count = 0
        gray_shape = None

        for path in image_paths:
            if not os.path.exists(path):
                continue
            
            img = cv2.imread(path)
            if img is None:
                continue
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray_shape = gray.shape[::-1]

            # Tìm góc bàn cờ
            ret, corners = cv2.findChessboardCorners(gray, self.sidebar_check_size_board() if hasattr(self, 'sidebar_check_size_board') else self.board_size, None)

            if ret:
                objpoints.append(objp)
                # Tinh chỉnh tọa độ góc cờ đạt độ chính xác pixel phụ
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners2)
                valid_count += 1

        if valid_count < 3:
            return False, self.intrinsic, valid_count, 0.0

        # Chạy hiệu chuẩn Camera
        try:
            ret_rms, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray_shape, None, None
            )
            self.intrinsic = CameraIntrinsic(camera_matrix=mtx, dist_coeffs=dist, rms=ret_rms)
            return True, self.intrinsic, valid_count, ret_rms
        except Exception as e:
            print(f"Lỗi trong quá trình calibrateCamera: {e}")
            return False, self.intrinsic, valid_count, 0.0

    def undistort(self, img: np.ndarray) -> np.ndarray:
        """Khử méo ảnh sử dụng ma trận camera nội tại hiện tại."""
        if self.intrinsic.camera_matrix is None or self.intrinsic.dist_coeffs is None:
            return img
        
        h, w = img.shape[:2]
        # Tính toán ma trận camera tối ưu mới dựa trên hệ số méo
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            self.intrinsic.camera_matrix, self.intrinsic.dist_coeffs, (w, h), 1, (w, h)
        )
        # Khử méo ảnh
        dst = cv2.undistort(img, self.intrinsic.camera_matrix, self.intrinsic.dist_coeffs, None, newcameramtx)
        
        # Crop ảnh theo ROI nếu cần (ở đây ta giữ nguyên kích thước để không làm lệch tọa độ)
        return dst
