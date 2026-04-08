import sys
import asyncio
import signal
from pathlib import Path

# Thêm src vào module path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

import uvicorn
from app.main import app
from app.utils.logger import setup_logging, get_logger
from app.core.config import SERVER_HOST, SERVER_PORT

logger = get_logger("be_system")

_keep_running = True


def _handle_exit(sig, frame):
    global _keep_running
    logger.info("🛑 Nhận tín hiệu thoát. Đang dừng...")
    _keep_running = False


async def main():
    global _keep_running

    setup_logging()
    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    config = uvicorn.Config(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    logger.info("=" * 55)
    print("🚀 SMART PARKING — LPR BACKEND ĐÃ SẴN SÀNG")
    print(f"   🌐 API: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   📷 Chụp camera:  POST /api/v1/recognize/camera")
    print(f"   🖼️  Ảnh local:    POST /api/v1/recognize/local")
    print(f"   📋 Xem sessions: GET  /api/v1/recognize/sessions")
    logger.info("=" * 55)

    try:
        while _keep_running:
            await asyncio.sleep(1)
    finally:
        server.should_exit = True
        await server_task
        logger.info("👋 Hệ thống đã thoát.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
