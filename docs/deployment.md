# Deployment

## Docker Compose development

1. Copy `.env.example` to `.env` and change the local development values.
2. Start Docker Desktop (Linux containers) and run `docker compose up --build` from the repository root.
3. Open `http://localhost:8080`; the API is on port 8000. PostgreSQL and Redis are internal Compose services.
4. Stop with `docker compose down`. Persisted data is in named volumes; `docker compose down -v` removes it.

Compose health checks gate API startup on PostgreSQL and Redis. Nginx serves the SPA and proxies API requests to FastAPI. Development API startup creates tables. Production mode skips automatic table creation and should run `alembic upgrade head` before the API.

## Local development without Docker

Run FastAPI from `backend/` with its virtual environment and run Vite from `frontend/`. SQLite is the default database. `/health` checks process liveness; `/health/ready` checks database and Redis and therefore remains unavailable without a running Redis instance.

## Production checklist

- Build and scan pinned container images; run as non-root where supported.
- Supply managed PostgreSQL/Redis, TLS ingress, backups, retention, and restore drills.
- Set `ENVIRONMENT=production`, a high-entropy `SECRET_KEY`, strong database credentials, restricted `CORS_ORIGINS`, and a provider webhook secret through a secret manager.
- Apply explicit Alembic migrations; automatic development schema creation is disabled in production.
- Replace in-memory rate limiting with a shared gateway/Redis implementation; configure trusted proxy handling.
- Configure and verify LLM, telephony, speech, and notification adapters before enabling patient calls.
- Add audit-event coverage, access reviews, incident response, monitoring, and privacy/consent retention controls.

CI runs API tests, frontend lint/tests/build, and container builds. It does not deploy automatically.
