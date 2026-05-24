from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database.db import get_db
from app.models import Queue, Token, TokenStatus, Domain, PriorityLevel
from app.auth.auth import get_staff_user
from app.utils.token_generator import generate_token

router = APIRouter()


class BankingTokenCreate(BaseModel):
    customer_name: str
    phone: str
    service_type: str
    account_type: Optional[str] = "savings"
    is_premium: bool = False


@router.post("/token")
def create_banking_token(data: BankingTokenCreate, db: Session = Depends(get_db)):
    """Create a new banking token without authentication"""
    try:
        # Generate token ID
        token_id = generate_token("banking", data.service_type.upper()[:3])
        
        # Calculate position
        position = db.query(Token).filter(
            Token.domain == Domain.BANKING,
            Token.status == TokenStatus.ACTIVE
        ).count() + 1
        
        # Premium customers get priority
        estimated_wait = 3 if data.is_premium else 10
        priority = PriorityLevel.HIGH if data.is_premium else PriorityLevel.NORMAL
        
        # Create token
        token = Token(
            token_number=token_id,
            domain=Domain.BANKING,
            status=TokenStatus.ACTIVE,
            priority=priority,
            position=position,
            estimated_wait_time=estimated_wait,
            service_name=data.service_type
        )
        
        db.add(token)
        db.commit()
        db.refresh(token)
        
        return {
            "token_id": token_id,
            "position": position,
            "estimated_wait_time": estimated_wait,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
def get_banking_queue(service_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get banking queue status"""
    try:
        query = db.query(Token).filter(
            Token.domain == Domain.BANKING,
            Token.status == TokenStatus.ACTIVE
        )
        
        if service_type:
            query = query.filter(Token.service_name == service_type)
        
        count = query.count()
        
        return [{
            "service_type": service_type or "all",
            "count": count,
            "status": "active"
        }]
    except Exception as e:
        return []


@router.get("/counters")
def list_counters(db: Session = Depends(get_db), _=Depends(get_staff_user)):
    return db.query(Queue).filter(Queue.domain == Domain.BANKING).all()
