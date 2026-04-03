import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_SYSTEM_URL = os.getenv("BACKEND_SYSTEM_URL")

client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global client
    if client is None:
        client = httpx.AsyncClient(
            base_url=BACKEND_SYSTEM_URL,
            timeout=5.0
        )
    return client


async def close_client():
    global client
    if client:
        await client.aclose()
        client = None