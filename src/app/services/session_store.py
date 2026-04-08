from datetime import datetime, timezone
import uuid

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models.parking_session import ParkingSession
from app.utils.logger import get_logger

logger = get_logger("session_store")


def add_or_complete_session(plate_number: str, image_url: str | None) -> tuple[ParkingSession, str]:
    """
    Nếu xe chưa có phiên active: tạo phiên mới (entry).
    Nếu đã có phiên active: đóng phiên đó (exit).
    """
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        stmt = (
            select(ParkingSession)
            .where(ParkingSession.plate_number == plate_number, ParkingSession.status == "active")
            .order_by(ParkingSession.entry_time.desc())
            .limit(1)
        )
        active_session = db.execute(stmt).scalar_one_or_none()

        if active_session:
            active_session.exit_time = now
            active_session.exit_image_url = image_url
            active_session.status = "completed"
            action = "exit"
            session = active_session
        else:
            session = ParkingSession(
                plate_number=plate_number,
                entry_time=now,
                status="active",
                entry_image_url=image_url,
            )
            db.add(session)
            action = "entry"

        db.commit()
        db.refresh(session)

    logger.info(f"✅ Lưu phiên ({action}): plate={session.plate_number}, id={session.id}")
    return session, action


def get_all_sessions() -> list[dict]:
    with SessionLocal() as db:
        stmt = select(ParkingSession).order_by(ParkingSession.created_at.desc())
        sessions = db.execute(stmt).scalars().all()
        return [s.to_dict() for s in sessions]


def get_session_by_id(session_id: str) -> dict | None:
    with SessionLocal() as db:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return None
        stmt = select(ParkingSession).where(ParkingSession.id == session_uuid)
        session = db.execute(stmt).scalar_one_or_none()
        return session.to_dict() if session else None


def clear_sessions() -> None:
    with SessionLocal() as db:
        db.execute(delete(ParkingSession))
        db.commit()
    logger.info("🗑️ Đã xóa toàn bộ phiên đỗ xe")
