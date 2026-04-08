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

# Skip pre-download at build time because PaddleOCR init can crash
# in constrained build environments (Render builder), causing exit 134.

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SERVER_HOST=0.0.0.0
EXPOSE 10000

CMD ["sh", "-c", "SERVER_PORT=${PORT:-10000} python main.py"]
