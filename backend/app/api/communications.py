import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agent import handle_message
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.db import get_db
from app.models import Business, Call, CallTranscript, Customer, Escalation, Notification, User
from app.schemas import AIMessageRequest, AIMessageResponse, VoiceWebhook
from app.services.rag import rag_service

router = APIRouter(prefix="/api/v1", tags=["calls and AI"])


@router.get("/calls")
def list_calls(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Call).where(Call.business_id == user.business_id).order_by(Call.started_at.desc()).limit(250)).all()


@router.get("/calls/{call_id}")
def get_call(call_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    call = database.scalar(select(Call).where(Call.id == call_id, Call.business_id == user.business_id))
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    transcript = database.scalars(select(CallTranscript).where(CallTranscript.call_id == call.id).order_by(CallTranscript.created_at)).all()
    return {"call": call, "transcript": transcript}


@router.get("/escalations")
def list_escalations(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Escalation).where(Escalation.business_id == user.business_id).order_by(Escalation.created_at.desc())).all()


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Notification).where(Notification.business_id == user.business_id).order_by(Notification.created_at.desc()).limit(250)).all()


@router.post("/escalations", status_code=201)
def create_escalation(reason: str, priority: str = "normal", call_id: int | None = None, customer_id: int | None = None, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    if priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(status_code=422, detail="Invalid escalation priority")
    if call_id is not None and database.scalar(select(Call.id).where(Call.id == call_id, Call.business_id == user.business_id)) is None:
        raise HTTPException(status_code=404, detail="Call not found")
    if customer_id is not None and database.scalar(select(Customer.id).where(Customer.id == customer_id, Customer.business_id == user.business_id)) is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    escalation = Escalation(business_id=user.business_id, call_id=call_id, customer_id=customer_id, reason=reason[:300], priority=priority)
    database.add(escalation)
    database.commit()
    database.refresh(escalation)
    return escalation


@router.patch("/escalations/{escalation_id}")
def update_escalation(escalation_id: int, status: str, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    if status not in {"OPEN", "IN_PROGRESS", "RESOLVED"}:
        raise HTTPException(status_code=422, detail="Invalid escalation status")
    escalation = database.scalar(select(Escalation).where(Escalation.id == escalation_id, Escalation.business_id == user.business_id))
    if escalation is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    escalation.status = status
    escalation.resolved_at = datetime.now(timezone.utc) if status == "RESOLVED" else None
    database.commit()
    database.refresh(escalation)
    return escalation


@router.post("/ai/message", response_model=AIMessageResponse)
def ai_message(payload: AIMessageRequest, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    if user.business_id is None:
        raise HTTPException(status_code=403, detail="Business access is required")
    call = None
    if payload.call_id is not None:
        call = database.scalar(select(Call).where(Call.id == payload.call_id, Call.business_id == user.business_id))
        if call is None:
            raise HTTPException(status_code=404, detail="Call not found")
        database.add(CallTranscript(call_id=call.id, speaker="customer", text=payload.message))
    knowledge_answer = rag_service.answer(database, user.business_id, payload.message)
    language, intent, response, handoff = handle_message(payload.message, knowledge_answer)
    if call:
        call.language = language
        call.detected_intent = intent
        database.add(CallTranscript(call_id=call.id, speaker="assistant", text=response, language=language))
    if handoff:
        database.add(Escalation(business_id=user.business_id, call_id=call.id if call else None, reason="Customer requested human assistance", priority="high"))
    database.commit()
    return AIMessageResponse(language=language, intent=intent, response=response, handoff=handoff)


@router.post("/voice/webhook", status_code=202)
def voice_webhook(payload: VoiceWebhook, x_voice_webhook_secret: str | None = Header(default=None), database: Session = Depends(get_db)):
    if not settings.voice_webhook_secret:
        raise HTTPException(status_code=503, detail="Voice webhook is disabled until a provider secret is configured")
    if x_voice_webhook_secret is None or not hmac.compare_digest(x_voice_webhook_secret, settings.voice_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid voice webhook signature")
    if database.get(Business, payload.business_id) is None:
        raise HTTPException(status_code=404, detail="Business not found")
    allowed_events = {"CALL_STARTED", "CALL_ACTIVE", "CALL_ENDED", "CALL_FAILED"}
    if payload.event not in allowed_events:
        raise HTTPException(status_code=422, detail="Unsupported call event")
    call = database.scalar(select(Call).where(Call.provider_call_id == payload.call_id))
    if call is None:
        call = Call(business_id=payload.business_id, provider_call_id=payload.call_id, caller_number=payload.caller_number)
        database.add(call)
        database.flush()
    elif call.business_id != payload.business_id:
        raise HTTPException(status_code=409, detail="Call does not belong to this business")
    call.status = payload.event
    call.language = payload.language or call.language
    call.detected_intent = payload.intent or call.detected_intent
    if payload.event in {"CALL_ENDED", "CALL_FAILED"}:
        call.ended_at = datetime.now(timezone.utc)
    if payload.transcript:
        database.add(CallTranscript(call_id=call.id, speaker="customer", text=payload.transcript, language=payload.language))
    database.commit()
    return {"call_id": call.id, "status": call.status}
