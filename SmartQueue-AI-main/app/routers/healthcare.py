"""
Healthcare Router — SmartQueue AI
SAVE AS: app/routers/healthcare.py
Changes: severity scoring, strike check, SMS on walk-in token creation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.auth.auth import get_doctor_user
from app.models import DoctorProfile, Token, Queue, TokenStatus, PriorityLevel, Domain
from app.utils.token_generator import generate_token
from app.services.priority_engine import (
    calculate_severity_score,
    get_severity_flag,
    is_emergency_blocked,
    get_strike_count
)
from app.services.notification_service import sms_walkin_created

router = APIRouter()


class HealthcareTokenCreate(BaseModel):
    patient_name: str
    phone:        str
    department:   str
    doctor_id:    Optional[str] = None
    priority:     str = "normal"
    age:          Optional[int] = None
    gender:       Optional[str] = None
    reason:       Optional[str] = None


@router.post("/token")
def create_healthcare_token(
    data: HealthcareTokenCreate,
    db:   Session = Depends(get_db)
):
    """
    Create a walk-in healthcare token.
    Runs severity scoring on symptoms.
    Checks emergency strike count before allowing P1.
    Sends SMS confirmation.
    """
    try:
        priority_str = data.priority
        severity_score = None
        severity_flag  = None
        auto_downgraded = False

        # ── Emergency handling ─────────────────────────────────────────────
        if priority_str == "emergency":

            # 1. Check if this phone is blocked (3+ strikes)
            if is_emergency_blocked(data.phone, db):
                strike_count = get_strike_count(data.phone, db)
                # Silent downgrade — don't tell abuser why
                priority_str    = "normal"
                auto_downgraded = True
                print(f"[Priority] Phone {data.phone} blocked ({strike_count} strikes) — downgraded to normal")

            else:
                # 2. Score the symptoms
                severity_score = calculate_severity_score(data.reason or "")
                flag_data      = get_severity_flag(severity_score)
                severity_flag  = flag_data["flag"]
                print(f"[Severity] Score={severity_score} Flag={severity_flag} Symptoms='{data.reason}'")

        # ── Map priority ───────────────────────────────────────────────────
        priority_map = {
            "emergency": PriorityLevel.EMERGENCY,
            "senior":    PriorityLevel.HIGH,
            "normal":    PriorityLevel.NORMAL
        }
        priority_enum = priority_map.get(priority_str, PriorityLevel.NORMAL)

        # ── Calculate position ─────────────────────────────────────────────
        position = db.query(Token).filter(
            Token.domain == Domain.HEALTHCARE,
            Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
        ).count() + 1

        # ── Wait time based on priority ────────────────────────────────────
        wait_times = {"emergency": 2, "senior": 8, "normal": 15}
        estimated_wait = wait_times.get(priority_str, 15)

        # ── Create token ───────────────────────────────────────────────────
        token_id = generate_token("healthcare", data.department.upper()[:3])

        token = Token(
            token_number        = token_id,
            domain              = Domain.HEALTHCARE,
            status              = TokenStatus.ACTIVE,
            priority            = priority_enum,
            position            = position,
            estimated_wait_time = estimated_wait,
            symptoms            = data.reason,
            service_name        = data.department,
            patient_name        = data.patient_name,
            patient_phone       = data.phone,
            severity_score      = severity_score,
            severity_flag       = severity_flag
        )

        db.add(token)
        db.commit()
        db.refresh(token)

        # ── SMS: walk-in token created ─────────────────────────────────────
        if data.phone:
            sms_walkin_created(
                phone      = data.phone,
                token_id   = token_id,
                department = data.department,
                position   = position,
                wait_mins  = estimated_wait
            )

        response = {
            "token_id":           token_id,
            "position":           position,
            "estimated_wait_time": estimated_wait,
            "status":             "active",
            "priority":           priority_str,
            "created_at":         datetime.now().isoformat()
        }

        # Include severity info for emergency tokens (admin sees this)
        if severity_score is not None:
            response["severity_score"] = severity_score
            response["severity_flag"]  = severity_flag

        # Inform if downgraded (without revealing why)
        if auto_downgraded:
            response["note"] = "Priority adjusted by system."

        return response

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
def get_healthcare_queue(
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get healthcare queue status per department."""
    try:
        query = db.query(Token).filter(
            Token.domain == Domain.HEALTHCARE,
            Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
        )
        if department:
            query = query.filter(Token.service_name == department)
        count = query.count()
        return [{"department": department or "all", "count": count, "status": "active"}]
    except Exception:
        return []


@router.patch("/doctors/{doctor_id}/availability")
def update_availability(
    doctor_id: int,
    available: bool,
    db: Session = Depends(get_db),
    _=Depends(get_doctor_user)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if doctor:
        doctor.is_available = available
        db.commit()
    return {"status": "updated"}