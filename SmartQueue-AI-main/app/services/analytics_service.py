from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models import Token, Queue, ServiceHistory, TokenStatus


def average_wait_time(db: Session, queue_id: int):
    result = (
        db.query(func.avg(Token.actual_wait_time))
        .filter(Token.queue_id == queue_id, Token.status == TokenStatus.COMPLETED)
        .scalar()
    )
    return round(result or 0, 2)


def peak_hour_analysis(db: Session, days: int = 7):
    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            func.extract("hour", ServiceHistory.created_at).label("hour"),
            func.count(ServiceHistory.id)
        )
        .filter(ServiceHistory.created_at >= since)
        .group_by("hour")
        .order_by(func.count(ServiceHistory.id).desc())
        .all()
    )

    return [{"hour": int(h), "count": c} for h, c in rows]


def staff_performance(db: Session):
    rows = (
        db.query(
            ServiceHistory.doctor_id,
            func.avg(ServiceHistory.service_time),
            func.count(ServiceHistory.id)
        )
        .group_by(ServiceHistory.doctor_id)
        .all()
    )

    return [
        {
            "staff_id": r[0],
            "avg_service_time": round(r[1], 2) if r[1] else 0,
            "tokens_served": r[2]
        }
        for r in rows
    ]
