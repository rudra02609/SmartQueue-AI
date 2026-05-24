"""
Queue Engine — Core queue operations with buffer-aware cancellation.

SAVE THIS FILE AS: app/services/queue_engine.py
"""

from sqlalchemy.orm import Session
from typing import Optional

from app.models import Token, Queue, TokenStatus, PriorityLevel
from app.services.priority_engine import calculate_priority

# ── Constants ────────────────────────────────────────────────────────────────

AVG_SERVICE_TIME   = 8    # minutes per person at counter
MIN_ARRIVAL_BUFFER = 10   # minimum minutes a person needs to safely arrive
SKIP_GRACE_BUFFER  = 5    # extra minutes added when someone is skipped/absent

PRIORITY_ORDER = {
    PriorityLevel.EMERGENCY: 0,
    PriorityLevel.HIGH:      1,
    PriorityLevel.MEDIUM:    2,
    PriorityLevel.NORMAL:    3,
}


# ── Add token to queue ────────────────────────────────────────────────────────

def add_token_to_queue(db: Session, token: Token, queue: Queue):
    """
    Assign priority and position when a token joins.
    Priority: EMERGENCY > HIGH (senior/VIP) > MEDIUM > NORMAL
    Within same priority: FIFO by created_at.
    """
    priority = calculate_priority(token, queue)
    token.priority = priority

    ahead = (
        db.query(Token)
        .filter(
            Token.queue_id == queue.id,
            Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED]),
        )
        .all()
    )

    ahead_sorted = sorted(
        ahead,
        key=lambda t: (PRIORITY_ORDER.get(t.priority, 3), t.created_at)
    )

    token.position = len(ahead_sorted) + 1
    token.estimated_wait_time = len(ahead_sorted) * AVG_SERVICE_TIME

    db.add(token)
    db.commit()


# ── Recalculate entire queue ──────────────────────────────────────────────────

def recalculate_queue(db: Session, queue_id: Optional[int] = None, extra_buffer: int = 0):
    """
    Recalculate positions and ETA for all waiting tokens.

    Buffer-aware ETA rule:
      - A person's ETA is never dropped below MIN_ARRIVAL_BUFFER (except
        position 1 who is already next regardless).
      - extra_buffer: additional grace minutes for position-1 person after
        a skip/no-show event.
    """
    query = db.query(Token).filter(
        Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
    )
    if queue_id:
        query = query.filter(Token.queue_id == queue_id)

    active_tokens = query.all()

    active_tokens.sort(key=lambda t: (
        PRIORITY_ORDER.get(t.priority, 3),
        t.position or 999
    ))

    for new_pos, token in enumerate(active_tokens, start=1):
        token.position = new_pos
        if new_pos == 1:
            token.estimated_wait_time = extra_buffer
        else:
            raw_eta = (new_pos - 1) * AVG_SERVICE_TIME + extra_buffer
            token.estimated_wait_time = max(raw_eta, MIN_ARRIVAL_BUFFER)

    db.commit()


# ── Buffer-aware cancellation ────────────────────────────────────────────────

def handle_cancellation(db: Session, cancelled_token: Token) -> dict:
    """
    Cancel a token and redistribute the freed slot with a buffer check.

    For each person behind the cancelled slot:
      - new_eta = current_eta - AVG_SERVICE_TIME
      - If new_eta >= MIN_ARRIVAL_BUFFER  → safe to update
      - If new_eta < MIN_ARRIVAL_BUFFER   → floor at MIN_ARRIVAL_BUFFER,
        open freed slot for standby list
    """
    queue_id       = cancelled_token.queue_id
    freed_position = cancelled_token.position

    cancelled_token.status = TokenStatus.CANCELLED
    db.commit()

    tokens_behind = (
        db.query(Token)
        .filter(
            Token.queue_id == queue_id,
            Token.position > freed_position,
            Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED])
        )
        .order_by(Token.position)
        .all()
    )

    standby_slots_opened = 0
    safely_updated       = 0

    for token in tokens_behind:
        current_eta = token.estimated_wait_time or 0
        new_eta     = current_eta - AVG_SERVICE_TIME

        if new_eta >= MIN_ARRIVAL_BUFFER:
            token.position -= 1
            token.estimated_wait_time = new_eta
            safely_updated += 1
        else:
            # ETA would be dangerously low — protect the person
            token.position -= 1
            token.estimated_wait_time = max(new_eta, MIN_ARRIVAL_BUFFER)
            standby_slots_opened += 1

    db.commit()

    # Final priority-aware recalculation to clean up edge cases
    recalculate_queue(db, queue_id=queue_id, extra_buffer=0)

    return {
        "cancelled_token":      cancelled_token.token_number,
        "freed_position":       freed_position,
        "tokens_shifted":       safely_updated,
        "standby_slots_opened": standby_slots_opened,
        "min_buffer_applied":   MIN_ARRIVAL_BUFFER,
        "message": (
            f"Slot freed. {safely_updated} users updated safely. "
            f"{standby_slots_opened} standby slot(s) opened."
            if standby_slots_opened
            else f"Slot freed. {safely_updated} users updated. Queue rebalanced."
        )
    }


# ── Emergency fraud downgrade ─────────────────────────────────────────────────

def downgrade_unverified_emergency(db: Session, token: Token) -> dict:
    """
    Called by admin/staff when an emergency claim is rejected.
    Penalty: token moves to the BACK of the normal queue.
    """
    last_normal = (
        db.query(Token)
        .filter(
            Token.queue_id == token.queue_id,
            Token.status.in_([TokenStatus.ACTIVE, TokenStatus.CREATED]),
            Token.priority == PriorityLevel.NORMAL,
        )
        .order_by(Token.position.desc())
        .first()
    )

    penalty_position = (last_normal.position + 1) if last_normal else 999
    token.priority              = PriorityLevel.NORMAL
    token.position              = penalty_position
    token.estimated_wait_time   = (penalty_position - 1) * AVG_SERVICE_TIME

    db.commit()
    recalculate_queue(db, queue_id=token.queue_id)

    return {
        "token":        token.token_number,
        "action":       "emergency_downgraded",
        "new_priority": "normal",
        "new_position": token.position,
        "new_eta":      token.estimated_wait_time,
        "message":      "Emergency claim rejected. Token moved to end of normal queue."
    }