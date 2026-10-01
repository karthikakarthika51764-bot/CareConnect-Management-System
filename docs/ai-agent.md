# AI Agent

## Current behavior

The local assistant detects Tamil script, a small set of Tanglish markers, and English as a fallback. Intent classification is deterministic and limited to appointment booking, cancellation, rescheduling, pricing, timing, human handoff, and general questions. It is a development adapter, not an LLM.

FAQ retrieval is in `backend/app/services/rag.py`, outside the language/intent module. Documents are chunked on upload and retrieved with tenant-scoped lexical matching. The response is the saved chunk verbatim. If no matching evidence exists, the exact safe fallback is: “I don't have that information right now. I can connect you with our staff.”

Appointment intent asks for missing doctor/service/date context. Booking itself is carried out by the authenticated appointment API and validated service; a live multi-turn AI tool planner is not connected yet. The AI module has no direct ORM queries.

## Provider boundary

`backend/app/ai/providers.py` defines replaceable LLM, speech-to-text, text-to-speech, voice, and embedding protocols. No external provider is configured. Add a provider implementation behind these interfaces, retain server-side tenant authorization, and test tool arguments and results before enabling it for calls.

## Required production work

- Configure an LLM provider with structured tool calling and explicit JSON schemas.
- Add conversation state and idempotency keyed by call/session ID.
- Ground doctor/service/hours responses in verified service data.
- Require confirmation before appointment mutations and pass tool results back as authoritative facts.
- Evaluate Tamil/Tanglish utterances against a reviewed corpus; the current keyword rules are not adequate for production speech understanding.
