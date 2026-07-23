from collections.abc import AsyncIterator

import httpx
from supabase import Client, create_client

from app.config import settings


def create_service_role_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def create_anon_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def auth_headers(token: str) -> dict[str, str]:
    return {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {token}",
    }


def service_role_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }


async def supabase_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=settings.supabase_url, timeout=10) as client:
        yield client
