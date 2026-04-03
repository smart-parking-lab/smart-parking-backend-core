import sys
from pathlib import Path

# Cài đặt src vào module path để có thể import từ app.*
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=9000, reload=True)
