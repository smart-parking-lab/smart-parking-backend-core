import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader

from app.core.config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
)
from app.utils.logger import get_logger

logger = get_logger("storage_service")

LOCAL_CAPTURE_DIR = Path("storage") / "captures"
LOCAL_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


def save_image(image_bytes: bytes, folder: str = "captures") -> str | None:
    """
    Upload ảnh lên Cloudinary, nếu lỗi thì fallback lưu local.
    """
    if not image_bytes:
        return None
    try:
        if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
            cloudinary.config(
                cloud_name=CLOUDINARY_CLOUD_NAME,
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                secure=True,
            )
            result = cloudinary.uploader.upload(
                image_bytes,
                folder=folder,
                public_id=str(uuid.uuid4()),
                resource_type="image",
            )
            image_url = result.get("secure_url")
            if image_url:
                logger.info(f"☁️ Đã upload ảnh Cloudinary: {image_url}")
                return image_url
            logger.warning("⚠️ Cloudinary không trả về secure_url, fallback local")
        else:
            logger.warning("⚠️ Thiếu cấu hình Cloudinary, fallback local")
    except Exception as e:
        logger.error(f"❌ Lỗi upload Cloudinary: {e}")

    try:
        save_dir = Path("storage") / folder
        save_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4()}.jpg"
        file_path = save_dir / file_name
        file_path.write_bytes(image_bytes)
        logger.info(f"💾 Fallback lưu ảnh local: {file_path.as_posix()}")
        return file_path.as_posix()
    except Exception as e:
        logger.error(f"❌ Lỗi khi fallback lưu local: {e}")
        return None
