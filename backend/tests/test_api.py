from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_database():
        database = test_sessions()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client: TestClient, email: str = "owner@example.com") -> tuple[dict, dict]:
    response = client.post("/api/v1/auth/register", json={
        "name": "Clinic Owner",
        "email": email,
        "password": "clinic-test-password-123",
        "business_name": "Greenfield Clinic",
    })
    assert response.status_code == 201, response.text
    tokens = response.json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


def make_booking_records(client: TestClient, headers: dict) -> tuple[int, int, int]:
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "Patient One", "phone": "+919876500001"})
    doctor = client.post("/api/v1/doctors", headers=headers, json={"name": "Dr. Ravi", "specialization": "Dermatology", "consultation_fee": 800})
    service = client.post("/api/v1/services", headers=headers, json={"name": "Consultation", "duration_minutes": 60, "price": 800})
    assert customer.status_code == doctor.status_code == service.status_code == 201
    return customer.json()["id"], doctor.json()["id"], service.json()["id"]


def test_health_and_registration_issue_tokens(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}
    tokens, headers = register(client)
    assert tokens["access_token"] and tokens["refresh_token"]
    assert client.get("/api/v1/auth/me", headers=headers).json()["email"] == "owner@example.com"


def test_refresh_rotates_token_and_rejects_reuse(client: TestClient):
    tokens, _ = register(client)
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


def test_business_data_is_tenant_scoped(client: TestClient):
    _, first_headers = register(client, "first@example.com")
    created = client.post("/api/v1/customers", headers=first_headers, json={"name": "Private Patient", "phone": "+919876500002"})
    _, second_headers = register(client, "second@example.com")
    assert client.get("/api/v1/customers", headers=second_headers).json() == []
    response = client.get(f"/api/v1/customers/{created.json()['id']}", headers=second_headers)
    assert response.status_code == 404


def test_tamil_english_and_tanglish_intents_and_safe_unknown(client: TestClient):
    _, headers = register(client)
    cases = [
        ("எனக்கு appointment வேண்டும்", "ta"),
        ("I want to book a dermatologist appointment", "en"),
        ("Enakku skin doctor appointment venum", "ta-en"),
    ]
    for message, language in cases:
        response = client.post("/api/v1/ai/message", headers=headers, json={"message": message})
        assert response.status_code == 200
        assert response.json()["language"] == language
        assert response.json()["intent"] == "BOOK_APPOINTMENT"
    unknown = client.post("/api/v1/ai/message", headers=headers, json={"message": "Is there parking nearby?"})
    assert unknown.json()["response"] == "I don't have that information right now. I can connect you with our staff."


def test_knowledge_is_business_scoped_chunked_and_used_for_answers(client: TestClient):
    _, headers = register(client)
    content = "Patients may use the free parking area behind the clinic entrance."
    saved = client.post("/api/v1/knowledge/documents", headers=headers, json={
        "title": "Parking information",
        "content": content,
        "category": "faq",
    })
    assert saved.status_code == 201, saved.text
    answer = client.get("/api/v1/knowledge/search", headers=headers, params={"q": "parking"})
    assert answer.status_code == 200 and answer.json()["answer"] == content
    _, other_headers = register(client, "other-owner@example.com")
    private_answer = client.get("/api/v1/knowledge/search", headers=other_headers, params={"q": "parking"})
    assert "don't have that information" in private_answer.json()["answer"]


def test_overlapping_appointments_conflict_and_cancel_releases_time(client: TestClient):
    _, headers = register(client)
    customer_id, doctor_id, service_id = make_booking_records(client, headers)
    starts_at = (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=10, minute=0, second=0, microsecond=0)
    payload = {"customer_id": customer_id, "doctor_id": doctor_id, "service_id": service_id, "starts_at": starts_at.isoformat()}
    first = client.post("/api/v1/appointments", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    duplicate = client.post("/api/v1/appointments", headers=headers, json=payload)
    assert duplicate.status_code == 409
    overlap_payload = {**payload, "starts_at": (starts_at + timedelta(minutes=30)).isoformat()}
    overlap = client.post("/api/v1/appointments", headers=headers, json=overlap_payload)
    assert overlap.status_code == 409
    cancelled = client.post(f"/api/v1/appointments/{first.json()['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    notification_events = client.get("/api/v1/notifications", headers=headers).json()
    assert {item["event_type"] for item in notification_events} >= {"APPOINTMENT_CONFIRMED", "APPOINTMENT_CANCELLED"}
    replacement = client.post("/api/v1/appointments", headers=headers, json=overlap_payload)
    assert replacement.status_code == 201, replacement.text


def test_reschedule_rejects_past_and_occupied_slots(client: TestClient):
    _, headers = register(client)
    customer_id, doctor_id, service_id = make_booking_records(client, headers)
    starts_at = (datetime.now(timezone.utc) + timedelta(days=12)).replace(hour=11, minute=0, second=0, microsecond=0)
    payload = {"customer_id": customer_id, "doctor_id": doctor_id, "service_id": service_id, "starts_at": starts_at.isoformat()}
    first = client.post("/api/v1/appointments", headers=headers, json=payload)
    second_payload = {**payload, "starts_at": (starts_at + timedelta(hours=2)).isoformat()}
    second = client.post("/api/v1/appointments", headers=headers, json=second_payload)
    assert first.status_code == second.status_code == 201
    busy = client.post(f"/api/v1/appointments/{second.json()['id']}/reschedule", headers=headers, json={"starts_at": starts_at.isoformat()})
    assert busy.status_code == 409
    past = client.post(f"/api/v1/appointments/{first.json()['id']}/reschedule", headers=headers, json={"starts_at": "2020-01-01T10:00:00+00:00"})
    assert past.status_code == 422


def test_invalid_doctor_and_timezone_are_rejected(client: TestClient):
    _, headers = register(client)
    customer_id, _, service_id = make_booking_records(client, headers)
    future = (datetime.now(timezone.utc) + timedelta(days=14)).replace(hour=9, minute=0, second=0, microsecond=0)
    payload = {"customer_id": customer_id, "doctor_id": 999, "service_id": service_id, "starts_at": future.isoformat()}
    assert client.post("/api/v1/appointments", headers=headers, json=payload).status_code == 404
    payload["doctor_id"] = 1
    payload["starts_at"] = future.replace(tzinfo=None).isoformat()
    assert client.post("/api/v1/appointments", headers=headers, json=payload).status_code == 422
