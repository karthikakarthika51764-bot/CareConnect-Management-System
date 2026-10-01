# Testing

## Backend

`backend/tests/test_api.py` uses isolated SQLite and FastAPI dependency overrides. Coverage includes health/registration, refresh replay protection, tenant isolation, Tamil/English/Tanglish intent classification, safe unknown answers, knowledge visibility, appointment duplicate/overlap prevention, cancellation and slot release, reschedule conflicts, invalid doctor, and missing timezone.

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Frontend

Vitest, jsdom, and Testing Library render the metric-card component. Run from `frontend/` with `npm test -- --run`. `npm run build` performs strict TypeScript checking before bundling. `npm run lint` runs Oxlint.

## Coverage still needed

Add integration tests for Postgres concurrency, Redis-backed rate limiting, role/permission matrices, doctor/service update routes, hours/holiday availability, voice webhook signatures and lifecycle, provider failure, notification worker delivery, frontend booking/auth forms, accessibility, and end-to-end browser workflows. Current tests do not certify production integrations.
