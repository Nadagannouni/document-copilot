# Backend

FastAPI service for Document Copilot.

## Setup

```powershell
cd backend
uv sync
Copy-Item .env.example .env
```

Edit `.env` with the required Supabase, OpenAI, database, and CORS settings.

## Run locally

```powershell
uv run uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Useful URLs:

- Health check: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

## Tests and linting

```powershell
uv run pytest
uv run ruff check .
```

## Database migrations

Run migrations from this folder:

```powershell
uv run alembic upgrade head
```

Review generated Alembic migrations before applying them.

## Configuration

Application settings live in `app/config.py`. Keep environment access there rather than reading env vars directly in app code.
