Set-Location "C:\Users\laavanjan\Desktop\Project\document-analysis"

git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    git remote add origin https://github.com/laavanjan/docIQ.git
    Write-Host "Remote added."
} else {
    Write-Host "Remote already set."
}

# 1
git add .gitignore .env.example
git commit -m "chore: initial repo setup - gitignore and env example"

# 2
git add Makefile docker-compose.yml
git commit -m "chore: add Makefile and docker-compose orchestration"

# 3
git add README.md ARCHITECTURE.md
git commit -m "docs: add README and architecture overview"

# 4
git add .github/
git commit -m "ci: add GitHub Actions workflow"

# 5
git add backend/.dockerignore backend/Dockerfile backend/.env.example
git commit -m "chore(backend): add Dockerfile and dockerignore"

# 6
git add backend/pyproject.toml backend/alembic.ini backend/requirements.txt backend/requirements-dev.txt
git commit -m "chore(backend): add pyproject, alembic config and requirements"

# 7
git add backend/app/__init__.py backend/app/main.py
git commit -m "feat(backend): add FastAPI app entry point"

# 8
git add backend/app/core/
git commit -m "feat(backend): add core config, security, deps and logging"

# 9
git add backend/app/db/
git commit -m "feat(backend): add database session and base setup"

# 10
git add backend/app/models/user.py backend/app/models/__init__.py backend/app/models/constants.py
git commit -m "feat(backend): add user model and constants"

# 11
git add backend/app/models/document.py
git commit -m "feat(backend): add document model"

# 12
git add backend/app/models/chunk.py backend/app/models/document_image.py backend/app/models/query_log.py
git commit -m "feat(backend): add chunk, document image and query log models"

# 13
git add backend/app/schemas/
git commit -m "feat(backend): add Pydantic schemas for auth, documents and query"

# 14
git add backend/app/api/__init__.py backend/app/api/router.py backend/app/api/routes/health.py backend/app/api/routes/__init__.py
git commit -m "feat(backend): add API router and health check route"

# 15
git add backend/app/api/routes/auth.py
git commit -m "feat(backend): add authentication routes"

# 16
git add backend/app/api/routes/documents.py
git commit -m "feat(backend): add document upload and management routes"

# 17
git add backend/app/api/routes/query.py
git commit -m "feat(backend): add RAG query routes"

# 18
git add backend/app/services/llm/
git commit -m "feat(backend): add LLM router with Anthropic and OpenAI providers"

# 19
git add backend/app/services/extraction/
git commit -m "feat(backend): add document extraction - text, OCR, vision, layout"

# 20
git add backend/app/services/chunking.py backend/app/services/embeddings.py backend/app/services/__init__.py
git commit -m "feat(backend): add text chunking and embedding service"

# 21
git add backend/app/services/vectorstore.py backend/app/services/images.py backend/app/services/pipeline.py
git commit -m "feat(backend): add vector store, image service and ingestion pipeline"

# 22
git add backend/app/services/rag.py
git commit -m "feat(backend): add RAG query service with pgvector retrieval"

# 23
git add backend/alembic/
git commit -m "chore(backend): add Alembic migration environment and scripts"

# 24
git add backend/tests/
git commit -m "test(backend): add tests for auth, chunking, health and LLM router"

# 25
git add samples/
git commit -m "chore: add sample bank statement documents"

# 26
git add docs/
git commit -m "docs: add API, deployment, configuration and architecture diagrams"

# 27
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/next.config.mjs frontend/tailwind.config.ts frontend/postcss.config.mjs frontend/.eslintrc.json frontend/next-env.d.ts
git commit -m "chore(frontend): add Next.js config, Tailwind and TypeScript setup"

# 28
git add frontend/Dockerfile frontend/.dockerignore frontend/.env.local.example
git commit -m "chore(frontend): add frontend Dockerfile and env example"

# 29
git add frontend/app/ frontend/public/
git commit -m "feat(frontend): add app pages - chat, documents, login, register"

# 30
git add frontend/components/ frontend/lib/ frontend/context/
git commit -m "feat(frontend): add UI components, API lib, auth context and helpers"

Write-Host "All 30 commits created. Pushing to GitHub..."
git push -u origin main
Write-Host "Done! https://github.com/laavanjan/docIQ"
