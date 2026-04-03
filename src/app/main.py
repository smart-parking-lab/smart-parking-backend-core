from fastapi import FastAPI, Depends
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from app.core.cors import setup_cors
from app.api.lpr import router as lpr_router
from app.utils.http_client import close_client
from app.utils.mqtt_client import mqtt_client

load_dotenv()
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client.connect()
    yield
    mqtt_client.disconnect()
    await close_client()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Parking Management Core",
        description="API nhận diện biển số xe",
        version="0.1.0",
        lifespan=lifespan
    )
    

    setup_cors(app)

    app.include_router(lpr_router, prefix="/api/v1")
    @app.get("/", tags=["Health"])
    def health_check():
        return {"status": "ok", "message": "Parking Management core is running"}
    return app


app = create_app()
