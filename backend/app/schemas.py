from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    business_name: str = Field(min_length=2, max_length=180)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(ORMModel):
    id: int
    name: str
    email: str
    role: str
    business_id: int | None


class BusinessUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=400)
    timezone: str = Field(default="Asia/Kolkata", max_length=80)
    description: str | None = None


class BusinessResponse(ORMModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    address: str | None
    timezone: str
    description: str | None
    status: str


class BusinessHourInput(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool = False

    @model_validator(mode="after")
    def valid_hours(self):
        if not self.is_closed and (self.open_time is None or self.close_time is None or self.open_time >= self.close_time):
            raise ValueError("Open and close times must form a valid interval")
        return self


class BusinessHourResponse(ORMModel):
    id: int
    day_of_week: int
    open_time: time | None
    close_time: time | None
    is_closed: bool


class HolidayInput(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=160)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: EmailStr | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=5, max_length=40)
    email: EmailStr | None = None
    notes: str | None = None


class CustomerResponse(ORMModel):
    id: int
    name: str
    phone: str
    email: str | None
    notes: str | None
    created_at: datetime


class DoctorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    specialization: str = Field(min_length=2, max_length=160)
    phone: str | None = None
    email: EmailStr | None = None
    consultation_fee: float | None = Field(default=None, ge=0)


class DoctorResponse(ORMModel):
    id: int
    name: str
    specialization: str
    phone: str | None
    email: str | None
    consultation_fee: float | None
    status: str


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    duration_minutes: int = Field(default=30, ge=5, le=480)
    price: float | None = Field(default=None, ge=0)


class ServiceResponse(ORMModel):
    id: int
    name: str
    description: str | None
    duration_minutes: int
    price: float | None
    status: str


class AppointmentCreate(BaseModel):
    customer_id: int
    doctor_id: int
    service_id: int
    starts_at: datetime
    notes: str | None = None


class AppointmentResponse(ORMModel):
    id: int
    customer_id: int
    doctor_id: int
    service_id: int
    starts_at: datetime
    ends_at: datetime
    status: str
    notes: str | None


class AppointmentReschedule(BaseModel):
    starts_at: datetime


class LeadCreate(BaseModel):
    customer_id: int
    source: str = "manual"
    status: str = "NEW"
    notes: str | None = None
    assigned_staff_id: int | None = None


class LeadResponse(ORMModel):
    id: int
    customer_id: int
    source: str
    status: str
    notes: str | None
    assigned_staff_id: int | None
    created_at: datetime


class FollowUpCreate(BaseModel):
    customer_id: int
    lead_id: int | None = None
    due_at: datetime
    notes: str | None = None


class FollowUpResponse(ORMModel):
    id: int
    customer_id: int
    lead_id: int | None
    due_at: datetime
    status: str
    notes: str | None


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: str = "STAFF"


class StaffResponse(ORMModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=10, max_length=100_000)
    category: str = "faq"


class KnowledgeResponse(ORMModel):
    id: int
    title: str
    content: str
    category: str
    created_at: datetime


class VoiceWebhook(BaseModel):
    call_id: str
    business_id: int
    event: str
    caller_number: str | None = None
    transcript: str | None = None
    language: str | None = None
    intent: str | None = None


class AIMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    call_id: int | None = None


class AIMessageResponse(BaseModel):
    language: str
    intent: str
    response: str
    handoff: bool = False
