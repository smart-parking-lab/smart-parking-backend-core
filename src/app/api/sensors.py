from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import sensors_services
from app.schemas.sensors import SensorCreate, SensorUpdate, SensorUpdateStatus
from app.utils.database import get_db
from uuid import UUID

router = APIRouter(prefix="/sensors", tags=["sensors"])

@router.post("", status_code=201)
async def create_sensor(request: Request, payload: SensorCreate, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await sensors_services.create_sensor(db, payload, user_id)

@router.get("")
async def get_all_sensors(request: Request, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await sensors_services.get_all_sensors(db, user_id)

@router.get("/{sensor_id}")
async def get_sensor_by_id(request: Request, sensor_id: UUID, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await sensors_services.get_sensor_by_id(db, sensor_id, user_id)

@router.put("")
async def update_sensor(request: Request, payload: SensorUpdate, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await sensors_services.update_sensor(db, payload, user_id)

@router.put("/status")
async def update_status_sensor(request: Request, payload: SensorUpdateStatus, db: AsyncSession = Depends(get_db)):
    user_payload = request.state.user
    user_id = user_payload.get("sub")
    return await sensors_services.update_status_sensor(db, payload, user_id)
