import os
from dotenv import load_dotenv

load_dotenv()

# ===== Camera =====
CAMERA_URL = os.getenv("CAMERA_URL", "http://192.168.1.41:8080/shot.jpg")
CAMERA_ROTATE_DEG = int(os.getenv("CAMERA_ROTATE_DEG", "90"))

# ===== Thư mục ảnh local dùng cho test =====
IMAGE_DIR = os.getenv("IMAGE_DIR", r"E:\tam\smart-parking-backend-core\tests\image")

# ===== Database =====
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ===== Cloudinary =====
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# ===== Server =====
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
