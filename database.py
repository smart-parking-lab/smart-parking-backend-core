import databases
import sqlalchemy
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables.")

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

parking_logs = sqlalchemy.Table(
    "parking_logs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("plate_number", sqlalchemy.String, index=True),
    sqlalchemy.Column("entry_time", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("exit_time", sqlalchemy.DateTime, nullable=True),
    sqlalchemy.Column("status", sqlalchemy.String, default="in"), # 'in' hoặc 'out'
    sqlalchemy.Column("fee", sqlalchemy.Float, nullable=True),
)

# sqlalchemy requires postgresql:// instead of postgres://, adjust if needed
engine_url = DATABASE_URL
if engine_url.startswith("postgres://"):
    engine_url = engine_url.replace("postgres://", "postgresql://", 1)

engine = sqlalchemy.create_engine(engine_url)
metadata.create_all(engine)
