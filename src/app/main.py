from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.cors import setup_cors
from app.api.health import router as health_router
from app.api.recognize import router as recognize_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Parking — LPR Backend",
        description="Backend nhận diện biển số xe: chụp từ camera hoặc ảnh local",
        version="2.0.0",
    )

    setup_cors(app)
    storage_dir = Path("storage")
    storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(recognize_router, prefix="/api/v1")

    @app.get("/", tags=["Root"])
    def root():
        return {"status": "ok", "service": "Smart Parking — LPR Backend"}

    return app


app = create_app()
