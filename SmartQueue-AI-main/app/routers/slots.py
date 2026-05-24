from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from typing import Optional, List
import random, string

from app.database.db import get_db
from app.models import (
    AppointmentSlot, Token, TokenStatus, SlotStatus,
    Domain, PriorityLevel
)
from app.utils.token_generator import generate_token
from app.services.notification_service import (
    sms_otp, sms_booking_confirmed,
    sms_token_activated, sms_token_expired
)

router = APIRouter()

# --- CONFIG ---
SLOT_DURATION = 30  # minutes
DAY_START = "09:00"
DAY_END = "17:00"

# --- SCHEMAS ---
class SlotResponse(BaseModel):
    id: int
    slot_time: str
    slot_end: str
    available: int
    booked_count: int
    capacity: int
    is_full: bool
    status: str

    class Config:
        from_attributes = True


class AvailableSlotsResponse(BaseModel):
    date: str
    department: str
    slots: List[SlotResponse]
    message: Optional[str] = None


class OTPSendRequest(BaseModel):
    phone: str


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str


class SlotGenerateRequest(BaseModel):
    date: str
    department: str
    domain: str
    capacity: Optional[int] = 10
    doctor_id: Optional[int] = None


class SlotBookRequest(BaseModel):
    slot_id: int
    phone: str
    patient_name: str
    department: str
    domain: str
    priority: Optional[str] = "normal"
    reason: Optional[str] = None


# --- IN-MEMORY OTP STORE ---
_otp_store: dict = {}


# ─────────────────────────────────────────────
# HELPER: normalise inputs consistently
# ─────────────────────────────────────────────
def _normalise_domain(raw: str) -> Domain:
    """Parse domain string case-insensitively and raise a clean 400 on failure."""
    try:
        return Domain(raw.strip().lower())
    except ValueError:
        valid = [d.value for d in Domain]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain '{raw}'. Valid values: {valid}"
        )


# ─────────────────────────────────────────────
# GENERATE SLOTS
# Run this via Swagger to pre-create slots for a date.
# ─────────────────────────────────────────────
@router.post("/generate")
def generate_slots(data: SlotGenerateRequest, db: Session = Depends(get_db)):
    """Generate 30-minute appointment slots for a given date/department/domain."""
    try:
        gen_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    domain_enum = _normalise_domain(data.domain)
    department  = data.department.strip()

    created_count = 0
    curr_time = datetime.strptime(DAY_START, "%H:%M")
    end_time  = datetime.strptime(DAY_END,   "%H:%M")

    while curr_time < end_time:
        start_str  = curr_time.strftime("%H:%M")
        curr_time += timedelta(minutes=SLOT_DURATION)
        end_str    = curr_time.strftime("%H:%M")

        # Avoid duplicate slots
        exists = db.query(AppointmentSlot).filter(
            AppointmentSlot.slot_date  == gen_date,
            AppointmentSlot.slot_time  == start_str,
            AppointmentSlot.department == department,
            AppointmentSlot.domain     == domain_enum
        ).first()

        if not exists:
            new_slot = AppointmentSlot(
                slot_date    = gen_date,
                slot_time    = start_str,
                slot_end     = end_str,
                department   = department,
                domain       = domain_enum,
                capacity     = data.capacity,
                booked_count = 0,
                status       = SlotStatus.AVAILABLE
            )
            db.add(new_slot)
            created_count += 1

    db.commit()
    return {
        "message":   f"Generated {created_count} slots for {data.date}",
        "date":      data.date,
        "department": department,
        "domain":    domain_enum.value,
        "capacity":  data.capacity
    }


# ─────────────────────────────────────────────
# OTP — SEND
# ─────────────────────────────────────────────
@router.post("/otp/send")
def send_otp(data: OTPSendRequest):
    phone = data.phone.strip()
    if not phone or len(phone) < 10:
        raise HTTPException(400, "Invalid phone number.")

    otp = ''.join(random.choices(string.digits, k=6))
    _otp_store[phone] = {
        "otp":      otp,
        "expires":  datetime.utcnow() + timedelta(minutes=10),
        "verified": False
    }
    sms_otp(phone, otp)
    return {"message": "OTP sent.", "dev_otp": otp}  # Remove dev_otp in production!


# ─────────────────────────────────────────────
# OTP — VERIFY
# ─────────────────────────────────────────────
@router.post("/otp/verify")
def verify_otp(data: OTPVerifyRequest):
    phone  = data.phone.strip()
    record = _otp_store.get(phone)

    if not record or datetime.utcnow() > record["expires"]:
        raise HTTPException(400, "OTP expired or not found.")
    if record["otp"] != data.otp.strip():
        raise HTTPException(400, "Incorrect OTP.")

    _otp_store[phone]["verified"] = True
    return {"verified": True, "phone": phone}


# ─────────────────────────────────────────────
# GET AVAILABLE SLOTS  ← MAIN FIX IS HERE
# ─────────────────────────────────────────────
@router.get("/available", response_model=AvailableSlotsResponse)
def get_available_slots(
    date_str:   str,
    department: str,
    domain:     str,
    db: Session = Depends(get_db)
):
    # 1. Parse date
    try:
        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Use YYYY-MM-DD format.")

    # 2. Normalise inputs  ← FIX: case-insensitive domain + trimmed department
    domain_enum = _normalise_domain(domain)
    department  = department.strip()

    # 3. Query — use ilike() for case-insensitive department match  ← FIX
    slots = db.query(AppointmentSlot).filter(
        AppointmentSlot.slot_date  == slot_date,
        AppointmentSlot.department.ilike(department),   # ← was == (case-sensitive)
        AppointmentSlot.domain     == domain_enum,
        AppointmentSlot.status     != SlotStatus.CLOSED
    ).order_by(AppointmentSlot.slot_time).all()

    # 4. Return clear message when no slots found
    if not slots:
        return {
            "date":       date_str,
            "department": department,
            "slots":      [],
            "message":    (
                f"No slots found for {department} / {domain_enum.value} on {date_str}. "
                "Run POST /api/slots/generate first, or check department & domain spelling."
            )
        }

    return {
        "date":       date_str,
        "department": department,
        "slots": [
            {
                "id":           s.id,
                "slot_time":    s.slot_time,
                "slot_end":     s.slot_end,
                "available":    max(0, s.capacity - s.booked_count),
                "booked_count": s.booked_count,
                "capacity":     s.capacity,
                "is_full":      s.booked_count >= s.capacity,
                "status":       s.status.value
            }
            for s in slots
        ]
    }


# ─────────────────────────────────────────────
# BOOK A SLOT
# ─────────────────────────────────────────────
@router.post("/book")
def book_slot(data: SlotBookRequest, db: Session = Depends(get_db)):
    # 1. OTP must be verified
    phone      = data.phone.strip()
    otp_record = _otp_store.get(phone)
    if not otp_record or not otp_record.get("verified"):
        raise HTTPException(400, "Verify phone via OTP first.")

    # 2. Validate domain
    domain_enum = _normalise_domain(data.domain)

    # 3. Get slot
    slot = db.query(AppointmentSlot).filter(
        AppointmentSlot.id == data.slot_id
    ).first()

    if not slot:
        raise HTTPException(404, "Slot not found.")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(400, "Slot is full.")
    if slot.status == SlotStatus.CLOSED:
        raise HTTPException(400, "Slot is closed.")

    # 4. Create token
    token_id = generate_token(data.domain, data.department.upper()[:3])

    token = Token(
        token_number     = token_id,
        domain           = domain_enum,
        status           = TokenStatus.BOOKED,
        slot_id          = data.slot_id,
        patient_name     = data.patient_name,
        patient_phone    = phone,
        service_name     = data.department.strip(),
        appointment_time = datetime.combine(
            slot.slot_date,
            datetime.strptime(slot.slot_time, "%H:%M").time()
        )
    )

    # 5. Update slot counts
    slot.booked_count += 1
    if slot.booked_count >= slot.capacity:
        slot.status = SlotStatus.FULL

    db.add(token)
    db.commit()

    # 6. Clear OTP and send confirmation SMS
    _otp_store.pop(phone, None)
    sms_booking_confirmed(
        phone, token_id, data.department,
        slot.slot_date.strftime("%d %b"),
        slot.slot_time,
        slot.booked_count
    )

    return {
        "token_id":  token_id,
        "status":    "booked",
        "slot_time": slot.slot_time,
        "slot_date": slot.slot_date.strftime("%Y-%m-%d"),
        "position":  slot.booked_count
    }