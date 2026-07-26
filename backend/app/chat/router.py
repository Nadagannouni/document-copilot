import json
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import AuthenticatedUser, get_current_user, require_chat_thread_owner
from app.chat.azure import stream_azure_chat_response
from app.database.supabase import service_role_headers, supabase_http_client


router = APIRouter(prefix="/chat", tags=["chat"])

type AssistantStreamer = Callable[[list[dict[str, str]]], AsyncIterator[str]]


class CreateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatThreadResponse(BaseModel):
    id: UUID
    title: str
    created_at: str
    updated_at: str


class ListThreadsResponse(BaseModel):
    threads: list[ChatThreadResponse]


class MessageCitationResponse(BaseModel):
    id: UUID
    document_chunk_id: UUID
    citation_index: int
    excerpt: str
    metadata: dict[str, Any]


class ChatMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str
    message_json: Any
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class ListMessagesResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    thread_id: UUID = Field(alias="threadId")
    messages: list[dict[str, Any]]


@router.get("/threads", response_model=ListThreadsResponse)
async def list_threads(
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(supabase_http_client),
) -> ListThreadsResponse:
    response = await client.get(
        "/rest/v1/chat_threads",
        headers=service_role_headers(),
        params={
            "user_id": f"eq.{current_user.id}",
            "select": "id,title,created_at,updated_at",
            "order": "updated_at.desc",
        },
    )
    rows = parse_supabase_rows(response)
    return ListThreadsResponse(threads=[parse_thread(row) for row in rows])


@router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: CreateThreadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(supabase_http_client),
) -> ChatThreadResponse:
    await upsert_user(current_user, client)

    title = body.title.strip() if body.title else "New chat"
    if not title:
        title = "New chat"

    response = await client.post(
        "/rest/v1/chat_threads",
        headers={
            **service_role_headers(),
            "Prefer": "return=representation",
        },
        json={
            "user_id": str(current_user.id),
            "title": title,
        },
        params={"select": "id,title,created_at,updated_at"},
    )
    rows = parse_supabase_rows(response)
    if len(rows) != 1:
        raise_bad_gateway("Invalid Supabase response")
    return parse_thread(rows[0])


@router.get("/threads/{thread_id}/messages", response_model=ListMessagesResponse)
async def list_messages(
    thread_id: UUID,
    _authorized_thread=Depends(require_chat_thread_owner),
    client: httpx.AsyncClient = Depends(supabase_http_client),
) -> ListMessagesResponse:
    response = await client.get(
        "/rest/v1/chat_messages",
        headers=service_role_headers(),
        params={
            "thread_id": f"eq.{thread_id}",
            "select": "id,thread_id,role,content,created_at,message_json",
            "order": "created_at.asc",
        },
    )
    rows = parse_supabase_rows(response)
    return ListMessagesResponse(messages=[parse_message(row) for row in rows])


@router.post("/stream")
async def stream_chat(
    body: ChatStreamRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    client: httpx.AsyncClient = Depends(supabase_http_client),
    assistant_streamer: AssistantStreamer = Depends(lambda: stream_azure_chat_response),
) -> StreamingResponse:
    await require_chat_thread_owner(body.thread_id, current_user, client)
    user_message = latest_user_message(body.messages)
    chat_messages = chat_completion_messages(body.messages)

    return StreamingResponse(
        stream_assistant_response(body.thread_id, user_message, chat_messages, client, assistant_streamer),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def stream_assistant_response(
    thread_id: UUID,
    user_message: dict[str, Any],
    chat_messages: list[dict[str, str]],
    client: httpx.AsyncClient,
    assistant_streamer: AssistantStreamer,
) -> AsyncIterator[str]:
    assistant_content = ""

    try:
        async for chunk in assistant_streamer(chat_messages):
            assistant_content += chunk
            yield sse_event("delta", {"text": chunk})

        await persist_chat_turn(thread_id, user_message, assistant_content, client)
        yield sse_event("complete", {"content": assistant_content})
    except Exception:
        yield sse_event("error", {"detail": "Chat response failed"})


async def upsert_user(user: AuthenticatedUser, client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/rest/v1/users",
        headers={
            **service_role_headers(),
            "Prefer": "resolution=merge-duplicates",
        },
        json={
            "id": str(user.id),
            "email": user.email,
        },
        params={"on_conflict": "id"},
    )
    if response.status_code >= 400:
        raise_bad_gateway("Failed to upsert user")


async def persist_chat_turn(
    thread_id: UUID,
    user_message: dict[str, Any],
    assistant_content: str,
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/rest/v1/chat_messages",
        headers=service_role_headers(),
        json=[
            {
                "thread_id": str(thread_id),
                "role": "user",
                "content": message_text(user_message),
                "message_json": user_message,
            },
            {
                "thread_id": str(thread_id),
                "role": "assistant",
                "content": assistant_content,
                "message_json": {
                    "provider": "azure_openai",
                },
            },
        ],
    )
    if response.status_code >= 400:
        raise_bad_gateway("Failed to persist chat messages")


def latest_user_message(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if not messages:
        raise HTTPException(
            status_code=422,
            detail="messages must include at least one message",
        )

    for message in reversed(messages):
        if message.get("role") == "user":
            if not message_text(message):
                raise HTTPException(
                    status_code=422,
                    detail="latest user message content cannot be empty",
                )
            return message

    raise HTTPException(
        status_code=422,
        detail="messages must include a user message",
    )


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "\n".join(parts).strip()
    return ""


def chat_completion_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    chat_messages: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role")
        if role not in {"user", "assistant", "system"}:
            continue

        content = message_text(message)
        if content:
            chat_messages.append({"role": role, "content": content})

    return chat_messages


def parse_supabase_rows(response: httpx.Response) -> list[dict[str, Any]]:
    if response.status_code >= 400:
        raise_bad_gateway("Supabase request failed")

    rows = response.json()
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise_bad_gateway("Invalid Supabase response")
    return rows


def parse_thread(row: dict[str, Any]) -> ChatThreadResponse:
    return ChatThreadResponse(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_message(row: dict[str, Any]) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=row["id"],
        thread_id=row["thread_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
        message_json=row.get("message_json"),
        citations=[],
    )


def sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def raise_bad_gateway(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
    )
