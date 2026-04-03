from pydantic import BaseModel
from typing import Optional

class LPRRequest(BaseModel):
    image_base64: str

class LPRResponse(BaseModel):
    success: bool
    plate_number: str

    status: Optional[str] = None 
    amount: Optional[float] = None
    duration_hours: Optional[float] = None

