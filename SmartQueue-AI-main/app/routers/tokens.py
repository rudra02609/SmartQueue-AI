from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.db import get_db
from app.schemas import TokenCreate, TokenResponse
from app.models import Token, TokenStatus
from app.utils.token_generator import generate_token
from app.auth.auth import get_current_active_user
from app.services.queue_engine import handle_cancellation

router = APIRouter()


class StatusUpdate(BaseModel):
    status: str


# 🔥 ✅ CREATE TOKEN (FIXED POSITION LOGIC)
@router.post("/", response_model=TokenResponse)
def create_token(
    data: TokenCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user)
):
    token_number = generate_token(data.domain.value, "S")

    # 🔥 Get last position in queue
    last_token = db.query(Token).filter(
        Token.queue_id == data.queue_id,
        Token.status != TokenStatus.CANCELLED
    ).order_by(Token.position.desc()).first()

    next_position = 1 if not last_token else last_token.position + 1

    token = Token(
        token_number=token_number,
        user_id=user.id,
        queue_id=data.queue_id,
        domain=data.domain,
        status=TokenStatus.ACTIVE,
        position=next_position   # 🔥 IMPORTANT
    )

    db.add(token)
    db.commit()
    db.refresh(token)
    return token


# ✅ GET TOKEN DETAILS
@router.get("/{token_id}")
def get_token(token_id: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return {
        "token_id":       token.token_number,
        "position":       token.position,
        "estimated_wait": token.estimated_wait_time,
        "status":         token.status.value if token.status else "active",
        "domain":         token.domain.value if token.domain else None,
        "service":        token.service_name,
    }


# ✅ GET POSITION
@router.get("/{token_id}/position")
def get_token_position(token_id: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    ahead = db.query(Token).filter(
        Token.queue_id == token.queue_id,
        Token.status == TokenStatus.ACTIVE,
        Token.position < token.position
    ).count()

    return {
        "token_id":       token_id,
        "position":       token.position,
        "estimated_wait": token.estimated_wait_time,
        "ahead_count":    ahead,
        "status":         token.status.value if token.status else "active"
    }


# 🔥 ✅ UPDATE STATUS
@router.patch("/{token_id}/status")
def update_token_status(token_id: str, payload: StatusUpdate, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    status_map = {
        "waiting":   TokenStatus.ACTIVE,
        "called":    TokenStatus.IN_SERVICE,
        "serving":   TokenStatus.IN_SERVICE,
        "completed": TokenStatus.COMPLETED,
        "cancelled": TokenStatus.CANCELLED
    }

    if payload.status in status_map:
        token.status = status_map[payload.status]
        db.commit()

    return {"token_id": token_id, "status": payload.status}


# 🔥🔥🔥 ✅ CANCEL TOKEN — buffer-aware redistribution
@router.delete("/{token_id}")
def cancel_token(token_id: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_id).first()

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if token.status == TokenStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Token already cancelled")

    # ✅ Buffer-aware cancellation — no more blind position -= 1
    result = handle_cancellation(db, token)
    return result