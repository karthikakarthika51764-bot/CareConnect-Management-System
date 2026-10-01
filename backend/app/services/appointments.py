from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentSlot, Business, BusinessHour, Customer, Doctor, Holiday, Service


ACTIVE_STATUSES = {"PENDING", "CONFIRMED"}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(status_code=422, detail="Appointment time must include a timezone")
    normalized = value.astimezone(timezone.utc)
    if normalized.second or normalized.microsecond or normalized.minute % 15:
        raise HTTPException(status_code=422, detail="Appointment time must align to a fifteen-minute slot")
    return normalized


def _reservation_rows(appointment: Appointment) -> list[AppointmentSlot]:
    slots = []
    current = appointment.starts_at
    while current < appointment.ends_at:
        slots.append(AppointmentSlot(appointment_id=appointment.id, doctor_id=appointment.doctor_id, slot_at=current))
        current += timedelta(minutes=5)
    return slots


def validate_business_window(database: Session, business_id: int, starts_at: datetime, duration_minutes: int) -> None:
    business = database.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    local_start = starts_at.astimezone(ZoneInfo(business.timezone))
    local_end = (starts_at + timedelta(minutes=duration_minutes)).astimezone(ZoneInfo(business.timezone))
    if local_start.date() != local_end.date():
        raise HTTPException(status_code=422, detail="Appointment must fit within one business day")
    if database.scalar(select(Holiday.id).where(Holiday.business_id == business_id, Holiday.holiday_date == local_start.date())):
        raise HTTPException(status_code=422, detail="The clinic is closed on this date")
    hours = database.scalar(select(BusinessHour).where(BusinessHour.business_id == business_id, BusinessHour.day_of_week == local_start.weekday()))
    if hours is not None and hours.is_closed:
        raise HTTPException(status_code=422, detail="The clinic is closed on this day")
    opens_at = hours.open_time if hours and hours.open_time else time(9, 0)
    closes_at = hours.close_time if hours and hours.close_time else time(17, 0)
    if local_start.time().replace(tzinfo=None) < opens_at or local_end.time().replace(tzinfo=None) > closes_at:
        raise HTTPException(status_code=422, detail="Appointment is outside the clinic's working hours")


def book_appointment(database: Session, business_id: int, payload) -> Appointment:
    customer = database.scalar(select(Customer).where(Customer.id == payload.customer_id, Customer.business_id == business_id))
    doctor = database.scalar(select(Doctor).where(Doctor.id == payload.doctor_id, Doctor.business_id == business_id, Doctor.status == "active"))
    service = database.scalar(select(Service).where(Service.id == payload.service_id, Service.business_id == business_id, Service.status == "active"))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    starts_at = _as_utc(payload.starts_at)
    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Appointment must be in the future")
    validate_business_window(database, business_id, starts_at, service.duration_minutes)
    slot_key = f"{business_id}:{doctor.id}:{starts_at.isoformat()}"
    appointment = Appointment(
        business_id=business_id,
        customer_id=customer.id,
        doctor_id=doctor.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=service.duration_minutes),
        notes=payload.notes,
        status="CONFIRMED",
        slot_key=slot_key,
    )
    database.add(appointment)
    try:
        database.flush()
        database.add_all(_reservation_rows(appointment))
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="That doctor already has an appointment at this time") from None
    database.refresh(appointment)
    return appointment


def change_appointment_time(database: Session, appointment: Appointment, starts_at: datetime) -> Appointment:
    starts_at = _as_utc(starts_at)
    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Appointment must be in the future")
    service = database.get(Service, appointment.service_id)
    validate_business_window(database, appointment.business_id, starts_at, service.duration_minutes)
    appointment.starts_at = starts_at
    appointment.ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    appointment.slot_key = f"{appointment.business_id}:{appointment.doctor_id}:{starts_at.isoformat()}"
    try:
        database.query(AppointmentSlot).filter(AppointmentSlot.appointment_id == appointment.id).delete()
        database.flush()
        database.add_all(_reservation_rows(appointment))
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="That doctor already has an appointment at this time") from None
    database.refresh(appointment)
    return appointment
