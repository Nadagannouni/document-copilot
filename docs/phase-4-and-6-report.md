# Phase 4 And Phase 6 Implementation Report

This report explains the work completed in Phase 4 and Phase 6 in plain English: what changed, why each change matters, and how the pieces fit together.

## Big Picture

Before Phase 4 and Phase 6, the app had login/auth basics, database tables, and a placeholder frontend screen. It did not yet have a real chat product loop.

Now it has that loop:

1. User signs in.
2. User creates or selects a chat thread.
3. Frontend loads message history.
4. User sends a question.
5. Backend checks auth and thread ownership.
6. Backend streams assistant text back to the frontend.
7. Backend saves the user message and assistant response.
8. Frontend displays the conversation.

That is the core skeleton of the product.

## Phase 4: Backend Chat API

Phase 4 added the backend endpoints that the frontend needs.

### `backend/app/chat/router.py`

This is the main backend chat API file.

It defines routes like:

```text
GET  /chat/threads
POST /chat/threads
GET  /chat/threads/{thread_id}/messages
POST /chat/stream
```

Why it matters:

- The frontend needs a way to list chats.
- It needs a way to create a new chat.
- It needs a way to load previous messages.
- It needs a way to send a message and receive the assistant response as a stream.

Without this file, the frontend chat UI would have nothing real to talk to.

Important parts inside it:

- `list_threads`: gets all chat threads owned by the current signed-in user.
- `create_thread`: creates a new chat thread and ensures the user exists in the local `users` table.
- `list_messages`: loads the messages inside one thread.
- `stream_chat`: handles sending a user question, streaming assistant text, and saving the completed turn.

At first this used a stub response. Then it was changed to stream from Azure OpenAI.

### `backend/app/chat/azure.py`

This file connects the backend to Azure OpenAI.

Why it matters:

- Your Azure API key must stay secret.
- The frontend runs in the browser, so it must never see that key.
- This file keeps Azure calls safely on the backend.

It creates an Azure OpenAI client using:

```text
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_VERSION
AZURE_OPENAI_CHAT_DEPLOYMENT
```

Then it streams GPT-4o output chunk by chunk.

### `backend/app/config.py`

This file was updated with Azure settings.

Why it matters:

- The repo rule says all backend environment variables must go through `app/config.py`.
- This keeps configuration centralized.
- The code does not randomly read environment variables in different files.

### `backend/app/main.py`

This file now mounts the chat router.

The important line is:

```python
app.include_router(chat_router)
```

Why it matters:

- Creating `router.py` is not enough by itself.
- FastAPI only exposes those routes if `main.py` includes the router.
- This line tells the app to make all `/chat/...` endpoints available.

### `backend/tests/conftest.py`

This file was updated with fake Azure environment variables for tests.

Why it matters:

- The backend settings require Azure env vars now.
- Tests should not use real secrets.
- The test setup provides safe dummy values.

### `backend/tests/chat/test_router.py`

This file tests the chat backend.

Why it matters:

- Confirms users need auth.
- Confirms users cannot access someone else's thread.
- Confirms thread creation works.
- Confirms message history works.
- Confirms streaming works.
- Confirms messages are persisted after streaming.

The Azure stream is mocked in tests, so tests do not spend money or call the real API.

## Phase 6: Frontend Chat Experience

Phase 6 added the actual user interface for chat.

### `frontend/src/App.tsx`

Before, `/chat` showed a placeholder page.

Now it routes to the real chat page:

```text
/chat
/chat/:threadId
```

Why it matters:

- `/chat` shows the chat workspace.
- `/chat/:threadId` opens one selected conversation.
- This is how clicking a thread changes the visible chat.

### `frontend/src/pages/ChatPage.tsx`

This is the main frontend chat screen.

Why it matters:

It coordinates almost everything the user sees:

- loading threads
- creating a new thread
- loading messages
- sending a message
- receiving streaming response text
- showing errors
- selecting citation chips
- opening the source panel

Think of this as the brain of the chat UI.

### `frontend/src/lib/api.ts`

This file was updated with `streamChat`.

Why it matters:

- Normal API calls return JSON after the backend is done.
- Chat streaming is different: the backend sends little text pieces over time.
- `streamChat` reads those pieces and gives them to the UI as they arrive.

This is what makes the assistant message appear gradually instead of only appearing at the end.

### `frontend/src/components/chat/ThreadList.tsx`

This is the left sidebar.

Why it matters:

- Shows all chat threads.
- Lets the user select a thread.
- Lets the user create a new thread.
- Shows loading and error states for thread loading.

### `frontend/src/components/chat/MessageTimeline.tsx`

This renders the actual conversation.

Why it matters:

- Shows user messages.
- Shows assistant messages.
- Shows a streaming spinner while the assistant is still responding.
- Shows citation chips on assistant messages.
- Shows `No citations attached yet` for now because retrieval is not implemented yet.
- Detects `not enough evidence` style answers and displays them clearly.

### `frontend/src/components/chat/ChatComposer.tsx`

This is the message input box.

Why it matters:

- Lets the user type a question.
- Sends the message.
- Disables while the assistant is streaming, so the user does not accidentally send overlapping requests.

### `frontend/src/components/chat/SourcePanel.tsx`

This is the citation/source viewer.

Why it matters:

- Later, when retrieval is implemented, assistant answers will have citations.
- Clicking a citation chip will show the source excerpt and metadata here.
- On desktop it appears as a right panel.
- On smaller screens it behaves like a drawer.

Right now it is mostly future-ready because the backend returns empty citations until retrieval exists.

### `frontend/src/components/chat/types.ts`

This file contains frontend-only chat types.

Why it matters:

- The backend message type does not know about frontend-only things like `isStreaming`.
- This file defines those UI-specific shapes cleanly.

### Removed: `frontend/src/pages/ChatHomePage.tsx`

This file was removed because it was only a placeholder page.

After adding the real `ChatPage`, it was no longer used.

## Environment Files

### `backend/.env.example`

This file was updated with Azure example values.

Why it matters:

- It tells developers what env vars they need.
- It does not contain real secrets.

### `backend/.env`

This local file was updated with Azure placeholders.

Why it matters:

- This is your local backend config file.
- You need to replace placeholders with your real Azure values.

The required Azure values are:

```env
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
```

### `frontend/.env.example`

This file was updated with a warning that Azure keys belong only in the backend.

Why it matters:

- Anything starting with `VITE_` becomes visible in the browser.
- API keys must never go there.
- The frontend only needs the backend URL and public Supabase anon key.

## How The Chat Flow Works Now

When you ask a question:

1. `ChatComposer` captures your text.
2. `ChatPage` adds a temporary user message to the screen.
3. `ChatPage` calls `api.streamChat`.
4. `api.streamChat` sends the request to FastAPI.
5. FastAPI checks your Supabase auth token.
6. FastAPI checks you own the selected thread.
7. FastAPI sends the messages to Azure OpenAI.
8. Azure sends text chunks back.
9. FastAPI forwards those chunks as SSE events.
10. Frontend receives each chunk and appends it to the assistant message.
11. Backend saves the final user and assistant messages.
12. Frontend reloads message history from the database.

So now the product has a real end-to-end chat loop.

## What Is Still Missing

The assistant can now answer using GPT-4o through Azure, but it does not yet truly read SEC filings.

That comes next in later phases:

- Phase 7: ingest SEC filings into the database
- Phase 8: retrieve relevant filing chunks
- Phase 9: force grounded answers with citations

Right now, the assistant is connected to GPT-4o, but citation grounding is not fully real yet. The UI is ready for citations, but the retrieval backend still needs to be built.

