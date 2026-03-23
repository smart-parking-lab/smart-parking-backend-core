from pydantic import BaseModel
from typing import Optional

class LPRRequest(BaseModel):
    image_base64: str

class LPRResponse(BaseModel):
    success: bool
    plate_number: str
    message: Optional[str] = None
    
    # Bổ sung thông tin quản lý bãi đỗ
    status: Optional[str] = None # 'in' (vào), 'out' (ra)
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    fee: Optional[float] = None
    duration_hours: Optional[float] = None
