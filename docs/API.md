# API Reference

Base URL: `http://localhost:8000`. All versioned endpoints are under `/api/v1`.
Interactive docs (Swagger UI) are served at `/docs`.

Authentication is **JWT Bearer**. Obtain a token via `/auth/login`, then send
`Authorization: Bearer <access_token>`. Every response includes an `X-Request-ID` header for
log correlation.

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | Liveness. `{ "status": "ok", "version": "…" }` |
| GET | `/health/ready` | none | Readiness — checks DB connectivity (503 if down). |

## Auth — `/api/v1/auth`

### POST `/auth/register`
```json
{ "email": "user@example.com", "password": "at-least-8-chars" }
```
`201` → the created user. `409` if the email already exists.

### POST `/auth/login`
Form-encoded (OAuth2 password flow): `username=<email>&password=<password>`.
```json
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer" }
```
`401` on bad credentials.

### POST `/auth/refresh`
```json
{ "refresh_token": "…" }
```
Returns a fresh token pair. `401` if the refresh token is invalid/expired.

### GET `/auth/me`
Returns the current user. Requires a Bearer token.

## Documents — `/api/v1/documents`

### POST `/documents`
`multipart/form-data`:
- `file` — the PDF
- `method` — `text` | `ocr` | `vision` (default `text`)

`201` → a Document with `status: "processing"`. Ingestion runs in the background; poll the
list/detail endpoint until `status` becomes `ready` (or `error`).

Errors: `415` (not a PDF), `413` (too large), `422` (bad method).

```jsonc
// Document
{
  "id": "uuid", "filename": "report.pdf", "content_type": "application/pdf",
  "size_bytes": 12345, "extraction_method": "text", "status": "ready",
  "page_count": 3, "chunk_count": 12, "error": null,
  "created_at": "…", "updated_at": "…"
}
```

### GET `/documents`
List the current user's documents (newest first).

### GET `/documents/{id}`
A single document. `404` if not found or not owned by the caller.

### DELETE `/documents/{id}`
Deletes the document, its file, and its chunks (cascade). `204` on success.

## Query — `/api/v1/documents/{id}`

The document must be `ready`, else `409`.

### POST `/documents/{id}/query`
Non-streaming. Body:
```json
{ "question": "What is the total balance?", "top_k": 5 }
```
Response:
```jsonc
{
  "answer": "The total balance is … [p.2]",
  "provider": "anthropic", "model": "claude-sonnet-4-6",
  "sources": [{ "chunk_id": "uuid", "page_number": 2, "score": 0.83, "preview": "…" }],
  "input_tokens": 1234, "output_tokens": 210, "latency_ms": 1830
}
```

### POST `/documents/{id}/query/stream`
Same body; responds with **Server-Sent Events** (`text/event-stream`). Each `data:` line is a
JSON object with a `type`:

| `type` | Payload |
|---|---|
| `sources` | `{ "sources": [ { chunk_id, page_number, score, preview } ] }` (sent first) |
| `delta` | `{ "text": "partial answer…" }` (many) |
| `done` | `{ provider, model, input_tokens, output_tokens, latency_ms, answer_chars }` |
| `error` | `{ "detail": "…" }` |

> Use `fetch` + a stream reader (not `EventSource`) so you can send the `Authorization`
> header — see `frontend/lib/query.ts`.

## API-key access (optional)

If `API_KEYS` is configured, protected programmatic endpoints also accept an `X-API-Key`
header. Leave `API_KEYS` empty to disable this path entirely.
