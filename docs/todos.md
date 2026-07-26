# Document Copilot Implementation Checklist

## Build Order

Start with the backend foundations, then build a thin frontend against stubbed backend endpoints, then replace the stubs with ingestion, retrieval, LLM, and grounding.

That order is the most logical for this project because the client brief is trust-heavy: citations, source passages, user-owned chat history, and refusal behavior matter more than visual polish. The frontend should be useful early, but it should not invent product behavior that the backend cannot support.

Recommended sequence:

1. Backend skeleton and config
2. Database schema and migrations
3. Auth boundary between Supabase and FastAPI
4. Stubbed chat API and streaming contract
5. Frontend auth, routing, chat UI, and citation surfaces
6. Ingestion pipeline for SEC filings
7. Hybrid retrieval with vector search and full-text search
8. PydanticAI assistant and grounding validation
9. End-to-end pilot hardening, deployment, and client acceptance checks

## Phase 0 - Project Decisions

- [x] Confirm the first pilot corpus: Apple, Amazon, Alphabet, Microsoft, and NVIDIA 10-Ks for 2021-2025.
- [x] Confirm the pilot user scope: Driftwood email-only auth, no SSO, no multi-tenant roles.
- [x] Confirm the answer contract: every factual claim needs a citation, and unsupported questions must be refused clearly.
- [x] Confirm that Railway has two services: one FastAPI backend service and one Vite frontend service.
- [x] Confirm Supabase project setup and collect required local env values.

## Phase 1 - Backend Foundation

- [x] Create the FastAPI app structure under `backend/app/`.
- [x] Add `app/config.py` using `pydantic-settings` as the single source of truth for backend env vars.
- [x] Add the FastAPI entrypoint in `app/main.py`.
- [x] Add a health endpoint, such as `GET /health`.
- [x] Configure CORS from `ALLOWED_ORIGINS`.
- [ ] Add structured logging with `structlog`.
- [ ] Add backend test setup with `pytest`.
- [x] Verify backend starts locally with `uv run uvicorn app.main:app --reload`.

## Phase 2 - Database Schema

- [x] Set up Alembic in `backend/`.
- [x] Create SQLAlchemy models in `app/database/models/`, one file per model.
- [x] Model `users`.
- [x] Model `chat_threads`.
- [x] Model `chat_messages`.
- [x] Model `message_citations`.
- [x] Model `source_documents`.
- [x] Model `document_chunks`.
- [x] Add an initial migration that enables `pgvector`.
- [x] Add vector columns, generated full-text search vectors, HNSW indexes, GIN indexes, and normal relational indexes.
- [x] Add RLS policies for user-owned chat data.
- [x] Add service-role-safe policies for ingestion and document writes.
- [x] Apply migrations against Supabase using the direct/session `DATABASE_URL`.

## Phase 3 - Supabase Auth Boundary

- [x] Add `app/auth/dependencies.py` to verify `Authorization: Bearer <token>`.
- [x] Derive the authenticated user ID and email from Supabase Auth.
- [x] Reject missing or invalid tokens with `401 Unauthorized`.
- [x] Add user-scoped chat thread authorization.
- [x] Add database client construction in `app/database/supabase.py`.
- [x] Add tests for auth success, missing token, invalid token, and cross-user thread access.

## Phase 4 - Chat API Contract

- [x] Add `GET /chat/threads` to list the current user's threads.
- [x] Add `POST /chat/threads` to create a new thread.
- [x] Add `GET /chat/threads/{thread_id}/messages` to load message history.
- [x] Add `POST /chat/stream` with a stubbed assistant response.
- [x] Translate the frontend AI SDK message shape into internal backend models.
- [x] Stream text deltas over the backend-first SSE contract.
- [x] Persist the final user and assistant messages after a successful stubbed run.
- [x] Return useful errors for `401`, `403`, `404`, `422`, and upstream failures.

## Phase 5 - Frontend Foundation

- [x] Scaffold the Vite React TypeScript SPA in `frontend/`.
- [x] Add Tailwind CSS and shadcn/ui setup.
- [x] Add React Router.
- [x] Add `src/lib/env.ts` to validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`.
- [x] Add `src/lib/supabase.ts` for browser Supabase auth.
- [x] Add `src/lib/http.ts` for fetch, base URL handling, auth token injection, timeouts, and typed errors.
- [x] Add `src/lib/api.ts` for thread and message calls.
- [x] Add sign-in and sign-out screens for email auth.
- [x] Add authenticated route protection.
- [x] Verify with `pnpm tsc --noEmit` and `pnpm lint`.

## Phase 6 - Frontend Chat Experience

- [x] Add a thread list view.
- [x] Add a chat route for a selected thread.
- [x] Add message rendering for user and assistant messages.
- [x] Add streaming assistant response rendering.
- [x] Add loading, empty, error, and retry states.
- [x] Add citation chips on assistant messages.
- [x] Add a source passage panel or drawer that shows filing metadata and excerpt text.
- [x] Add clear unsupported-answer display for "not enough evidence" responses.
- [x] Keep the UI dense, calm, and analyst-oriented rather than marketing-like.

## Phase 7 - Ingestion Pipeline

- [ ] Review the existing SEC downloader in `data/download.py`.
- [ ] Define normalized source document metadata: company, ticker, filing type, filing date, fiscal year, accession number, source URL, page or section.
- [ ] Add Markdown or text extraction for downloaded SEC filings.
- [ ] Store normalized source documents in `source_documents`.
- [ ] Add chunking with stable chunk indexes and useful metadata.
- [ ] Generate embeddings with the configured OpenAI embedding model.
- [ ] Store chunks, embeddings, token counts, and full-text metadata in `document_chunks`.
- [ ] Make ingestion idempotent by accession number and chunk index.
- [ ] Add unit tests for parsing, metadata extraction, and chunking.

## Phase 8 - Retrieval

- [ ] Add semantic search over `document_chunks.embedding`.
- [ ] Add Postgres full-text search over `document_chunks.search_vector`.
- [ ] Add reciprocal rank fusion in Python.
- [ ] Fetch neighboring chunks when useful for context.
- [ ] Return typed `SourcePassage` records with complete citation metadata.
- [ ] Add retrieval tests with deterministic fake data.
- [ ] Evaluate retrieval quality against the 10 example questions in `docs/client-brief.md`.

## Phase 9 - Assistant And Grounding

- [ ] Add PydanticAI agent setup in `app/assistant/agent.py`.
- [ ] Add typed dependencies in `app/assistant/deps.py`.
- [ ] Add typed outputs for `GroundedAnswer`, `Citation`, and `SourcePassage`.
- [ ] Write assistant instructions that forbid unsupported claims, stock picks, and uncited facts.
- [ ] Add bounded retrieval tools such as `search_filings`, `read_chunk`, and `read_surrounding_chunks`.
- [ ] Add grounding validation that every citation maps to a retrieved passage.
- [ ] Return a controlled failure if citation validation fails.
- [ ] Add tests for citation validation, unsupported-answer refusal, and invalid citation rejection.

## Phase 10 - End-To-End Product Hardening

- [ ] Run the full local flow: sign in, create thread, ask question, stream answer, inspect citations.
- [ ] Test all 10 example analyst questions from the client brief.
- [ ] Confirm every answer cites filing and page or section metadata.
- [ ] Confirm unsupported questions refuse instead of guessing.
- [ ] Confirm users cannot read another user's threads.
- [ ] Confirm frontend handles expired auth sessions gracefully.
- [ ] Confirm backend logs enough context to debug failed chat turns without logging secrets.
- [ ] Confirm ingestion can be re-run without duplicate documents or chunks.

## Phase 11 - Deployment

- [ ] Add backend Railway start command.
- [ ] Add frontend Railway build and start configuration.
- [ ] Set backend env vars in Railway.
- [ ] Set frontend env vars in Railway.
- [ ] Configure Supabase auth redirect URLs for local and Railway frontend URLs.
- [ ] Apply production migrations.
- [ ] Run ingestion against the production Supabase database.
- [ ] Smoke test the deployed app with a pilot user account.

## Phase 12 - Client Acceptance

- [ ] Create a short analyst pilot script using the 10 questions from the brief.
- [ ] Add a feedback rubric for saved time, citation trust, answer usefulness, and missing-document cases.
- [ ] Track whether 5 senior analysts report at least 3 hours saved per analyst per week.
- [ ] Collect examples where answers were unsupported, incomplete, or hard to verify.
- [ ] Prioritize fixes before firm-wide rollout.

## Current Next Step

- [ ] Build Phase 7 next: ingestion pipeline for SEC filings.
