from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.model import ParkingSlot, User, Sensor
from app.schemas.parking_slots import (
    ParkingSlotCreate,
    ParkingSlotResponse,
    ParkingSlotUpdate,
    ParkingSlotStatusUpdate,
    ParkingSlotWithSensorResponse
)
from fastapi import HTTPException
from datetime import datetime
from uuid import UUID


async def create_new_parking_slot(db: AsyncSession, payload: ParkingSlotCreate, user_id: UUID) -> ParkingSlotResponse:
    user_result = await db.execute(select(User).options(selectinload(User.role)).filter(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="User is not admin")

    parking_slot = ParkingSlot(**payload.dict())
    db.add(parking_slot)
    await db.commit()
    await db.refresh(parking_slot)
    return parking_slot

async def get_parking_slots(db: AsyncSession) -> list[ParkingSlotResponse]:
    result = await db.execute(select(ParkingSlot))
    return result.scalars().all()

async def update_parking_slot(db: AsyncSession, payload: ParkingSlotUpdate, user_id: UUID) -> ParkingSlotResponse:
    user_result = await db.execute(select(User).options(selectinload(User.role)).filter(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="User is not admin")
        
    result = await db.execute(select(ParkingSlot).filter(ParkingSlot.id == payload.id))
    parking_slot = result.scalars().first()
    if not parking_slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
        
    parking_slot.slot_code = payload.slot_code
    parking_slot.status = payload.status
    parking_slot.position_x = payload.position_x
    parking_slot.position_y = payload.position_y
    
    await db.commit()
    await db.refresh(parking_slot)
    return parking_slot

async def update_parking_slot_status(db: AsyncSession, payload: ParkingSlotStatusUpdate) -> ParkingSlotResponse:
    result = await db.execute(select(ParkingSlot).filter(ParkingSlot.id == payload.id))
    parking_slot = result.scalars().first()
    if not parking_slot:
        raise HTTPException(status_code=404, detail="Parking slot not found")
        
    parking_slot.status = payload.status
    await db.commit()
    await db.refresh(parking_slot)
    return parking_slot


async def get_parking_slots_with_active_sensors(db: AsyncSession, user_id: UUID) -> list[ParkingSlotWithSensorResponse]:
    user_result = await db.execute(select(User).options(selectinload(User.role)).filter(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.name != "Admin":
        raise HTTPException(status_code=403, detail="User is not admin")

    result = await db.execute(
        select(ParkingSlot)
        .options(selectinload(ParkingSlot.sensors))
    )
    parking_slots = result.scalars().all()
    
    results = []
    for slot in parking_slots:
        valid_sensors = [s for s in slot.sensors if s.status != "replaced"]
        
        if not valid_sensors:
            continue
            
        valid_sensors.sort(key=lambda x: x.last_heartbeat, reverse=True)
        top_sensor = valid_sensors[0]
        
        results.append(ParkingSlotWithSensorResponse(
            id=slot.id,
            slot_code=slot.slot_code,
            status=slot.status,
            position_x=slot.position_x,
            position_y=slot.position_y,
            created_at=slot.created_at,
            updated_at=slot.updated_at,
            sensors=top_sensor
        ))

    return results

async def has_empty_slot(db: AsyncSession) -> bool:
    result = await db.execute(select(ParkingSlot).filter(ParkingSlot.status == "empty"))
    return len(result.scalars().all()) > 0
