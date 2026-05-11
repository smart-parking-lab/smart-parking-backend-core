from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY_ACCESS_TOKEN = os.getenv("SECRET_KEY_ACCESS_TOKEN", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


PUBLIC_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("GET",  "/"),
    ("GET",  "/docs"),                 
    ("GET",  "/openapi.json"),          
    ("GET",  "/redoc"), 
    # Cho phép Core LPR service gọi nội bộ
    ("GET", "/api/v1/parking-slots"),

    ("POST", "/api/v1/parking-sessions"),
    ("PUT",  "/api/v1/parking-sessions"),
    ("OPTIONS", "/api/v1/auth/login"),
    ("OPTIONS", "/api/v1/auth/me"),
    ("OPTIONS", "/api/v1/parking-sessions"),
}


class JWTAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        key = (request.method.upper(), request.url.path)

        if key in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Thiếu token xác thực (Authorization: Bearer <token>)"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY_ACCESS_TOKEN, algorithms=[ALGORITHM])
            request.state.user = payload
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token không hợp lệ hoặc đã hết hạn"},
            )

        return await call_next(request)
