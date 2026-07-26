import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.auth.dependencies import AuthenticatedUser
from app.chat.router import (
    ChatStreamRequest,
    CreateThreadRequest,
    create_thread,
    latest_user_message,
    list_messages,
    list_threads,
    stream_chat,
)
from app.main import app


CREATED_AT = "2026-07-25T10:00:00+00:00"
UPDATED_AT = "2026-07-25T10:01:00+00:00"
ASSISTANT_RESPONSE = "Azure streamed response."


class FakeResponse:
    def __init__(self, status_code: int, payload: object = None) -> None:
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
        self.requests.append({"method": "GET", "path": path, **kwargs})
        return self.responses.pop(0)

    async def post(self, path: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"method": "POST", "path": path, **kwargs})
        return self.responses.pop(0)


def thread_row(thread_id: str, user_id: str | None = None) -> dict[str, str]:
    row = {
        "id": thread_id,
        "title": "Margin analysis",
        "created_at": CREATED_AT,
        "updated_at": UPDATED_AT,
    }
    if user_id:
        row["user_id"] = user_id
    return row


def current_user(user_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(id=user_id or uuid4(), email="analyst@example.com")


def test_chat_endpoints_require_auth() -> None:
    client = TestClient(app)

    response = client.get("/chat/threads")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_threads_returns_current_user_threads() -> None:
    user = current_user()
    first_thread_id = uuid4()
    second_thread_id = uuid4()
    client = FakeSupabaseClient(
        [
            FakeResponse(
                status.HTTP_200_OK,
                [
                    thread_row(str(first_thread_id)),
                    thread_row(str(second_thread_id)),
                ],
            )
        ]
    )

    response = asyncio.run(list_threads(user, client))

    assert [thread.id for thread in response.threads] == [first_thread_id, second_thread_id]
    assert client.requests[0]["path"] == "/rest/v1/chat_threads"
    assert client.requests[0]["params"]["user_id"] == f"eq.{user.id}"
    assert client.requests[0]["params"]["order"] == "updated_at.desc"


def test_create_thread_upserts_user_and_inserts_thread() -> None:
    user = current_user()
    thread_id = uuid4()
    client = FakeSupabaseClient(
        [
            FakeResponse(status.HTTP_201_CREATED, []),
            FakeResponse(status.HTTP_201_CREATED, [thread_row(str(thread_id))]),
        ]
    )

    response = asyncio.run(create_thread(CreateThreadRequest(title="  Revenue mix  "), user, client))

    assert response.id == thread_id
    assert response.title == "Margin analysis"
    assert client.requests[0]["path"] == "/rest/v1/users"
    assert client.requests[0]["json"] == {"id": str(user.id), "email": user.email}
    assert client.requests[1]["path"] == "/rest/v1/chat_threads"
    assert client.requests[1]["json"]["user_id"] == str(user.id)
    assert client.requests[1]["json"]["title"] == "Revenue mix"


def test_list_messages_returns_history_with_empty_citations() -> None:
    thread_id = uuid4()
    message_id = uuid4()
    client = FakeSupabaseClient(
        [
            FakeResponse(
                status.HTTP_200_OK,
                [
                    {
                        "id": str(message_id),
                        "thread_id": str(thread_id),
                        "role": "user",
                        "content": "What changed?",
                        "created_at": CREATED_AT,
                        "message_json": {"role": "user", "content": "What changed?"},
                    }
                ],
            ),
        ]
    )

    response = asyncio.run(list_messages(thread_id, None, client))

    assert len(response.messages) == 1
    assert response.messages[0].id == message_id
    assert response.messages[0].citations == []
    assert client.requests[0]["path"] == "/rest/v1/chat_messages"
    assert client.requests[0]["params"]["thread_id"] == f"eq.{thread_id}"


def test_stream_rejects_cross_user_thread_access() -> None:
    user = current_user()
    thread_id = uuid4()
    other_user_id = uuid4()
    client = FakeSupabaseClient(
        [FakeResponse(status.HTTP_200_OK, [thread_row(str(thread_id), str(other_user_id))])]
    )
    body = ChatStreamRequest(threadId=thread_id, messages=[{"role": "user", "content": "Hi"}])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(stream_chat(body, user, client, fake_assistant_streamer))

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_stream_rejects_empty_or_missing_user_messages() -> None:
    with pytest.raises(HTTPException) as empty_exc:
        latest_user_message([])

    with pytest.raises(HTTPException) as no_user_exc:
        latest_user_message([{"role": "assistant", "content": "Hello"}])

    assert empty_exc.value.status_code == 422
    assert no_user_exc.value.status_code == 422


def test_stream_emits_deltas_completion_and_persists_messages() -> None:
    user = current_user()
    thread_id = uuid4()
    user_message = {"role": "user", "content": [{"type": "text", "text": "Summarize revenue"}]}
    client = FakeSupabaseClient(
        [
            FakeResponse(status.HTTP_200_OK, [thread_row(str(thread_id), str(user.id))]),
            FakeResponse(status.HTTP_201_CREATED, []),
        ]
    )
    body = ChatStreamRequest(threadId=thread_id, messages=[user_message])

    response = asyncio.run(stream_chat(body, user, client, fake_assistant_streamer))
    events = asyncio.run(collect_stream(response.body_iterator))
    stream_text = "".join(event for event in events if event.startswith("event: delta"))

    assert "event: complete" in "".join(events)
    assert ASSISTANT_RESPONSE in "".join(events)
    assert "Azure " in stream_text
    assert client.requests[1]["path"] == "/rest/v1/chat_messages"
    persisted_messages = client.requests[1]["json"]
    assert persisted_messages[0]["role"] == "user"
    assert persisted_messages[0]["content"] == "Summarize revenue"
    assert persisted_messages[0]["message_json"] == user_message
    assert persisted_messages[1]["role"] == "assistant"
    assert persisted_messages[1]["content"] == ASSISTANT_RESPONSE
    assert persisted_messages[1]["message_json"] == {"provider": "azure_openai"}


async def collect_stream(body_iterator) -> list[str]:
    chunks = []
    async for chunk in body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return chunks


async def fake_assistant_streamer(messages: list[dict[str, str]]):
    assert messages[-1] == {"role": "user", "content": "Summarize revenue"}
    yield "Azure "
    yield "streamed response."
