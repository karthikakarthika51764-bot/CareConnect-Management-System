from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Appointment, Customer, Notification


class SMSProvider(Protocol):
    def send_sms(self, recipient: str, message: str) -> str: ...


class WhatsAppProvider(Protocol):
    def send_whatsapp(self, recipient: str, message: str) -> str: ...


class EmailProvider(Protocol):
    def send_email(self, recipient: str, subject: str, message: str) -> str: ...


def queue_appointment_notification(database: Session, appointment: Appointment, event_type: str) -> Notification | None:
    customer = database.get(Customer, appointment.customer_id)
    if customer is None or not customer.phone:
        return None
    notification = Notification(
        business_id=appointment.business_id,
        customer_id=customer.id,
        channel="sms",
        recipient=customer.phone,
        event_type=event_type,
        payload={"appointment_id": appointment.id, "starts_at": appointment.starts_at.isoformat(), "status": appointment.status},
        status="QUEUED",
    )
    database.add(notification)
    return notification
