from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import DATABASE_URL


def _normalize_sync_database_url(url: str) -> str:
    """
    SQLAlchemy sync engine không dùng được asyncpg URL.
    Tự động chuyển postgresql+asyncpg:// -> postgresql+psycopg2://
    """
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return url


engine = create_engine(_normalize_sync_database_url(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency: tạo DB session cho mỗi request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
