# Troubleshooting

## API does not start

- Confirm `backend/.venv` exists and `pip install -r backend/requirements.txt` completed.
- Start Uvicorn from `backend/` so `app.main:app` resolves and the default SQLite file is local to the backend.
- `/health` does not require Redis; `/health/ready` does. A 503 readiness response without Redis is expected in local SQLite-only mode.

## Frontend cannot reach API

- Keep FastAPI on port 8000 and Vite on 5173; Vite proxies `/api` and `/health` to the API.
- In Compose, use the Nginx frontend at 8080; its `/api/` location proxies to the backend service.

## Docker Compose fails

- Start Docker Desktop and switch to Linux containers. `docker compose config` validates configuration without a running engine.
- Copy `.env.example` to `.env`; Compose requires PostgreSQL variables and `SECRET_KEY`.
- Check `docker compose ps` and `docker compose logs backend postgres redis` after startup.

## Appointment time unavailable

- Choose an active doctor and service, configure business hours, and select a future date/time.
- Starts must align to five-minute intervals. The API rechecks reservation uniqueness transactionally; a competing booking returns HTTP 409.

## Known limitations

- No external LLM, telephony, STT, TTS, embedding, or SMS/WhatsApp/email sender is configured. The local AI is a small rule-based adapter; webhook ingestion only works after a secret is set.
- Knowledge retrieval is chunked lexical search, not a vector database or semantic RAG implementation.
- Notification records are queued in the database but there is no delivery worker or reminder scheduler.
- The permission model is coarse role checks; granular named permissions and role editing are not implemented.
- The rate limiter is per-process memory; Redis is provisioned/readiness-checked but not used for shared rate limiting or caching.
- Appointment availability follows business hours; individual doctor schedules, buffers, recurring slots, and appointment-duration overlap edge policies need domain review.
- Call summaries, advanced analytics, audit-event coverage, and production concurrency/retention testing remain to be implemented.
