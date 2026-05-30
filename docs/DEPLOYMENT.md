# Deployment

## Docker Compose (recommended)

```bash
cp .env.example .env        # set ANTHROPIC_API_KEY, JWT_SECRET, (optional) OPENAI_API_KEY
docker compose up --build
```

Services: postgres (pgvector), backend (FastAPI), frontend (Next.js).

- Frontend → http://localhost:3000
- Backend → http://localhost:8000 (`/docs`)
- The backend entrypoint runs `alembic upgrade head` before starting Uvicorn.
- The backend image bundles **Tesseract + poppler + OpenCV libs**, so OCR and Vision work with
  no host installs.

### Volumes
| Volume | Purpose |
|---|---|
| `pgdata` | Postgres data |
| `uploads` | uploaded PDFs |
| `logs` | `app.log` / `error.log` |
| `model_cache` | fastembed + YOLO + HF downloads (first-run cache) |

### Notes
- `NEXT_PUBLIC_API_URL` is **build-time** for the frontend (passed as a build arg in compose).
  If you deploy the backend at a different origin, rebuild the frontend with that URL.
- First request that uses the OCR/embedding/YOLO models downloads weights into `model_cache`;
  subsequent runs are fast.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR:
- **backend** — `ruff check`, `alembic upgrade head`, `pytest` against a `pgvector/pgvector:pg16`
  service container.
- **frontend** — `npm run lint` and `npm run build`.

Extend this with a deploy job (build & push images to a registry, then deploy) once a target
environment is chosen.

## Production hardening checklist

- [ ] Set a strong, unique `JWT_SECRET` (and rotate periodically).
- [ ] Use managed Postgres with `pgvector`; set `DATABASE_URL` accordingly and keep backups.
- [ ] Restrict `CORS_ORIGINS` to your real frontend origin(s).
- [ ] Terminate TLS at a reverse proxy (nginx/Caddy/cloud LB) in front of both services.
- [ ] Set `ENVIRONMENT=production`, `DEBUG=false`, and consider `LOG_JSON=true` for log shipping.
- [ ] Put uploads on durable/object storage (or a backed-up volume) rather than container disk.
- [ ] Add rate limiting / a WAF at the edge; consider `API_KEYS` for programmatic access.
- [ ] Set provider spend limits and monitor `query_logs` for token usage.
- [ ] Run more than one backend worker/replica; ingestion background tasks scale with replicas.
- [ ] Store secrets in a secret manager, not in `.env` committed anywhere.

## Scaling considerations

- **Ingestion** is CPU-bound (OCR/embeddings) — scale backend replicas or move processing to a
  dedicated worker queue (e.g. Celery/RQ) if upload volume grows.
- **Retrieval** uses an HNSW index; tune `m` / `ef_construction` (in the migration) and
  `RETRIEVAL_TOP_K` for your corpus size.
- **Vision extraction** cost scales with pages × image tokens — prefer Text/OCR when the PDF has
  selectable text.
