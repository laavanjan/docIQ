# Development Guide

## Prerequisites
- Python 3.11
- Node 20
- PostgreSQL 16 with the `pgvector` extension (easiest: `docker compose up -d postgres`)
- For the **OCR** method outside Docker: Tesseract and poppler on `PATH`

## Backend setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env              # set ANTHROPIC_API_KEY, DATABASE_URL, JWT_SECRET
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs.

## Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                       # http://localhost:3000
```

## Project layout (backend)

```
app/
├── main.py            # app factory, middleware (request-id + access log), router mount
├── core/              # config, logging, security (JWT), request context, deps
├── api/routes/        # auth, documents, query, health
├── models/            # SQLAlchemy: User, Document, Chunk (pgvector), QueryLog
├── schemas/           # Pydantic request/response DTOs
└── services/
    ├── extraction/    # text / ocr (YOLO+Tesseract) / vision + factory
    ├── llm/           # provider interface + Anthropic/OpenAI + router
    ├── chunking.py  embeddings.py  vectorstore.py  rag.py  pipeline.py
```

Architectural conventions:
- **Routes are thin** — they validate, call a service, and shape the response. Logic lives in
  `services/`.
- **Services log structured events** via `log_event(...)` (see [LOGGING.md](LOGGING.md)).
- **Heavy/optional imports are lazy** (ultralytics, fastembed, anthropic, openai, pdf2image)
  so importing a module never forces those dependencies until used.

## Database migrations (Alembic)

```bash
cd backend
alembic upgrade head                          # apply
alembic revision --autogenerate -m "message"  # create after model changes
alembic downgrade -1                           # roll back one
```

The initial migration creates the `vector` extension, all tables, and the HNSW cosine index on
`chunks.embedding`. **Changing `EMBEDDING_DIM`** (i.e. switching to an embedding model with a
different dimension) requires a new migration altering that column.

## Testing

```bash
cd backend
pytest                 # unit tests always run; DB tests auto-skip without Postgres
ruff check .           # lint
ruff check . --fix     # autofix
```

- **Unit tests** (`test_chunking.py`, `test_llm_router.py`) need no DB or network — the LLM
  providers are faked.
- **DB tests** (`test_health.py`, `test_auth.py`) depend on the `db_required` fixture and run
  only when `DATABASE_URL` is reachable (always true in CI, which provides a pgvector service).

## Frontend checks

```bash
cd frontend
npm run lint
npm run build          # type-check + production build
```

## Swapping models

- **LLM**: change `ANTHROPIC_MODEL` / `OPENAI_MODEL`, or flip `LLM_PRIMARY`. Add a new provider
  by implementing the `LLMProvider` interface in `services/llm/` and registering it in the
  router.
- **Embeddings**: change `EMBEDDING_MODEL` (+ `EMBEDDING_DIM` and a migration if the dimension
  differs). The `Embedder` interface in `services/embeddings.py` is the only thing a hosted
  embedder (e.g. Voyage) would need to satisfy.
