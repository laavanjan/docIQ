# Architecture

This document describes the system design of the Document Analysis Platform: its components,
data flow, data model, and the key decisions behind them.

## Overview

The platform is a two-tier application — a **Next.js** frontend and a **FastAPI** backend —
backed by a single **PostgreSQL + pgvector** datastore. Document content and its vector
embeddings live together in Postgres; the LLM layer is provider-agnostic with Claude as the
primary and OpenAI as an automatic fallback.

![System overview](docs/diagrams/overview.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
graph TB
    subgraph Client
        UI["Next.js (App Router, Tailwind)"]
    end
    subgraph Server["FastAPI backend"]
        API["REST API + SSE<br/>auth · documents · query"]
        PIPE["Ingestion pipeline<br/>extract → chunk → embed → store"]
        RAG["RAG service<br/>retrieve → prompt → generate"]
        LLM["LLM Router<br/>Claude → OpenAI fallback"]
        EMB["Embeddings<br/>fastembed (local, ONNX)"]
    end
    subgraph Data
        PG[("PostgreSQL + pgvector<br/>users · documents · chunks · query_logs")]
        FS["File storage<br/>uploaded PDFs"]
    end
    subgraph External
        ANTHROPIC["Anthropic API"]
        OPENAI["OpenAI API"]
    end

    UI -- "JSON / multipart / SSE" --> API
    API --> PIPE
    API --> RAG
    PIPE --> EMB
    PIPE --> FS
    PIPE --> PG
    RAG --> EMB
    RAG --> PG
    RAG --> LLM
    PIPE -. "vision method" .-> LLM
    LLM --> ANTHROPIC
    LLM --> OPENAI
```

</details>

## Components

### Frontend (`frontend/`)
- **App Router pages**: `login`, `register`, `documents` (upload + list), `chat/[docId]`.
- **`AuthContext`** holds the user/session; the access token is stored in `localStorage` and
  attached by the API client, which transparently refreshes on `401`.
- **`UploadForm` + `ExtractionMethodPicker`** let the user choose Text / OCR / Vision per upload.
- **`ChatPanel`** consumes the answer **SSE stream** (via `fetch`, so it can send the auth
  header), rendering tokens as they arrive plus a Sources panel and the answering provider.

### Backend (`backend/app/`)
- **`api/routes/`** — `auth`, `documents`, `query` (+ `health`). Thin controllers; logic lives
  in services.
- **`services/extraction/`** — `TextExtractor` (PyMuPDF), `OCRExtractor` (poppler → YOLO layout
  → Tesseract), `VisionExtractor` (page image → LLM), selected by `factory.get_extractor`.
- **`services/chunking.py`** — per-page recursive character chunker with overlap.
- **`services/embeddings.py`** — local `fastembed` model (`bge-small-en-v1.5`, 384-dim).
- **`services/vectorstore.py`** — pgvector insert + cosine-distance top-k search.
- **`services/llm/`** — `LLMProvider` interface, `AnthropicProvider`, `OpenAIProvider`, and the
  `LLMRouter` that does primary→fallback for both `complete()` and `stream()`.
- **`services/rag.py`** — orchestrates retrieval + generation, persists a `QueryLog`.
- **`services/pipeline.py`** — end-to-end ingestion, run as a background task.
- **`core/`** — settings, logging, request-id context, JWT/password security, dependencies.

## Ingestion flow

![Ingestion flow](docs/diagrams/ingestion.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant BG as Background task
    participant EX as Extractor
    participant EMB as Embeddings
    participant PG as Postgres+pgvector

    User->>FE: choose PDF + method, submit
    FE->>API: POST /documents (file, method)
    API->>PG: insert Document(status=processing)
    API-->>FE: 201 Document
    API->>BG: schedule process_document(id, request_id)
    BG->>EX: extract(file) [text | ocr(YOLO+Tesseract) | vision(LLM)]
    EX-->>BG: pages[]
    BG->>BG: chunk pages
    BG->>EMB: embed_documents(chunks)
    EMB-->>BG: vectors[]
    BG->>PG: bulk insert chunks (+embeddings)
    BG->>PG: update Document(status=ready, counts)
    FE->>API: GET /documents (poll)
    API-->>FE: status=ready
```

</details>

## Query (RAG) flow

![Query (RAG) flow](docs/diagrams/query.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant RAG as RAG service
    participant EMB as Embeddings
    participant PG as Postgres+pgvector
    participant LLM as LLM Router

    User->>FE: ask question
    FE->>API: POST /documents/{id}/query/stream (SSE)
    API->>RAG: answer_stream(document, question)
    RAG->>EMB: embed_query(question)
    RAG->>PG: top-k nearest chunks (cosine)
    PG-->>RAG: chunks + scores
    API-->>FE: event: sources
    RAG->>LLM: stream(system, context+question)
    LLM->>LLM: try Claude → fallback OpenAI on failure
    loop tokens
        LLM-->>RAG: delta
        API-->>FE: event: delta
    end
    RAG->>PG: insert QueryLog(provider, tokens, latency)
    API-->>FE: event: done (provider, usage)
```

</details>

## Data model

![Data model](docs/diagrams/data-model.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : owns
    DOCUMENTS ||--o{ CHUNKS : "split into"
    USERS ||--o{ QUERY_LOGS : asks
    DOCUMENTS ||--o{ QUERY_LOGS : "queried in"

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        bool is_active
        timestamptz created_at
    }
    DOCUMENTS {
        uuid id PK
        uuid owner_id FK
        string filename
        string extraction_method
        string status
        int page_count
        int chunk_count
        text error
    }
    CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid owner_id
        int chunk_index
        int page_number
        text content
        vector embedding "VECTOR(384), HNSW cosine index"
        jsonb meta
    }
    QUERY_LOGS {
        uuid id PK
        uuid owner_id
        uuid document_id
        text question
        string provider_used
        int input_tokens
        int output_tokens
        int latency_ms
    }
```

</details>

Retrieval is a single indexed query:

```sql
SELECT * FROM chunks
WHERE owner_id = :owner AND document_id = :doc
ORDER BY embedding <=> :query_embedding   -- cosine distance, HNSW index
LIMIT :k;
```

## Deployment (containers)

![Deployment (containers)](docs/diagrams/deployment.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
graph LR
    browser["Browser"] -->|":3000"| fe["frontend<br/>node:20"]
    browser -->|":8000"| be["backend<br/>python:3.11 + tesseract + poppler"]
    be -->|":5432"| db[("postgres<br/>pgvector/pgvector:pg16")]
    be --> ext["Anthropic / OpenAI APIs"]
    db --- v1[("volume: pgdata")]
    be --- v2[("volumes: uploads, logs, model_cache")]
```

</details>

## Key design decisions

- **Postgres + pgvector instead of a separate vector DB.** Chunks (the relational source of
  truth) and their embeddings live in one store, so there's no second system to keep in sync.
  An HNSW index gives fast approximate cosine search.
- **Local embeddings (fastembed/ONNX).** Anthropic has no embeddings endpoint, so RAG would
  otherwise need a third provider. fastembed runs on CPU, needs no API key, and avoids a torch
  dependency. The `embeddings.py` interface makes swapping in a hosted embedder (e.g. Voyage)
  straightforward — the embedding dimension is the only migration-sensitive part.
- **Provider-agnostic LLM with automatic fallback.** One `LLMProvider` interface plus a router
  means Claude is primary and OpenAI takes over on error/rate-limit. Streaming only falls back
  *before* the first token, so a client never sees a torn answer.
- **Three explicit extraction methods.** Different documents need different handling; exposing
  the choice (Text/OCR/Vision) in the UI keeps the trade-off (speed vs. robustness vs. cost)
  with the user. OCR reuses the original project's YOLO layout-analysis idea.
- **Ingestion off the request path.** Extraction/embedding can be slow, so uploads return
  immediately and processing runs as a background task that records success/failure on the row.
- **Correlation-id logging end to end.** Every request gets an id that is attached to all logs
  (including the background ingestion task) and returned as `X-Request-ID` — see
  [docs/LOGGING.md](docs/LOGGING.md).
