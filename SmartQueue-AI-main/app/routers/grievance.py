"""
Grievance Router — SmartQueue AI
SAVE AS: app/routers/grievance.py
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from app.database.db import get_db
from app.models import (
    Grievance, GrievanceStatus,
    Token, TokenStatus, PriorityLevel,
    EmergencyStrike, MAX_STRIKES
)
from app.services.notification_service import (
    sms_grievance_approved,
    sms_grievance_rejected_appeal
)
from app.services.queue_engine import recalculate_queue

router = APIRouter()

APPEAL_WINDOW_MINUTES = 30


# ─────────────────────────────────────────────
# AUTH HELPER
# ─────────────────────────────────────────────
def verify_logged_in(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    if not token or token in ("null", "undefined", ""):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────
class GrievanceSubmit(BaseModel):
    token_number: str
    phone:        str
    description:  str
    reason_code:  Optional[str] = "other"


class GrievanceResolve(BaseModel):
    resolution_note: str
    resolved_by:     Optional[str] = "admin"


# ─────────────────────────────────────────────
# POST /submit  — patient files appeal
# ─────────────────────────────────────────────
@router.post("/submit")
def submit_grievance(data: GrievanceSubmit, db: Session = Depends(get_db)):
    # 1. Find token
    token = db.query(Token).filter(
        Token.token_number == data.token_number.strip()
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found.")

    # 2. Phone must match
    if token.patient_phone and token.patient_phone.strip() != data.phone.strip():
        raise HTTPException(
            status_code=403,
            detail="Phone number does not match this token."
        )

    # 3. Validate description length
    if not data.description or len(data.description.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Please provide a detailed description (at least 20 characters)."
        )

    # 4. Check appeal window — only if token has a called_at timestamp
    if token.called_at:
        window_end = token.called_at + timedelta(minutes=APPEAL_WINDOW_MINUTES)
        if datetime.utcnow() > window_end:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Appeal window has closed. Appeals must be filed within "
                    f"{APPEAL_WINDOW_MINUTES} minutes."
                )
            )

    # 5. No duplicate pending grievance
    existing = db.query(Grievance).filter(
        Grievance.token_id == token.id,
        Grievance.status   == GrievanceStatus.PENDING
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a pending appeal (#{existing.id}) for this token."
        )

    # 6. Create grievance
    grievance = Grievance(
        token_id    = token.id,
        phone       = data.phone.strip(),
        description = data.description.strip(),
        reason_code = data.reason_code or "other",
        status      = GrievanceStatus.PENDING
    )
    db.add(grievance)
    db.commit()
    db.refresh(grievance)

    return {
        "grievance_id": grievance.id,
        "token_id":     data.token_number,
        "status":       "pending",
        "message": (
            f"Appeal #{grievance.id} filed successfully. "
            f"Admin will review shortly. "
            f"You will receive an SMS with the decision."
        )
    }


# ─────────────────────────────────────────────
# GET /list  — admin sees all grievances
# ─────────────────────────────────────────────
@router.get("/list")
def list_grievances(
    status: Optional[str] = "pending",
    db:     Session       = Depends(get_db),
    _:      str           = Depends(verify_logged_in)
):
    query = db.query(Grievance)

    if status and status.lower() != "all":
        try:
            query = query.filter(
                Grievance.status == GrievanceStatus(status.lower())
            )
        except ValueError:
            valid = [s.value for s in GrievanceStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid: {valid} or 'all'"
            )

    grievances = query.order_by(Grievance.created_at.desc()).all()

    result = []
    for g in grievances:
        t = g.token
        result.append({
            "grievance_id":     g.id,
            "token_number":     t.token_number     if t else None,
            "phone":            g.phone,
            "department":       t.service_name     if t else None,
            "description":      g.description,
            "reason_code":      g.reason_code,
            "rejection_reason": getattr(t, "rejection_reason", None),
            "severity_score":   getattr(t, "severity_score",   None),
            "severity_flag":    getattr(t, "severity_flag",    None),
            "status":           g.status.value,
            "filed_at":         g.created_at.isoformat() if g.created_at else None,
            "resolved_at":      g.resolved_at.isoformat() if g.resolved_at else None,
            "resolution_note":  g.resolution_note,
        })

    return {"count": len(result), "grievances": result}


# ─────────────────────────────────────────────
# GET /status/{token_number}  — patient polls appeal status
# NOTE: this must be defined BEFORE /{grievance_id} to avoid routing conflict
# ─────────────────────────────────────────────
@router.get("/status/{token_number}")
def get_appeal_status(token_number: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(
        Token.token_number == token_number
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found.")

    grievance = (
        db.query(Grievance)
        .filter(Grievance.token_id == token.id)
        .order_by(Grievance.created_at.desc())
        .first()
    )

    if not grievance:
        return {
            "token_id":      token_number,
            "has_grievance": False,
            "message":       "No appeal filed for this token."
        }

    status_messages = {
        "pending":  "Your appeal is under review. You will be notified by SMS.",
        "approved": "Appeal approved! Your emergency priority has been restored.",
        "rejected": "Appeal rejected. You remain in the normal queue."
    }

    return {
        "token_id":         token_number,
        "has_grievance":    True,
        "grievance_id":     grievance.id,
        "appeal_status":    grievance.status.value,
        "filed_at":         grievance.created_at.isoformat() if grievance.created_at else None,
        "resolved_at":      grievance.resolved_at.isoformat() if grievance.resolved_at else None,
        "resolution_note":  grievance.resolution_note,
        "current_priority": token.priority.value if token.priority else None,
        "current_position": token.position,
        "message":          status_messages.get(grievance.status.value, "")
    }


# ─────────────────────────────────────────────
# GET /{grievance_id}  — admin gets one grievance
# ─────────────────────────────────────────────
@router.get("/{grievance_id}")
def get_grievance(
    grievance_id: int,
    db: Session = Depends(get_db),
    _:  str     = Depends(verify_logged_in)
):
    g = db.query(Grievance).filter(Grievance.id == grievance_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found.")

    t = g.token
    return {
        "grievance_id":     g.id,
        "token_number":     t.token_number       if t else None,
        "current_position": t.position           if t else None,
        "current_priority": t.priority.value     if t and t.priority else None,
        "phone":            g.phone,
        "department":       t.service_name       if t else None,
        "symptoms":         getattr(t, "symptoms",          None),
        "description":      g.description,
        "reason_code":      g.reason_code,
        "rejection_reason": getattr(t, "rejection_reason",  None),
        "severity_score":   getattr(t, "severity_score",    None),
        "severity_flag":    getattr(t, "severity_flag",     None),
        "status":           g.status.value,
        "filed_at":         g.created_at.isoformat() if g.created_at else None,
        "resolved_at":      g.resolved_at.isoformat() if g.resolved_at else None,
        "resolution_note":  g.resolution_note,
        "resolved_by":      g.resolved_by
    }


# ─────────────────────────────────────────────
# PATCH /{grievance_id}/approve  — admin approves
# ─────────────────────────────────────────────
@router.patch("/{grievance_id}/approve")
def approve_grievance(
    grievance_id: int,
    data: GrievanceResolve,
    db:   Session = Depends(get_db),
    _:    str     = Depends(verify_logged_in)
):
    g = db.query(Grievance).filter(Grievance.id == grievance_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    if g.status != GrievanceStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Grievance is already {g.status.value}."
        )

    token = g.token
    if not token:
        raise HTTPException(status_code=404, detail="Associated token not found.")

    # Restore emergency priority
    token.priority = PriorityLevel.EMERGENCY
    if hasattr(token, "emergency_rejected"):
        token.emergency_rejected = False
    if hasattr(token, "rejection_reason"):
        token.rejection_reason = None

    # Move token to front — shift all active tokens forward by 1
    others = db.query(Token).filter(
        Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED]),
        Token.token_number != token.token_number
    ).all()
    for t in others:
        if t.position is not None:
            t.position += 1
    token.position = 1

    # Resolve grievance
    g.status          = GrievanceStatus.APPROVED
    g.resolved_by     = data.resolved_by or "admin"
    g.resolution_note = data.resolution_note
    g.resolved_at     = datetime.utcnow()

    db.commit()

    try:
        recalculate_queue(db, extra_buffer=0)
    except Exception:
        pass  # don't fail the whole request if recalculation has an issue

    if token.patient_phone:
        try:
            sms_grievance_approved(
                phone      = token.patient_phone,
                token_id   = token.token_number,
                department = token.service_name or "hospital"
            )
        except Exception:
            pass  # SMS failure should not block the response

    return {
        "grievance_id": grievance_id,
        "status":       "approved",
        "token_id":     token.token_number,
        "new_priority": "emergency",
        "new_position": 1,
        "message":      f"Appeal approved. Token {token.token_number} restored to emergency priority at position #1."
    }


# ─────────────────────────────────────────────
# PATCH /{grievance_id}/reject  — admin rejects
# ─────────────────────────────────────────────
@router.patch("/{grievance_id}/reject")
def reject_grievance(
    grievance_id: int,
    data: GrievanceResolve,
    db:   Session = Depends(get_db),
    _:    str     = Depends(verify_logged_in)
):
    g = db.query(Grievance).filter(Grievance.id == grievance_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    if g.status != GrievanceStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Grievance is already {g.status.value}."
        )

    token = g.token

    # Add a strike for false appeal
    strike = EmergencyStrike(
        phone      = g.phone,
        token_id   = token.token_number if token else None,
        reason     = f"False appeal rejected: {data.resolution_note}",
        created_by = data.resolved_by or "admin"
    )
    db.add(strike)

    # Resolve grievance
    g.status          = GrievanceStatus.REJECTED
    g.resolved_by     = data.resolved_by or "admin"
    g.resolution_note = data.resolution_note
    g.resolved_at     = datetime.utcnow()

    db.commit()

    total_strikes = db.query(EmergencyStrike).filter(
        EmergencyStrike.phone == g.phone
    ).count()

    if token and token.patient_phone:
        try:
            sms_grievance_rejected_appeal(
                phone        = token.patient_phone,
                token_id     = token.token_number,
                strike_count = total_strikes,
                max_strikes  = MAX_STRIKES
            )
        except Exception:
            pass  # SMS failure should not block the response

    return {
        "grievance_id":      grievance_id,
        "status":            "rejected",
        "token_id":          token.token_number if token else None,
        "total_strikes":     total_strikes,
        "emergency_blocked": total_strikes >= MAX_STRIKES,
        "message": (
            f"Appeal rejected. Token stays in normal queue. "
            f"Phone now has {total_strikes}/{MAX_STRIKES} strikes."
            + (" Emergency access BLOCKED." if total_strikes >= MAX_STRIKES else "")
        )
    }


# ─────────────────────────────────────────────
# GET /grievance-form  — serves the HTML page
# ─────────────────────────────────────────────
@router.get("/grievance-form", response_class=HTMLResponse)
def grievance_form():
    try:
        with open("app/templates/grievance.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h2 style='font-family:sans-serif;padding:2rem'>grievance.html not found. Place it in app/templates/</h2>",
            status_code=404
        )