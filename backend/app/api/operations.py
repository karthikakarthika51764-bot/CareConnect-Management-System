from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user, hash_password, require_roles
from app.db import get_db
from app.models import Appointment, AppointmentSlot, Business, BusinessHour, Call, Customer, Doctor, Escalation, FollowUp, Holiday, Lead, Service, User
from app.schemas import AppointmentCreate, AppointmentReschedule, AppointmentResponse, CustomerCreate, CustomerResponse, CustomerUpdate, DoctorCreate, DoctorResponse, FollowUpCreate, FollowUpResponse, LeadCreate, LeadResponse, ServiceCreate, ServiceResponse, StaffCreate, StaffResponse
from app.services.appointments import ACTIVE_STATUSES, book_appointment, change_appointment_time
from app.services.notifications import queue_appointment_notification

router = APIRouter(prefix="/api/v1", tags=["operations"])


def _not_found(resource: str):
    raise HTTPException(status_code=404, detail=f"{resource} not found")


def _active_customer(database: Session, business_id: int, customer_id: int) -> Customer:
    customer = database.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id))
    if customer is None:
        _not_found("Customer")
    return customer


@router.get("/dashboard/summary")
def dashboard_summary(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    business_id = user.business_id
    if business_id is None:
        raise HTTPException(status_code=403, detail="Business access is required")
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    def count(model, *filters):
        return database.scalar(select(func.count()).select_from(model).where(model.business_id == business_id, *filters)) or 0
    return {
        "total_calls": count(Call),
        "ai_calls": count(Call, Call.handled_by == "AI"),
        "human_calls": count(Call, Call.handled_by == "HUMAN"),
        "appointments_today": count(Appointment, Appointment.starts_at >= start, Appointment.starts_at < end, Appointment.status.in_(ACTIVE_STATUSES)),
        "new_leads": count(Lead, Lead.status == "NEW"),
        "pending_follow_ups": count(FollowUp, FollowUp.status == "OPEN"),
        "missed_calls": count(Call, Call.status == "CALL_FAILED"),
        "open_escalations": count(Escalation, Escalation.status == "OPEN"),
    }


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(q: str | None = None, offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    statement = select(Customer).where(Customer.business_id == user.business_id)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(Customer.name.ilike(term) | Customer.phone.ilike(term) | Customer.email.ilike(term))
    return database.scalars(statement.order_by(Customer.created_at.desc()).offset(offset).limit(limit)).all()


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    customer = Customer(business_id=user.business_id, **payload.model_dump())
    database.add(customer)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="A customer with this phone number already exists") from None
    database.refresh(customer)
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return _active_customer(database, user.business_id, customer_id)


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, payload: CustomerUpdate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    customer = _active_customer(database, user.business_id, customer_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="A customer with this phone number already exists") from None
    database.refresh(customer)
    return customer


@router.get("/customers/{customer_id}/history")
def customer_history(customer_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    _active_customer(database, user.business_id, customer_id)
    appointments = database.scalars(select(Appointment).where(Appointment.business_id == user.business_id, Appointment.customer_id == customer_id).order_by(Appointment.starts_at.desc())).all()
    leads = database.scalars(select(Lead).where(Lead.business_id == user.business_id, Lead.customer_id == customer_id).order_by(Lead.created_at.desc())).all()
    return {"appointments": [AppointmentResponse.model_validate(row) for row in appointments], "leads": [LeadResponse.model_validate(row) for row in leads]}


@router.get("/doctors", response_model=list[DoctorResponse])
def list_doctors(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Doctor).where(Doctor.business_id == user.business_id).order_by(Doctor.name)).all()


@router.post("/doctors", response_model=DoctorResponse, status_code=201)
def create_doctor(payload: DoctorCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    doctor = Doctor(business_id=user.business_id, **payload.model_dump())
    database.add(doctor)
    database.commit()
    database.refresh(doctor)
    return doctor


@router.get("/doctors/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    doctor = database.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.business_id == user.business_id))
    if doctor is None:
        _not_found("Doctor")
    return doctor


@router.put("/doctors/{doctor_id}", response_model=DoctorResponse)
def update_doctor(doctor_id: int, payload: DoctorCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    doctor = database.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.business_id == user.business_id))
    if doctor is None:
        _not_found("Doctor")
    for field, value in payload.model_dump().items():
        setattr(doctor, field, value)
    database.commit()
    database.refresh(doctor)
    return doctor


@router.get("/services", response_model=list[ServiceResponse])
def list_services(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Service).where(Service.business_id == user.business_id).order_by(Service.name)).all()


@router.post("/services", response_model=ServiceResponse, status_code=201)
def create_service(payload: ServiceCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    service = Service(business_id=user.business_id, **payload.model_dump())
    database.add(service)
    database.commit()
    database.refresh(service)
    return service


@router.get("/services/{service_id}", response_model=ServiceResponse)
def get_service(service_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    service = database.scalar(select(Service).where(Service.id == service_id, Service.business_id == user.business_id))
    if service is None:
        _not_found("Service")
    return service


@router.put("/services/{service_id}", response_model=ServiceResponse)
def update_service(service_id: int, payload: ServiceCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF")), database: Session = Depends(get_db)):
    service = database.scalar(select(Service).where(Service.id == service_id, Service.business_id == user.business_id))
    if service is None:
        _not_found("Service")
    for field, value in payload.model_dump().items():
        setattr(service, field, value)
    database.commit()
    database.refresh(service)
    return service


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(on_date: date | None = None, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    statement = select(Appointment).where(Appointment.business_id == user.business_id).order_by(Appointment.starts_at.desc()).limit(250)
    if on_date:
        start = datetime.combine(on_date, time.min, tzinfo=timezone.utc)
        statement = statement.where(Appointment.starts_at >= start, Appointment.starts_at < start + timedelta(days=1))
    return database.scalars(statement).all()


@router.get("/appointments/availability")
def appointment_availability(doctor_id: int, service_id: int, on_date: date, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    doctor = database.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.business_id == user.business_id, Doctor.status == "active"))
    service = database.scalar(select(Service).where(Service.id == service_id, Service.business_id == user.business_id, Service.status == "active"))
    if doctor is None or service is None:
        raise HTTPException(status_code=404, detail="Doctor or service not found")
    business = database.get(Business, user.business_id)
    zone = ZoneInfo(business.timezone)
    if database.scalar(select(Holiday.id).where(Holiday.business_id == user.business_id, Holiday.holiday_date == on_date)):
        return {"slots": []}
    hours = database.scalar(select(BusinessHour).where(BusinessHour.business_id == user.business_id, BusinessHour.day_of_week == on_date.weekday()))
    if hours is not None and hours.is_closed:
        return {"slots": []}
    open_time = hours.open_time if hours and hours.open_time else time(9, 0)
    close_time = hours.close_time if hours and hours.close_time else time(17, 0)
    local_start = datetime.combine(on_date, open_time, tzinfo=zone)
    local_end = datetime.combine(on_date, close_time, tzinfo=zone)
    now = datetime.now(timezone.utc)
    slots = []
    cursor = local_start
    while cursor + timedelta(minutes=service.duration_minutes) <= local_end:
        starts_at = cursor.astimezone(timezone.utc)
        ends_at = starts_at + timedelta(minutes=service.duration_minutes)
        if starts_at > now:
            busy = database.scalar(select(AppointmentSlot.id).where(AppointmentSlot.doctor_id == doctor_id, AppointmentSlot.slot_at >= starts_at, AppointmentSlot.slot_at < ends_at).limit(1))
            if not busy:
                slots.append(starts_at.isoformat())
        cursor += timedelta(minutes=15)
    return {"slots": slots}


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
def create_appointment(payload: AppointmentCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    appointment = book_appointment(database, user.business_id, payload)
    queue_appointment_notification(database, appointment, "APPOINTMENT_CONFIRMED")
    database.commit()
    return appointment


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(appointment_id: int, user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    appointment = database.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.business_id == user.business_id))
    if appointment is None:
        _not_found("Appointment")
    return appointment


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(appointment_id: int, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    appointment = database.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.business_id == user.business_id))
    if appointment is None:
        _not_found("Appointment")
    if appointment.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="Only active appointments can be cancelled")
    appointment.status = "CANCELLED"
    appointment.slot_key = None
    database.query(AppointmentSlot).filter(AppointmentSlot.appointment_id == appointment.id).delete()
    queue_appointment_notification(database, appointment, "APPOINTMENT_CANCELLED")
    database.commit()
    database.refresh(appointment)
    return appointment


@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(appointment_id: int, payload: AppointmentReschedule, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    appointment = database.scalar(select(Appointment).where(Appointment.id == appointment_id, Appointment.business_id == user.business_id))
    if appointment is None:
        _not_found("Appointment")
    if appointment.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="Only active appointments can be rescheduled")
    appointment = change_appointment_time(database, appointment, payload.starts_at)
    queue_appointment_notification(database, appointment, "APPOINTMENT_RESCHEDULED")
    database.commit()
    return appointment


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(Lead).where(Lead.business_id == user.business_id).order_by(Lead.created_at.desc()).limit(250)).all()


@router.post("/leads", response_model=LeadResponse, status_code=201)
def create_lead(payload: LeadCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    if payload.status not in {"NEW", "CONTACTED", "INTERESTED", "FOLLOW_UP", "CONVERTED", "NOT_INTERESTED", "LOST"}:
        raise HTTPException(status_code=422, detail="Invalid lead status")
    _active_customer(database, user.business_id, payload.customer_id)
    lead = Lead(business_id=user.business_id, **payload.model_dump())
    database.add(lead)
    database.commit()
    database.refresh(lead)
    return lead


@router.get("/follow-ups", response_model=list[FollowUpResponse])
def list_follow_ups(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(FollowUp).where(FollowUp.business_id == user.business_id).order_by(FollowUp.due_at).limit(250)).all()


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=201)
def create_follow_up(payload: FollowUpCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER", "STAFF", "RECEPTIONIST")), database: Session = Depends(get_db)):
    _active_customer(database, user.business_id, payload.customer_id)
    if payload.lead_id is not None and database.scalar(select(Lead.id).where(Lead.id == payload.lead_id, Lead.business_id == user.business_id)) is None:
        _not_found("Lead")
    follow_up = FollowUp(business_id=user.business_id, **payload.model_dump())
    database.add(follow_up)
    database.commit()
    database.refresh(follow_up)
    return follow_up


@router.get("/staff", response_model=list[StaffResponse])
def list_staff(user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    return database.scalars(select(User).where(User.business_id == user.business_id).order_by(User.name)).all()


@router.post("/staff", response_model=StaffResponse, status_code=201)
def create_staff(payload: StaffCreate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    if payload.role not in {"STAFF", "RECEPTIONIST"}:
        raise HTTPException(status_code=422, detail="Staff role must be STAFF or RECEPTIONIST")
    if database.scalar(select(User.id).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="This email is already registered")
    staff = User(business_id=user.business_id, name=payload.name, email=payload.email.lower(), password_hash=hash_password(payload.password), role=payload.role)
    database.add(staff)
    database.commit()
    database.refresh(staff)
    return staff
