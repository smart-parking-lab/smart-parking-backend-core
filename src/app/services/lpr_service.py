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


def normalize_vn_plate_string(plate: str) -> str:
    """
    Chuan hoa chuoi bien sau OCR theo kieu bien VN (xe may pho bien: 2 so tinh + ky hieu chu + day so).

    - O vi tri chu (sau 2 so ma tinh): so hay doc nham thanh chu: 6->G, 0->D, 8->B, 4->A, 1/7->T, 2->Z, 5->S
      (ap dung neu sau ky tu do con it nhat 4 chu so lien tiep; ca bien 7 ky tu nhu 55B6970).
    - Phan day so phia sau: chu hay doc nham thanh so: B->8, A->4, T->1, D/O/Q->0, I/L->1, v.v.
    """
    if not plate or plate == "UNKNOWN":
        return plate
    p = "".join(c for c in plate.upper() if c.isalnum())
    if len(p) < 7:
        return p

    # Truong hop OCR dinh them 1 ky tu so o dau (vat the la, chu so tren xe...):
    # Vi du 177C139373 -> bo ky tu dau tien -> 77C139373 (format VN thuong: 2 so + 1 chu + day so).
    if len(p) >= 8 and p[0].isdigit() and p[1].isdigit() and p[2].isdigit() and p[3].isalpha():
        p = p[1:]

    # O vi tri thu 3 (index 2): thuong la chu (Z, G, B, ...), OCR doi khi doc thanh so.
    # Xe may co day so ngan (vi du 4 so sau chu): can p>=7 va tail>=4, khong bat buoc p>=9.
    if len(p) >= 7 and p[0].isdigit() and p[1].isdigit():
        tail = p[3:]
        if len(tail) >= 4 and tail.isdigit():
            digit_misread_as_letter = {
                "0": "D",
                "1": "T",
                "2": "Z",
                "4": "A",
                "5": "S",
                "6": "G",
                "7": "T",
                "8": "B",
            }
            if p[2] in digit_misread_as_letter:
                p = p[:2] + digit_misread_as_letter[p[2]] + tail

    # Sau XX + mot chu cai: phan con lai la day so; chu cai trong do thuong la OCR nham.
    if len(p) >= 4 and p[0].isdigit() and p[1].isdigit() and p[2].isalpha():
        prefix, suffix = p[:3], p[3:]
        letter_misread_in_digits = str.maketrans(
            {
                "B": "8",
                "A": "4",
                "T": "1",
                "D": "0",
                "O": "0",
                "Q": "0",
                "I": "1",
                "L": "1",
                "Z": "2",
                "S": "5",
                "G": "6",
            }
        )
        p = prefix + suffix.translate(letter_misread_in_digits)

    return p


def _run_ocr_with_fallback(img: np.ndarray):
    """OCR voi fallback upscale 2x neu pass dau khong co detection."""
    result = ocr.ocr(img)
    if result and result[0]:
        return result

    upscaled = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    result_up = ocr.ocr(upscaled)
    if result_up and result_up[0]:
        return result_up
    return result


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
    """Nhan dien toan anh, sau do gom cum quanh 1 anchor de giam nhieu."""
    result = _run_ocr_with_fallback(img)

    if not result or not result[0]:
        logger.info("Ket qua nhan dien: UNKNOWN")
        return "UNKNOWN"

    candidates: list[dict] = []
    for line in result[0]:
        points = line[0]
        text = line[1][0]
        confidence = line[1][1]

        clean_text = "".join(c for c in text if c.isalnum()).upper()
        if not clean_text:
            continue

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bx = sum(xs) / len(xs)
        by = sum(ys) / len(ys)

        candidates.append(
            {
                "text": clean_text,
                "confidence": confidence,
                "x": bx,
                "y": by,
                "w": max(xs) - min(xs),
                "h": max(ys) - min(ys),
                "area": (max(xs) - min(xs)) * (max(ys) - min(ys)),
                "xmin": min(xs),
                "ymin": min(ys),
                "xmax": max(xs),
                "ymax": max(ys),
            }
        )

    if not candidates:
        plate = "UNKNOWN"
        logger.info(f"Ket qua nhan dien: {plate}")
        return plate

    def is_attached_to_anchor(c: dict, a: dict) -> bool:
        if c is a:
            return True
        tol_x = max(min(a["w"], c["w"]) * 0.20, 6.0)
        tol_y = max(min(a["h"], c["h"]) * 0.20, 4.0)
        overlap_w = min(c["xmax"], a["xmax"]) - max(c["xmin"], a["xmin"])
        overlap_h = min(c["ymax"], a["ymax"]) - max(c["ymin"], a["ymin"])
        gap_x = max(0.0, max(c["xmin"], a["xmin"]) - min(c["xmax"], a["xmax"]))
        gap_y = max(0.0, max(c["ymin"], a["ymin"]) - min(c["ymax"], a["ymax"]))
        return (overlap_w >= -tol_x and overlap_h >= -tol_y) or (gap_x <= tol_x and gap_y <= tol_y)

    # Gom thanh cac cum text theo quan he "dinh/trung nhau".
    unvisited = set(range(len(candidates)))
    components: list[list[dict]] = []
    while unvisited:
        start = unvisited.pop()
        stack = [start]
        comp_idx = [start]
        while stack:
            i = stack.pop()
            ci = candidates[i]
            attached = [j for j in list(unvisited) if is_attached_to_anchor(candidates[j], ci)]
            for j in attached:
                unvisited.remove(j)
                stack.append(j)
                comp_idx.append(j)
        components.append([candidates[i] for i in comp_idx])

    def is_short_numeric_component(comp: list[dict]) -> bool:
        comp_text = "".join(c["text"] for c in comp)
        return comp_text.isdigit() and len(comp_text) <= 3

    filtered_components = [comp for comp in components if not is_short_numeric_component(comp)]
    if filtered_components:
        components = filtered_components

    def comp_metrics(comp: list[dict]) -> tuple[float, float, float, float, int]:
        x1 = min(c["xmin"] for c in comp)
        y1 = min(c["ymin"] for c in comp)
        x2 = max(c["xmax"] for c in comp)
        y2 = max(c["ymax"] for c in comp)
        area = float(max(1.0, (x2 - x1) * (y2 - y1)))
        conf_max = float(max(c["confidence"] for c in comp))
        comp_text = "".join(c["text"] for c in comp)
        digit_ratio = (sum(ch.isdigit() for ch in comp_text) / len(comp_text)) if comp_text else 0.0
        # Bien xe may thuong o nua duoi anh: uu tien cum co tam y lon hon.
        cy = float((y1 + y2) / 2.0)
        lower_half_score = cy
        return digit_ratio, lower_half_score, area, conf_max, len(comp)

    # Uu tien cum giong bien so: nhieu so, o nua duoi, sau do moi den kich thuoc/mau.
    components.sort(key=lambda comp: comp_metrics(comp), reverse=True)
    cluster = components[0]

    cluster.sort(key=lambda c: (c["y"], c["x"]))

    plate = "".join(c["text"] for c in cluster).upper()
    if not plate:
        plate = "UNKNOWN"
    else:
        plate = normalize_vn_plate_string(plate)

    logger.info(f"Ket qua nhan dien: {plate}")
    return plate
