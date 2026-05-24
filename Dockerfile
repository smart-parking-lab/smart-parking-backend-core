# Sử dụng Python 3.11-slim từ Debian Bookworm để tối ưu dung lượng và tính tương thích cao
FROM python:3.11-slim-bookworm

# Khai báo các thông tin về Image
LABEL maintainer="smart-parking-team"
LABEL description="Backend Core của hệ thống Smart Parking Management System"

# Cài đặt các công cụ biên dịch để build psycopg2 từ source
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Sao chép công cụ quản lý thư viện UV siêu tốc từ Astral official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Cấu hình các biến môi trường cần thiết
ENV UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Sao chép các tệp quản lý dependencies để tận dụng cơ chế Docker Caching
COPY pyproject.toml uv.lock ./

# Cài đặt toàn bộ thư viện dependencies mà không cần copy code dự án (giúp build lại cực nhanh)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Sao chép toàn bộ mã nguồn của Backend vào container
COPY . .

# Đồng bộ hóa và biên dịch toàn bộ dự án
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Đưa môi trường ảo (.venv) vào đầu biến PATH để gọi trực tiếp các lệnh python/uvicorn
ENV PATH="/app/.venv/bin:$PATH"

# Cổng dịch vụ lắng nghe
EXPOSE 9000

# Chạy ứng dụng FastAPI thông qua Uvicorn
# Ràng buộc host 0.0.0.0 để Docker có thể ánh xạ cổng ra ngoài máy chủ
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
