FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
	libgl1 \
	libglib2.0-0 \
	libgomp1 \
	libsm6 \
	libxext6 \
	libxrender1 \
	ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download PaddleOCR models để tránh tải lại lúc runtime (gây timeout 502)
RUN python -c "\
from paddleocr import PaddleOCR; \
PaddleOCR(use_angle_cls=False, lang='en', show_log=True, use_gpu=False); \
print('✅ PaddleOCR models downloaded successfully')"

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SERVER_HOST=0.0.0.0
EXPOSE 10000

CMD ["sh", "-c", "SERVER_PORT=${PORT:-10000} python main.py"]
