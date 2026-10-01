# Voice Flow

The webhook contract accepts lifecycle events at `POST /api/v1/voice/webhook`. Set `VOICE_WEBHOOK_SECRET` and configure the provider to send the matching `X-Voice-Webhook-Secret`; without it the endpoint returns 503. Events are tenant-bound through the signed provider payload and an existing call cannot be moved between businesses.

Incoming lifecycle events create/update calls. Caller number, language, intent, event times, and transcript segments are persisted. Call records and transcripts are visible only within the owning business. Webhook authentication is currently a shared-secret header; use provider-signed timestamped HMAC requests and replay protection for production.

Provider protocols for telephony, STT, and TTS are defined in `backend/app/ai/providers.py`. A real call path still requires an adapter, streaming/session orchestration, interruption handling, retry policy, recording consent, data retention rules, and end-to-end provider tests. No phone number or external vendor is configured in this repository.
