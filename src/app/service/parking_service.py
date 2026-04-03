from fastapi import  HTTPException

from app.service.lpr import lpr_service
from app.schemas.schemas import LPRResponse

from app.utils.http_client import get_client

async def process_parking_logic(plate_number: str, image_bytes: bytes, filename: str, content_type: str):
    """
    Xử lý logic lưu xe lúc vào/ra và tính phí.
    """
    if plate_number == "Không nhận diện được" or plate_number == "Không tìm thấy nội dung biển số":
        return None
    client = await get_client()
    # Tìm xem chiếc xe này đang ở trong bãi không?
    response = await client.get("/parking-sessions/check", params={"plate_number": plate_number})
    if response.status_code == 200:
        response = await client.put(
            "/parking-sessions",
            data={"plate_number": plate_number},
            files={
                "exit_image": (filename, image_bytes, content_type)
            }
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Checkout API lỗi")

        return response.json()
    elif response.status_code == 404:
        response = await client.post(
            "/parking-sessions",
            data={"plate_number": plate_number},
            files={
                "entry_image": (filename, image_bytes, content_type)
            }
        )

        if response.status_code != 201:
            raise HTTPException(status_code=500, detail="Checkin API lỗi")

        return response.json()

    else:
        raise HTTPException(status_code=500, detail="Check API lỗi")
        
async def handle_lpr(image_bytes: bytes, filename: str, content_type: str):
    plate_number = await lpr_service.recognize_plate(image_bytes)

    db_info = await process_parking_logic(
        plate_number,
        image_bytes,
        filename,
        content_type
    )

    if not db_info:
        return LPRResponse(
            success=False,
            plate_number=plate_number,
            message="Không nhận diện được biển số"
        )

    return LPRResponse(
        success=True,
        plate_number=plate_number,
        status=db_info.get("status"),
        amount=db_info.get("amount"),
        duration_hours=db_info.get("duration_minutes"),
        message=db_info.get("message")
    )