import os
import io
import cv2
import numpy as np
import httpx
import logging
from PIL import Image, ImageOps
from paddleocr import PaddleOCR
from app.core.config import CAMERA_ROTATE_DEG, CAMERA_URL
from app.utils.logger import get_logger

os.environ['FLAGS_enable_pir_api'] = '0'
logging.getLogger('ppocr').setLevel(logging.ERROR)

logger = get_logger("lpr_service")

if CAMERA_ROTATE_DEG not in (0, 90, 180, 270):
    logger.warning("⚠️ CAMERA_ROTATE_DEG không hợp lệ, chỉ nhận 0/90/180/270. Sẽ dùng 0.")

# Khởi tạo PaddleOCR 1 lần duy nhất
try:
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)
except Exception:
    ocr = PaddleOCR(lang='en')


def _decode_image_preserve_orientation(raw_bytes: bytes) -> tuple[np.ndarray | None, bytes | None]:
    """
    Chuẩn hóa ảnh theo EXIF orientation (ảnh chụp điện thoại hay bị xoay 90 độ).
    Trả về:
    - img: numpy BGR để OCR
    - normalized_bytes: bytes JPEG đã chỉnh chiều để upload/lưu trùng với ảnh hiển thị
    """
    if not raw_bytes:
        return None, None

    try:
        with Image.open(io.BytesIO(raw_bytes)) as pil_img:
            pil_fixed = ImageOps.exif_transpose(pil_img).convert("RGB")
            rotate_deg = CAMERA_ROTATE_DEG if CAMERA_ROTATE_DEG in (90, 180, 270) else 0
            if rotate_deg:
                # PIL rotate ngược chiều kim đồng hồ, dùng dấu âm để xoay thuận chiều.
                pil_fixed = pil_fixed.rotate(-rotate_deg, expand=True)
            output = io.BytesIO()
            pil_fixed.save(output, format="JPEG", quality=95)
            normalized_bytes = output.getvalue()
    except Exception as e:
        logger.warning(f"⚠️ Không đọc EXIF orientation, dùng ảnh gốc: {e}")
        normalized_bytes = raw_bytes

    arr = np.frombuffer(normalized_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    return img, normalized_bytes


async def capture_image_from_camera() -> tuple[np.ndarray | None, bytes | None]:
    """Gọi HTTP GET đến camera (điện thoại) để chụp ảnh."""
    try:
        logger.info(f"📸 Đang gọi Camera: {CAMERA_URL}...")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(CAMERA_URL)
            if response.status_code == 200:
                raw_bytes = response.content
                img, normalized_bytes = _decode_image_preserve_orientation(raw_bytes)
                return img, normalized_bytes
    except Exception as e:
        logger.error(f"⚠️ Không kết nối được Camera: {e}")
    return None, None


def load_image_from_path(file_path: str) -> tuple[np.ndarray | None, bytes | None]:
    """Đọc ảnh từ đường dẫn local."""
    if not os.path.isfile(file_path):
        logger.error(f"❌ Không tìm thấy file: {file_path}")
        return None, None

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    img, normalized_bytes = _decode_image_preserve_orientation(raw_bytes)
    if img is None:
        logger.error(f"❌ Không thể đọc ảnh: {file_path}")
        return None, None
    return img, normalized_bytes


def recognize_plate(img: np.ndarray) -> str:
    """Chạy OCR và ưu tiên cụm ký tự gần trung tâm ảnh."""
    result = ocr.ocr(img)

    if not result or not result[0]:
        logger.info("🔍 Kết quả nhận diện: UNKNOWN")
        return "UNKNOWN"

    h, w = img.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    central_box_w = w * 0.6
    central_box_h = h * 0.6
    x_min = cx - central_box_w / 2.0
    x_max = cx + central_box_w / 2.0
    y_min = cy - central_box_h / 2.0
    y_max = cy + central_box_h / 2.0

    candidates: list[dict] = []
    for line in result[0]:
        points = line[0]
        text = line[1][0]
        confidence = line[1][1]
        if confidence <= 0.5:
            continue

        clean_text = "".join(c for c in text if c.isalnum()).upper()
        if not clean_text:
            continue

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bx = sum(xs) / len(xs)
        by = sum(ys) / len(ys)

        in_center = x_min <= bx <= x_max and y_min <= by <= y_max
        if not in_center:
            continue

        candidates.append(
            {
                "text": clean_text,
                "confidence": confidence,
                "x": bx,
                "y": by,
                "w": max(xs) - min(xs),
            }
        )

    if not candidates:
        plate = "UNKNOWN"
        logger.info(f"🔍 Kết quả nhận diện: {plate}")
        return plate

    # Chọn anchor gần tâm nhất, rồi chỉ ghép các box OCR nằm gần anchor đó.
    anchor = min(candidates, key=lambda c: (c["x"] - cx) ** 2 + (c["y"] - cy) ** 2)
    max_gap_x = max(anchor["w"] * 1.8, w * 0.15)
    max_gap_y = h * 0.10

    cluster = [
        c for c in candidates
        if abs(c["x"] - anchor["x"]) <= max_gap_x and abs(c["y"] - anchor["y"]) <= max_gap_y
    ]
    cluster.sort(key=lambda c: (c["y"], c["x"]))

    plate = "".join(c["text"] for c in cluster).upper()
    if not plate:
        plate = "UNKNOWN"

    logger.info(f"🔍 Kết quả nhận diện: {plate}")
    return plate
