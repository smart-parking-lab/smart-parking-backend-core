from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from lpr import router
import logging
import time

import sys

# Cấu hình format log để dễ đọc, có căn lề level
logger = logging.getLogger("custom_api_logger")
logger.setLevel(logging.INFO)
# Xóa các handler cũ nếu có khi reload
if logger.hasHandlers():
    logger.handlers.clear()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)
# Không lan truyền log lên root logger (không bị in đúp bởi uvicorn)
logger.propagate = False

app = FastAPI(
    title="Parking LPR Service",
    description="Microservice for License Plate Recognition",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    logger.info(f"==> [REQ_IN]  {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"<== [REQ_OUT] {request.method} {request.url.path} | STATUS: {response.status_code} | T/g: {process_time:.3f}s")
    return response

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    """
    Kiểm tra trạng thái hoạt động của service.
    """
    return {
        "status": "active", 
        "service": "parking-lpr-service",
        "description": "API nhận diện biển số xe sử dụng PaddleOCR"
    }

if __name__ == "__main__":
    import uvicorn
    # Chạy service trên port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
