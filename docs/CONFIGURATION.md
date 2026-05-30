# Configuration

All backend settings are environment variables, loaded by `app/core/config.py`
(`pydantic-settings`). For local dev put them in `backend/.env`; for Docker put them in the
root `.env` (consumed by `docker-compose.yml`). Frontend config lives in `frontend/.env.local`.

## Backend

### App
| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` \| `production` \| `test`. |
| `DEBUG` | `true` | Enables debug behaviour. |
| `API_V1_PREFIX` | `/api/v1` | Prefix for all versioned routes. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins. |

### Database
| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://docanalysis:docanalysis@localhost:5432/docanalysis` | SQLAlchemy URL (psycopg v3 driver). **Postgres + pgvector required.** |

### Auth / JWT
| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `change-me-...` | **Set a long random secret in production.** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh-token lifetime. |
| `API_KEYS` | _(empty)_ | Comma-separated keys enabling `X-API-Key` access. Empty disables it. |

### LLM providers
| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | _(empty)_ | Claude API key (primary provider). |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model id (vision-capable). |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key (fallback). If unset, fallback is disabled. |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model id (vision-capable). |
| `LLM_PRIMARY` | `anthropic` | `anthropic` \| `openai` — which provider is tried first. |
| `LLM_FALLBACK_ENABLED` | `true` | Try the other provider when the primary fails. |
| `LLM_MAX_TOKENS` | `2048` | Max output tokens per generation. |
| `LLM_TEMPERATURE` | `0.2` | Generation temperature. |

### Embeddings
| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name. |
| `EMBEDDING_DIM` | `384` | Vector dimension. **Must match the model and the `chunks.embedding` column** — changing it requires a new migration. |

### RAG
| Variable | Default | Description |
|---|---|---|
| `RETRIEVAL_TOP_K` | `5` | Chunks retrieved per question. |
| `CHUNK_SIZE` | `1000` | Max characters per chunk. |
| `CHUNK_OVERLAP` | `150` | Character overlap between chunks. |

### Extraction
| Variable | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `./data/uploads` | Where uploaded PDFs are stored. |
| `MAX_UPLOAD_MB` | `25` | Upload size limit. |
| `TESSERACT_CMD` | _(empty)_ | Path to the `tesseract` binary (OCR), if not on `PATH`. |
| `POPPLER_PATH` | _(empty)_ | Path to poppler `bin` (PDF rendering), if not on `PATH`. |
| `YOLO_ENABLED` | `true` | Run YOLOv8 layout detection before Tesseract in the OCR method. |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | Layout-detection weights (auto-downloaded if absent). |
| `OCR_DPI` | `200` | Render DPI for the OCR method. |
| `VISION_DPI` | `150` | Render DPI for the Vision method. |

### Logging
| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`. |
| `LOG_DIR` | `./logs` | Directory for `app.log` / `error.log`. |
| `LOG_JSON` | `false` | Emit structured JSON logs instead of console text. |

## Frontend
| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL. **Inlined at build time** — for Docker it is passed as a build arg. |
