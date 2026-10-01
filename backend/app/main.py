import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.api import auth, business, communications, knowledge, operations
from app.core.config import settings
from app.db import Base, engine
from app import models  # noqa: F401


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"time": self.formatTime(record), "level": record.levelname, "message": record.getMessage(), **getattr(record, "fields", {})})


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()], force=True)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())
logger = logging.getLogger("careconnect")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "production" and settings.secret_key.startswith("dev-only"):
        raise RuntimeError("SECRET_KEY must be configured outside development")
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Voice-Webhook-Secret"])

rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    incoming_id = request.headers.get("x-request-id", "")
    request_id = incoming_id if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", incoming_id) else str(uuid.uuid4())
    request.state.request_id = request_id
    if request.url.path not in {"/health", "/health/ready"}:
        now = time.monotonic()
        client = request.client.host if request.client else "unknown"
        bucket = rate_buckets[client]
        while bucket and now - bucket[0] >= 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded", "request_id": request_id}, headers={"X-Request-ID": request_id})
        bucket.append(now)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", extra={"fields": {"request_id": request_id, "path": request.url.path}})
        response = JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    logger.info("http_request", extra={"fields": {"request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "duration_ms": round((time.monotonic() - started) * 1000, 2)}})
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.4, socket_timeout=0.4)
        redis_ok = bool(redis_client.ping())
        redis_client.close()
    except Exception:
        redis_ok = False
    if not database_ok or not redis_ok:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": database_ok, "redis": redis_ok})
    return {"status": "ready", "database": True, "redis": True}


for route_group in (auth.router, business.router, operations.router, knowledge.router, communications.router):
    app.include_router(route_group)
