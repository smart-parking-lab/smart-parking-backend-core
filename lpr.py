from fastapi import APIRouter, UploadFile, File, HTTPException
import base64
from datetime import datetime
from lpr_service import lpr_service
from schemas import LPRResponse, LPRRequest
from database import database, parking_logs
import sqlalchemy

router = APIRouter(prefix="/lpr", tags=["License Plate Recognition"])

@router.on_event("startup")
async def startup():
    await database.connect()

@router.on_event("shutdown")
async def shutdown():
    await database.disconnect()

async def process_parking_logic(plate_number: str):
    """
    Xử lý logic lưu xe lúc vào/ra và tính phí.
    """
    if plate_number == "Không nhận diện được" or plate_number == "Không tìm thấy nội dung biển số":
        return None
        
    # Tìm xem chiếc xe này đang ở trong bãi không?
    query = parking_logs.select().where(
        sqlalchemy.and_(
            parking_logs.c.plate_number == plate_number,
            parking_logs.c.status == "in"
        )
    )
    existing_record = await database.fetch_one(query)

    now = datetime.utcnow()
    
    if existing_record:
        # Xe ĐANG TRONG BÃI -> Đi ra
        entry_time = existing_record["entry_time"]
        duration = now - entry_time
        duration_hours = duration.total_seconds() / 3600.0
        
        # Công thức tính phí giả lập: 10,000 VND / block 1 giờ (có làm tròn lên nửa giờ)
        # Sửa thành chỉ cần lấy chênh lệch, tối thiểu 10k
        hours_rounded = max(1, round(duration_hours + 0.49))
        fee = hours_rounded * 10000.0
        
        # Cập nhật db -> status="out"
        update_query = parking_logs.update().where(
            parking_logs.c.id == existing_record["id"]
        ).values(
            exit_time=now,
            status="out",
            fee=fee
        )
        await database.execute(update_query)
        
        return {
            "status": "out",
            "entry_time": entry_time.isoformat(),
            "exit_time": now.isoformat(),
            "duration_hours": round(duration_hours, 2),
            "fee": fee,
            "message": f"Xe {plate_number} ra. Phí: {fee:,.0f} VND"
        }
    else:
        # Xe KHÔNG CÓ TRONG BÃI -> Đi vào
        insert_query = parking_logs.insert().values(
            plate_number=plate_number,
            entry_time=now,
            status="in"
        )
        await database.execute(insert_query)
        
        return {
            "status": "in",
            "entry_time": now.isoformat(),
            "exit_time": None,
            "duration_hours": 0.0,
            "fee": 0.0,
            "message": f"Xe {plate_number} vào."
        }

@router.post("/recognize", response_model=LPRResponse)
async def recognize_plate(file: UploadFile = File(...)):
    """
    Nhận diện biển số từ file ảnh upload (multipart/form-data).
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh")

    try:
        image_bytes = await file.read()
        plate_number = await lpr_service.recognize_plate(image_bytes)
        
        # Xử lý CSDL check in/out
        db_info = await process_parking_logic(plate_number)
        
        if db_info:
            return LPRResponse(
                success=True,
                plate_number=plate_number,
                message=db_info["message"],
                status=db_info["status"],
                entry_time=db_info["entry_time"],
                exit_time=db_info["exit_time"],
                fee=db_info["fee"],
                duration_hours=db_info["duration_hours"]
            )
        else:
            return LPRResponse(
                success=False,
                plate_number=plate_number,
                message="Lỗi nhận diện, không thể ghi nhận"
            )

    except Exception as e:
        return LPRResponse(
            success=False,
            plate_number="",
            message=f"Lỗi: {str(e)}"
        )

@router.post("/recognize-base64", response_model=LPRResponse)
async def recognize_plate_base64(request: LPRRequest):
    """
    Nhận diện biển số từ chuỗi ảnh Base64 (application/json).
    """
    try:
        # Giải mã base64
        header, encoded = request.image_base64.split(",", 1) if "," in request.image_base64 else (None, request.image_base64)
        image_bytes = base64.b64decode(encoded)
        
        plate_number = await lpr_service.recognize_plate(image_bytes)
        
        # Xử lý CSDL check in/out
        db_info = await process_parking_logic(plate_number)
        
        if db_info:
            return LPRResponse(
                success=True,
                plate_number=plate_number,
                message=db_info["message"],
                status=db_info["status"],
                entry_time=db_info["entry_time"],
                exit_time=db_info["exit_time"],
                fee=db_info["fee"],
                duration_hours=db_info["duration_hours"]
            )
        else:
            return LPRResponse(
                success=False,
                plate_number=plate_number,
                message="Lỗi nhận diện, không thể ghi nhận"
            )

    except Exception as e:
        return LPRResponse(
            success=False,
            plate_number="",
            message=f"Lỗi giải mã base64 hoặc nhận diện: {str(e)}"
        )
