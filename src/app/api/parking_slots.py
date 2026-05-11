from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.parking_slots import (
    ParkingSlotCreate,
    ParkingSlotResponse,
    ParkingSlotUpdate,
    ParkingSlotStatusUpdate,
    ParkingSlotWithSensorResponse
)
from app.services import parking_slots_services
from app.utils.database import get_db

router = APIRouter(prefix="/parking-slots", tags=["Parking Slots"])

@router.post("", response_model=ParkingSlotResponse)
async def create_parking_slot(request: Request, payload: ParkingSlotCreate, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await parking_slots_services.create_new_parking_slot(db, payload, user_id)

@router.get("", response_model=list[ParkingSlotResponse])
async def get_all_parking_slots(request: Request, db: AsyncSession = Depends(get_db)):
    return await parking_slots_services.get_parking_slots(db)

@router.put("", response_model=ParkingSlotResponse)
async def update_parking_slot(request: Request, payload: ParkingSlotUpdate, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await parking_slots_services.update_parking_slot(db, payload, user_id)


@router.put("/status", response_model=ParkingSlotResponse)
async def update_parking_slot_status(request: Request, payload: ParkingSlotStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await parking_slots_services.update_parking_slot_status(db, payload)

@router.get("/with-sensors", response_model=list[ParkingSlotWithSensorResponse])
async def get_parking_slots_with_sensors(request: Request, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await parking_slots_services.get_parking_slots_with_active_sensors(db, user_id)
