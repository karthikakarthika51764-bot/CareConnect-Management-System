from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db import get_db
from app.models import Business, BusinessHour, Holiday, User
from app.schemas import BusinessHourInput, BusinessHourResponse, BusinessResponse, BusinessUpdate, HolidayInput

router = APIRouter(prefix="/api/v1/business", tags=["business"])


def get_business(database: Session, user: User) -> Business:
    if user.business_id is None:
        raise HTTPException(status_code=403, detail="This account is not assigned to a business")
    business = database.get(Business, user.business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.get("", response_model=BusinessResponse)
def read_business(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return get_business(database, user)


@router.put("", response_model=BusinessResponse)
def update_business(payload: BusinessUpdate, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    business = get_business(database, user)
    for key, value in payload.model_dump().items():
        setattr(business, key, value)
    database.commit()
    database.refresh(business)
    return business


@router.get("/hours", response_model=list[BusinessHourResponse])
def read_hours(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.scalars(select(BusinessHour).where(BusinessHour.business_id == user.business_id).order_by(BusinessHour.day_of_week)).all()


@router.put("/hours", response_model=list[BusinessHourResponse])
def update_hours(payload: list[BusinessHourInput], user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    if len({item.day_of_week for item in payload}) != len(payload):
        raise HTTPException(status_code=422, detail="Each weekday may appear only once")
    existing = {item.day_of_week: item for item in database.scalars(select(BusinessHour).where(BusinessHour.business_id == user.business_id)).all()}
    for item in payload:
        row = existing.get(item.day_of_week)
        if row is None:
            row = BusinessHour(business_id=user.business_id, day_of_week=item.day_of_week)
            database.add(row)
        row.open_time = item.open_time
        row.close_time = item.close_time
        row.is_closed = item.is_closed
    database.commit()
    return database.scalars(select(BusinessHour).where(BusinessHour.business_id == user.business_id).order_by(BusinessHour.day_of_week)).all()


@router.get("/holidays")
def read_holidays(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    return database.execute(select(Holiday).where(Holiday.business_id == user.business_id).order_by(Holiday.holiday_date)).scalars().all()


@router.post("/holidays", status_code=201)
def create_holiday(payload: HolidayInput, user: User = Depends(require_roles("SUPER_ADMIN", "BUSINESS_OWNER")), database: Session = Depends(get_db)):
    holiday = Holiday(business_id=user.business_id, holiday_date=payload.holiday_date, name=payload.name)
    database.add(holiday)
    database.commit()
    database.refresh(holiday)
    return holiday
