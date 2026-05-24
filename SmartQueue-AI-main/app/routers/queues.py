from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.database.db import get_db
from app.schemas import QueueCreate, QueueResponse
from app.models import Queue, Token, TokenStatus
from app.auth.auth import get_admin_user
from app.services.queue_engine import handle_cancellation

router = APIRouter()


# ✅ CREATE QUEUE
@router.post("/", response_model=QueueResponse)
def create_queue(
    data: QueueCreate,
    db: Session = Depends(get_db),
    _=Depends(get_admin_user)
):
    queue = Queue(**data.dict())
    db.add(queue)
    db.commit()
    db.refresh(queue)
    return queue


# ✅ LIST QUEUES
@router.get("/", response_model=list[QueueResponse])
def list_queues(db: Session = Depends(get_db)):
    return db.query(Queue).filter(Queue.is_active == True).all()


# 🔥 ✅ JOIN QUEUE (CREATE TOKEN)
@router.post("/join/{queue_id}")
def join_queue(queue_id: int, user_id: int, db: Session = Depends(get_db)):
    queue = db.query(Queue).filter(Queue.id == queue_id).first()

    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    last_token = (
        db.query(Token)
        .filter(Token.queue_id == queue_id, Token.status != TokenStatus.CANCELLED)
        .order_by(Token.position.desc())
        .first()
    )

    next_position = 1 if not last_token else last_token.position + 1

    new_token = Token(
        token_number=f"T{queue_id}-{next_position}",
        user_id=user_id,
        queue_id=queue_id,
        domain=queue.domain,
        status=TokenStatus.CREATED,
        position=next_position
    )

    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    return {
        "message": "User added to queue",
        "token": new_token.token_number,
        "position": new_token.position
    }


# 🔥🔥🔥 ✅ LEAVE QUEUE — buffer-aware, no more blind position -= 1
@router.post("/leave/{token_id}")
def leave_queue(token_id: int, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.id == token_id).first()

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if token.status == TokenStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Token already cancelled")

    # ✅ Buffer-aware redistribution — protects people with low ETAs
    result = handle_cancellation(db, token)
    return result


# 🔥 ✅ GET QUEUE WITH ORDER
@router.get("/{queue_id}/tokens")
def get_queue_tokens(queue_id: int, db: Session = Depends(get_db)):
    tokens = (
        db.query(Token)
        .filter(
            Token.queue_id == queue_id,
            Token.status != TokenStatus.CANCELLED
        )
        .order_by(asc(Token.position))
        .all()
    )

    return tokens