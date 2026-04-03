import os
import time
import logging
import requests

logger = logging.getLogger("camera")

IP_CAMERA = os.getenv("IP_CAMERA")
URL_FOCUS = f"http://{IP_CAMERA}:8080/focus"
URL_SHOT = f"http://{IP_CAMERA}:8080/shot.jpg"


async def capture_image_from_camera(gate: str) -> tuple[bytes, str, str]:
    """
    Chụp ảnh từ camera IP.
    Bước 1: Gọi /focus để lấy nét.
    Bước 2: Gọi /shot.jpg để lấy ảnh.

    Args:
        gate: "GATE_IN" hoặc "GATE_OUT"

    Returns:
        Tuple (image_bytes, filename, content_type)
    """
    logger.info(f"📸 [{gate}] Bắt đầu quy trình chụp ảnh...")

    try:
        # Bước 1: Ép camera lấy nét
        logger.info(f"   -> [{gate}] Đang ép lấy nét (Autofocus)...")
        try:
            requests.get(URL_FOCUS, timeout=2)
        except Exception as e:
            logger.warning(f"⚠️ [{gate}] Focus thất bại: {e} - vẫn tiếp tục chụp")

        # Chờ thấu kính ổn định
        time.sleep(0.6)

        # Bước 2: Lấy dữ liệu ảnh thô
        logger.info(f"   -> [{gate}] Đang tải ảnh về RAM...")
        response = requests.get(URL_SHOT, timeout=5)

        if response.status_code == 200:
            image_bytes = response.content
            filename = f"{gate.lower()}_{_timestamp()}.jpg"
            content_type = response.headers.get("Content-Type", "image/jpeg")
            logger.info(f"✅ [{gate}] Đã lấy ảnh thành công! ({len(image_bytes)} bytes) Dữ liệu sẵn sàng cho YOLO.")
            return image_bytes, filename, content_type
        else:
            logger.error(f"❌ [{gate}] Lỗi: Camera trả về mã {response.status_code}")

    except Exception as e:
        logger.error(f"❌ [{gate}] Lỗi kết nối Camera: {e}")

    # Fallback placeholder
    logger.warning(f"⚠️ [{gate}] Dùng ảnh placeholder do không lấy được ảnh từ camera")
    return _placeholder_image(), f"{gate.lower()}_{_timestamp()}.jpg", "image/jpeg"


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _placeholder_image() -> bytes:
    """JPEG 1x1 pixel trắng - dùng khi không có ảnh thật."""
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
        0x00, 0xFB, 0xD3, 0xFF, 0xD9
    ])
