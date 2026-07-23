from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database.supabase import auth_headers, service_role_headers, supabase_http_client


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str


@dataclass(frozen=True)
class AuthorizedChatThread:
    id: UUID
    user_id: UUID


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    client: httpx.AsyncClient = Depends(supabase_http_client),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()

    user_data = await fetch_supabase_user(credentials.credentials, client)
    user_id = user_data.get("id")
    email = user_data.get("email")
    if not isinstance(user_id, str) or not isinstance(email, str) or not email:
        raise_unauthorized()

    try:
        parsed_user_id = UUID(user_id)
    except ValueError:
        raise_unauthorized()

    return AuthenticatedUser(id=parsed_user_id, email=email)


async def fetch_supabase_user(token: str, client: httpx.AsyncClient) -> dict:
    response = await client.get("/auth/v1/user", headers=auth_headers(token))
    if response.status_code != status.HTTP_200_OK:
        raise_unauthorized()
    user_data = response.json()
    if not isinstance(user_data, dict):
        raise_unauthorized()
    return user_data


async def require_chat_thread_owner(
    thread_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(supabase_http_client),
) -> AuthorizedChatThread:
    thread = await fetch_chat_thread(thread_id, client)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found",
        )

    user_id = parse_uuid(thread.get("user_id"))
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chat thread",
        )

    return AuthorizedChatThread(id=thread_id, user_id=user_id)


async def fetch_chat_thread(
    thread_id: UUID,
    client: httpx.AsyncClient,
) -> dict | None:
    response = await client.get(
        "/rest/v1/chat_threads",
        headers=service_role_headers(),
        params={
            "id": f"eq.{thread_id}",
            "select": "id,user_id",
            "limit": "1",
        },
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid Supabase response",
        )
    if not rows:
        return None
    if not isinstance(rows[0], dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid Supabase response",
        )
    return rows[0]


def parse_uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid chat thread owner",
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid chat thread owner",
        ) from exc


def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
