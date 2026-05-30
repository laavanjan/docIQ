# Logging

Logging is configured centrally in `app/core/logging_config.py` and is designed so any line —
including those from the background ingestion task — can be traced back to the request that
caused it.

## Sinks

`configure_logging()` (called at import time in `app/main.py`) sets up three handlers:

| Handler | Destination | Level |
|---|---|---|
| console | stdout | `LOG_LEVEL` |
| `file_app` | `logs/app.log` (rotating, 10 MB × 5) | `LOG_LEVEL` |
| `file_error` | `logs/error.log` (rotating, 10 MB × 5) | `ERROR` |

Set `LOG_JSON=true` to switch every sink to single-line JSON (for log shippers/ELK). Set
`LOG_DIR` to relocate the files and `LOG_LEVEL` (e.g. `DEBUG`) to change verbosity.

## Request correlation

A middleware in `app/main.py` assigns each request a `request_id` (or reuses an inbound
`X-Request-ID`), stores it in a `contextvar` (`app/core/request_context.py`), and returns it as
the `X-Request-ID` response header. A logging `Filter` stamps `request_id` (and `user_id`) onto
**every** record, so the whole lifecycle of a request shares one id.

Because ingestion runs in a background task (separate context), the originating `request_id`
is passed into `process_document(...)` and re-applied — so upload and its asynchronous
processing share the same id.

Console format:
```
2026-05-30 14:03:11 | INFO     | req=ab12…  user=…  | app.services.rag | rag.answer event=rag.answer provider=anthropic ms=1830
```

## Structured pipeline events

The `log_event(logger, "name", **fields)` helper emits consistent, greppable events. Key ones:

| Event | Where | Notable fields |
|---|---|---|
| `request.start` / `request.end` | middleware | `method`, `path`, `status`, `duration_ms` |
| `ingest.start` / `ingest.done` | pipeline | `document_id`, `pages`, `chunks`, `ms` |
| `extract.done` | extractors | `method`, `pages`, `chars`, `yolo_regions`, `ms` |
| `chunk.done` | chunker | `chunks`, `size`, `overlap` |
| `embed.documents` | embeddings | `count`, `dim`, `ms` |
| `vectorstore.upsert` / `vectorstore.search` | vectorstore | `rows` / `k`, `hits`, `top_score`, `ms` |
| `llm.complete` / `llm.stream` | LLM router | `provider`, `model`, `fallback`, token counts |
| `llm.provider_failed` | LLM router | `provider`, `error`, `will_fallback` (WARNING) |
| `rag.answer` | RAG | `provider`, `sources`, `input_tokens`, `output_tokens`, `ms` |

## Tracing a request

1. Make a request; read the `X-Request-ID` from the response (the UI also logs to the console).
2. Grep the logs for it:
   ```bash
   grep ab12cd34 backend/logs/app.log
   ```
   You'll see the full chain — `request.start` → retrieval → `llm.*` → `rag.answer` →
   `request.end` — in order, plus any fallback events.
3. Errors (with full tracebacks) are isolated in `logs/error.log`, each tagged with its id; the
   client receives the same id in the error body so support can correlate it.

## Token usage & cost

Every answer writes a `query_logs` row (`provider_used`, `model`, `input_tokens`,
`output_tokens`, `latency_ms`) and a matching `rag.answer` log line — useful for auditing usage
and estimating spend per user/document.
