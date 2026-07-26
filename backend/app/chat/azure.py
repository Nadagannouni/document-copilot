from collections.abc import AsyncIterator

from openai import AsyncAzureOpenAI

from app.config import settings


SYSTEM_PROMPT = (
    "You are Document Copilot, an analyst assistant. Answer concisely from the chat context. "
    "When filing retrieval is unavailable, say that citations are not connected yet instead of "
    "pretending to have evidence."
)


def create_azure_openai_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


async def stream_azure_chat_response(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    client = create_azure_openai_client()
    stream = await client.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        model=settings.azure_openai_chat_deployment,
        stream=True,
    )

    async for event in stream:
        if not event.choices:
            continue

        content = event.choices[0].delta.content
        if content:
            yield content
