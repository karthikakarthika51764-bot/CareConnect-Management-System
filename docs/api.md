# API

Base prefix: `/api/v1`. JSON is used for request/response bodies. Protected routes require `Authorization: Bearer <access_token>`. Errors return a JSON `detail`; API requests include an `X-Request-ID` response header.

## Authentication

- `POST /auth/register` creates a clinic and `BUSINESS_OWNER`; body: name, email, password (10+ characters), business_name.
- `POST /auth/login` returns access and refresh tokens.
- `POST /auth/refresh` rotates a refresh token; replaying a used refresh token is rejected.
- `POST /auth/logout` revokes the refresh token.
- `GET /auth/me` returns the server-resolved user.

## Business and team

- `GET|PUT /business`
- `GET|PUT /business/hours`
- `GET|POST /business/holidays`
- `GET|POST /staff`

## Clinic operations

- `GET|POST /customers`; `GET|PATCH /customers/{id}`; `GET /customers/{id}/history`
- `GET|POST /doctors`; `GET|PUT /doctors/{id}`
- `GET|POST /services`; `GET|PUT /services/{id}`
- `GET /appointments`; `GET /appointments/availability?doctor_id=&service_id=&on_date=`
- `POST /appointments`; `GET /appointments/{id}`; `POST /appointments/{id}/cancel`; `POST /appointments/{id}/reschedule`
- `GET|POST /leads`
- `GET|POST /follow-ups`
- `GET /dashboard/summary`

## Knowledge and AI

- `POST|GET /knowledge/documents`; `DELETE /knowledge/documents/{id}`
- `GET /knowledge/search?q=...`
- `POST /ai/message` accepts `{ "message": "...", "call_id": null }` and returns language, rule-based intent, response, and handoff state.

## Calls and handoff

- `GET /calls`; `GET /calls/{id}` returns the call and transcript.
- `GET /escalations`; `POST /escalations`; `PATCH /escalations/{id}?status=RESOLVED`
- `GET /notifications` returns tenant-scoped queued outbox events.
- `POST /voice/webhook` requires `X-Voice-Webhook-Secret` and `call_id`, `business_id`, `event`; accepted events are CALL_STARTED, CALL_ACTIVE, CALL_ENDED, CALL_FAILED.

Operational writes validate tenant ownership in the API and database service. Interactive schemas are available at `/docs` in development mode.
