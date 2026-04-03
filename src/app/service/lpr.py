import os

# Tat OneDNN/MKLDNN truoc khi import paddle
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import cv2
import numpy as np
from paddleocr import PaddleOCR
import logging

logging.getLogger('ppocr').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


class LPRService:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=False,
            show_log=False,
            enable_mkldnn=False,
        )

    async def recognize_plate(self, image_bytes: bytes) -> str:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                logger.error("Không thể giải mã hình ảnh từ bytes")
                return "Lỗi: Không thể đọc được ảnh"

            logger.info("Bắt đầu xử lý nhận diện biển số...")
            
            # 1. Tìm khung biển số bằng phương pháp Contour (OpenCV)
            # Resize để chuẩn hóa kích thước xử lý
            h_orig, w_orig = img.shape[:2]
            scale = 800 / w_orig
            img_resized = cv2.resize(img, (800, int(h_orig * scale)))
            
            grayscale = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grayscale, (5, 5), 0)
            edged = cv2.Canny(blurred, 30, 200)

            contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # Sắp xếp theo diện tích giảm dần và lấy tối đa 10 contour đầu tiên
            sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
            contours = []
            for i in range(min(10, len(sorted_contours))):
                contours.append(sorted_contours[i])

            number_plate_crop = None
            for c in contours:
                perimeter = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * perimeter, True)
                if len(approx) == 4:
                    (x, y, w, h) = cv2.boundingRect(approx)
                    # Kiểm tra tỷ lệ khung hình (biển số thường có w > h)
                    aspect_ratio = w / float(h)
                    if 2.0 < aspect_ratio < 6.0:
                        padding = 10
                        ny = max(0, y - padding)
                        nx = max(0, x - padding)
                        number_plate_crop = img_resized[ny : y + h + padding, nx : x + w + padding]
                        logger.info(f"Đã tìm thấy vùng nghi vấn biển số qua Contour (x={x}, y={y}, w={w}, h={h})")
                        break

            # 2. Chạy OCR
            # Thử với vùng crop trước, nếu không được thì thử toàn bộ ảnh
            result = None
            if number_plate_crop is not None:
                result = self.ocr.ocr(number_plate_crop, cls=True)
                
            # Nếu không tìm thấy chữ trong vùng crop, thử với toàn bộ ảnh (để PaddleOCR tự detect)
            if not result or not result[0]:
                logger.info("Không tìm thấy chữ trong vùng crop hoặc không có vùng crop, thử nhận diện toàn bộ ảnh...")
                result = self.ocr.ocr(img, cls=True)

            if not result or not result[0]:
                logger.warning("Không tìm thấy bất kỳ ký tự nào trong ảnh")
                return "Không nhận diện được"

            # 3. Phân tích kết quả
            detected_texts = []
            ocr_result = result[0]
            if ocr_result:
                max_height = 0
                valid_lines = []
                
                # B1: Trích xuất tất cả các dòng chữ và tính kích thước
                for line in ocr_result:
                    if line and len(line) > 1:
                        box = line[0]
                        text_info = line[1]
                        if text_info and len(text_info) > 0:
                            text = text_info[0]
                            confidence = float(text_info[1])
                            
                            if confidence > 0.5: # Lọc độ tin cậy
                                # Tính chiều cao của bounding box
                                y_coords = [float(point[1]) for point in box]
                                height = max(y_coords) - min(y_coords)
                                max_height = max(max_height, height)
                                
                                valid_lines.append({
                                    'text': str(text),
                                    'height': height,
                                    'y_min': min(y_coords)
                                })
                
                # B2: Lọc bỏ các chữ phụ (tên xe) dựa vào tỉ lệ chiều cao
                # Biển số thường là chữ to nhất, nên ta chỉ lấy những dòng >= 60% max_height
                if float(max_height) > 0:
                    filtered_lines = [line for line in valid_lines if float(line['height']) >= float(max_height) * 0.6]
                    
                    # Sắp xếp các dòng chữ từ trên xuống dưới theo tọa độ y
                    filtered_lines = sorted(filtered_lines, key=lambda x: float(x['y_min']))
                    
                    for line in filtered_lines:
                        detected_texts.append(line['text'])

            if not detected_texts:
                return "Không tìm thấy nội dung biển số"

            # Làm sạch chuỗi: chỉ giữ ký tự chữ và số
            full_text = "".join(detected_texts).upper()
            clean_text = "".join(e for e in full_text if e.isalnum())
            
            logger.info(f"Kết quả nhận diện: {clean_text}")
            return clean_text

        except Exception as e:
            logger.error(f"LPR Error: {str(e)}")
            return f"Lỗi hệ thống: {str(e)}"


# Singleton instance
lpr_service = LPRService()
