from fastapi import APIRouter,UploadFile,HTTPException
from app.schemas.schemas import LPRRequest,LPRResponse
from app.service.parking_service import handle_lpr

import base64
router = APIRouter(prefix="/lpr", tags=["LPR"])

@router.post("/recognize", response_model=LPRResponse)
async def recognize_plate(file: UploadFile):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh")

    image_bytes = await file.read()

    return await handle_lpr(
        image_bytes,
        file.filename,
        file.content_type
    )

@router.post("/recognize-base64", response_model=LPRResponse)
async def recognize_plate_base64(request: LPRRequest):
    header, encoded = request.image_base64.split(",", 1) if "," in request.image_base64 else (None, request.image_base64)
    image_bytes = base64.b64decode(encoded)

    content_type = "image/jpeg"
    if header:
        if "image/png" in header:
            content_type = "image/png"

    return await handle_lpr(
        image_bytes,
        "image.jpg",
        content_type
    )

