import asyncio
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import (
    AuthenticatedUser,
    fetch_chat_thread,
    get_current_user,
    require_chat_thread_owner,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> object:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.supabase.co/rest/v1/chat_threads")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("Supabase request failed", request=request, response=response)


class FakeSupabaseClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    async def get(self, path: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"path": path, **kwargs})
        return self.responses.pop(0)


def bearer(token: str = "token") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_returns_supabase_user() -> None:
    user_id = uuid4()
    client = FakeSupabaseClient(
        [FakeResponse(status.HTTP_200_OK, {"id": str(user_id), "email": "analyst@example.com"})]
    )

    current_user = asyncio.run(get_current_user(bearer(), client))

    assert current_user == AuthenticatedUser(id=user_id, email="analyst@example.com")
    assert client.requests[0]["path"] == "/auth/v1/user"
    assert client.requests[0]["headers"]["Authorization"] == "Bearer token"


def test_get_current_user_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(None, FakeSupabaseClient([])))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_get_current_user_rejects_invalid_token() -> None:
    client = FakeSupabaseClient([FakeResponse(status.HTTP_401_UNAUTHORIZED, {"message": "bad jwt"})])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(bearer("bad-token"), client))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_require_chat_thread_owner_accepts_matching_user() -> None:
    user_id = uuid4()
    thread_id = uuid4()
    current_user = AuthenticatedUser(id=user_id, email="analyst@example.com")
    client = FakeSupabaseClient(
        [FakeResponse(status.HTTP_200_OK, [{"id": str(thread_id), "user_id": str(user_id)}])]
    )

    authorized_thread = asyncio.run(require_chat_thread_owner(thread_id, current_user, client))

    assert authorized_thread.id == thread_id
    assert authorized_thread.user_id == user_id
    assert client.requests[0]["path"] == "/rest/v1/chat_threads"
    assert client.requests[0]["params"]["id"] == f"eq.{thread_id}"


def test_require_chat_thread_owner_rejects_cross_user_access() -> None:
    current_user = AuthenticatedUser(id=uuid4(), email="analyst@example.com")
    client = FakeSupabaseClient(
        [FakeResponse(status.HTTP_200_OK, [{"id": str(uuid4()), "user_id": str(uuid4())}])]
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_chat_thread_owner(uuid4(), current_user, client))

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_fetch_chat_thread_returns_none_for_missing_thread() -> None:
    client = FakeSupabaseClient([FakeResponse(status.HTTP_200_OK, [])])

    thread = asyncio.run(fetch_chat_thread(UUID("00000000-0000-0000-0000-000000000001"), client))

    assert thread is None
