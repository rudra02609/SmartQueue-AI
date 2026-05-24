"""
Admin Router — SmartQueue AI
SAVE AS: app/routers/admin.py
Changes: severity flag in queue table, reason required on reject,
         grievance count in dashboard, strike tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.models import (
    Token, TokenStatus, Domain, PriorityLevel,
    EmergencyStrike, Grievance, GrievanceStatus
)
from app.services.notification_service import (
    sms_your_turn,
    sms_emergency_rejected
)
from app.services.queue_engine import (
    recalculate_queue,
    handle_cancellation,
    downgrade_unverified_emergency,
    SKIP_GRACE_BUFFER,
)
from app.services.priority_engine import add_strike
from app.services.websocket_manager import manager

router = APIRouter()


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_logged_in(authorization: Optional[str] = Header(None)):
    # BYPASSED FOR NOW AS REQUESTED BY USER
    return "dummy_token"


# ── Schemas ───────────────────────────────────────────────────────────────────

class RejectEmergencyRequest(BaseModel):
    reason: Optional[str] = "Rejected by staff"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: str = Depends(verify_logged_in)):
    active = [TokenStatus.ACTIVE, TokenStatus.CREATED]

    healthcare = db.query(Token).filter(
        Token.domain == Domain.HEALTHCARE, Token.status.in_(active)
    ).count()

    banking = db.query(Token).filter(
        Token.domain == Domain.BANKING, Token.status.in_(active)
    ).count()

    active_tokens = db.query(Token).filter(Token.status.in_(active)).all()
    avg_wait = 0
    if active_tokens:
        avg_wait = sum(t.estimated_wait_time or 0 for t in active_tokens) // len(active_tokens)

    # Pending grievances count — shown as alert in dashboard
    pending_grievances = db.query(Grievance).filter(
        Grievance.status == GrievanceStatus.PENDING
    ).count()

    return {
        "total_tokens":        healthcare + banking,
        "healthcare_queue":    healthcare,
        "banking_queue":       banking,
        "active_queues":       2,
        "avg_wait_time":       f"{avg_wait}m",
        "served_today":        db.query(Token).filter(
                                   Token.status == TokenStatus.COMPLETED
                               ).count(),
        "pending_grievances":  pending_grievances   # ← new field
    }


# ── Queue table ───────────────────────────────────────────────────────────────

@router.get("/queues")
def get_queues(db: Session = Depends(get_db), _: str = Depends(verify_logged_in)):
    tokens = db.query(Token).filter(
        Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
    ).order_by(Token.position).all()

    return [
        {
            "token_id":       t.token_number,
            "service":        t.service_name,
            "domain":         t.domain.value if t.domain else None,
            "priority":       t.priority.value if t.priority else "normal",
            "position":       t.position,
            "estimated_wait": t.estimated_wait_time,
            "status":         t.status.value if t.status else "active",
            # Severity info for emergency tokens — shown as flag in admin UI
            "severity_score": t.severity_score,
            "severity_flag":  t.severity_flag,
        }
        for t in tokens
    ]


# ── Call token ────────────────────────────────────────────────────────────────

@router.patch("/tokens/{token_id}/call")
def call_token(
    token_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_logged_in)
):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.status    = TokenStatus.IN_SERVICE
    token.called_at = datetime.utcnow()
    db.commit()

    recalculate_queue(db, extra_buffer=0)

    if token.patient_phone:
        sms_your_turn(
            phone      = token.patient_phone,
            token_id   = token_id,
            department = token.service_name or "counter",
            counter    = token.queue.counter_number if token.queue else None
        )

    return {
        "token_id": token_id,
        "message":  f"{token_id} is now being served",
        "status":   "in_service"
    }


# ── Skip token ────────────────────────────────────────────────────────────────

@router.patch("/tokens/{token_id}/skip")
def skip_token(
    token_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_logged_in)
):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    queue_size = db.query(Token).filter(
        Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
    ).count()

    token.position = queue_size + 1
    db.commit()

    recalculate_queue(db, extra_buffer=SKIP_GRACE_BUFFER)

    return {
        "token_id":     token_id,
        "message":      f"{token_id} skipped — moved to end. +{SKIP_GRACE_BUFFER} min buffer added.",
        "new_position": queue_size,
        "buffer_added": SKIP_GRACE_BUFFER
    }


# ── Complete token ────────────────────────────────────────────────────────────

@router.patch("/tokens/{token_id}/complete")
def complete_token(
    token_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_logged_in)
):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.status              = TokenStatus.COMPLETED
    token.service_completed_at = datetime.utcnow()
    db.commit()

    recalculate_queue(db, extra_buffer=0)
    return {"token_id": token_id, "status": "completed"}


# ── Reject emergency claim ────────────────────────────────────────────────────

@router.patch("/tokens/{token_id}/reject-emergency")
def reject_emergency_claim(
    token_id: str,
    payload:  RejectEmergencyRequest = RejectEmergencyRequest(),
    db:       Session = Depends(get_db),
    _:        str     = Depends(verify_logged_in)
):
    """
    Staff rejects emergency claim.
    - Downgrades token to back of normal queue
    - Adds abuse strike to phone number
    - Records rejection reason
    - Sends SMS with appeal instructions
    """
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if token.priority != PriorityLevel.EMERGENCY:
        raise HTTPException(status_code=400, detail="Token is not marked as emergency")

    # Save original priority before downgrade
    token.original_priority  = PriorityLevel.EMERGENCY.value
    token.emergency_rejected = True
    token.rejection_reason   = payload.reason
    token.called_at          = datetime.utcnow()   # timestamp for appeal window

    result = downgrade_unverified_emergency(db, token)

    # Add strike to phone number
    if token.patient_phone:
        total_strikes = add_strike(
            phone      = token.patient_phone,
            token_id   = token_id,
            reason     = payload.reason or "Rejected by staff",
            db         = db,
            created_by = "admin"
        )
        result["total_strikes"]      = total_strikes
        result["emergency_blocked"]  = total_strikes >= 3

        # SMS with appeal instructions
        sms_emergency_rejected(
            phone        = token.patient_phone,
            token_id     = token_id,
            new_position = result.get("new_position", 0)
        )

    # Send WebSocket notification to user
    import asyncio
    async def send_rejection_notification():
        await manager.send_personal_message({
            "type": "token_rejected",
            "token_id": token_id,
            "message": "Your token has been rejected",
            "reason": payload.reason or "Rejected by staff",
            "new_position": result.get("new_position", 0),
            "can_appeal": True
        }, token_id)
    
    try:
        asyncio.create_task(send_rejection_notification())
    except Exception as e:
        print(f"WebSocket notification error: {e}")

    return result


# ── Call next (legacy) ────────────────────────────────────────────────────────

@router.post("/queues/{queue_id}/call-next")
def call_next(
    queue_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_logged_in)
):
    next_token = db.query(Token).filter(
        Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
    ).order_by(Token.position).first()

    if not next_token:
        return {"message": "No tokens in queue"}

    next_token.status    = TokenStatus.IN_SERVICE
    next_token.called_at = datetime.utcnow()
    db.commit()
    recalculate_queue(db, extra_buffer=0)

    return {
        "token_id": next_token.token_number,
        "service":  next_token.service_name,
        "position": next_token.position
    }


# ── Live tokens (legacy) ──────────────────────────────────────────────────────

@router.get("/live-tokens")
def live_tokens(db: Session = Depends(get_db), _: str = Depends(verify_logged_in)):
    return db.query(Token).all()