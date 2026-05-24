"""
Priority Engine — SmartQueue AI
AI severity scoring + priority calculation + strike checking
SAVE AS: app/services/priority_engine.py
"""

from app.models import PriorityLevel, Domain


# ══════════════════════════════════════════════════════
# SEVERITY SCORING — keyword-based AI
# ══════════════════════════════════════════════════════

# Score 8-10: strong emergency indicators
CRITICAL_KEYWORDS = [
    "chest pain", "heart attack", "cardiac", "can't breathe",
    "difficulty breathing", "shortness of breath", "unconscious",
    "not responding", "seizure", "stroke", "severe bleeding",
    "head injury", "overdose", "choking", "anaphylaxis",
    "allergic reaction", "convulsion", "fracture", "broken bone",
    "severe burn", "high fever", "paralysis", "blood pressure",
    "diabetic", "insulin", "severe pain", "accident", "fell down",
    "road accident", "hit by", "stabbed", "injury"
]

# Score 5-7: possible emergency — needs staff check
MODERATE_KEYWORDS = [
    "fever", "vomiting", "vomiting blood", "dizziness", "faint",
    "fainting", "swelling", "infection", "wound", "cut", "pain",
    "bleeding", "breathless", "cold", "cough", "headache",
    "stomach pain", "abdominal pain", "back pain", "nausea"
]

# Score 1-4: likely not emergency — flag as suspicious
LOW_RISK_KEYWORDS = [
    "general checkup", "routine", "prescription", "prescription refill",
    "follow up", "follow-up", "report collection", "certificate",
    "mild", "slight", "minor", "just in case", "not urgent",
    "normal checkup", "regular visit", "fitness certificate"
]


def calculate_severity_score(symptoms: str) -> int:
    """
    Score symptom text 1–10.
    8–10 = likely genuine emergency
    5–7  = possible emergency, staff should verify
    1–4  = likely not emergency, flag as suspicious

    Returns 3 if symptoms are empty (suspicious — no reason given).
    """
    if not symptoms or symptoms.strip() == "":
        return 3   # No symptoms = suspicious

    text = symptoms.lower().strip()

    # Check critical keywords first
    for keyword in CRITICAL_KEYWORDS:
        if keyword in text:
            return 9

    # Check moderate keywords
    for keyword in MODERATE_KEYWORDS:
        if keyword in text:
            return 6

    # Check low-risk keywords
    for keyword in LOW_RISK_KEYWORDS:
        if keyword in text:
            return 2

    # Unknown symptoms — neutral
    return 4


def get_severity_flag(score: int) -> dict:
    """
    Returns display flag for the admin dashboard.
    Shows next to emergency tokens so staff know what to expect.
    """
    if score >= 8:
        return {
            "flag":      "likely_genuine",
            "label":     "Likely genuine",
            "color":     "green",
            "recommend": "approve"
        }
    elif score >= 5:
        return {
            "flag":      "needs_check",
            "label":     "Needs check",
            "color":     "amber",
            "recommend": "verify_physically"
        }
    else:
        return {
            "flag":      "suspicious",
            "label":     "Suspicious",
            "color":     "red",
            "recommend": "reject"
        }


# ══════════════════════════════════════════════════════
# STRIKE CHECK — block repeat abusers
# ══════════════════════════════════════════════════════

def is_emergency_blocked(phone: str, db) -> bool:
    """
    Check if a phone number has reached MAX_STRIKES.
    If blocked, emergency claims are silently downgraded to NORMAL.
    """
    from app.models import EmergencyStrike, MAX_STRIKES
    if not phone:
        return False
    count = db.query(EmergencyStrike).filter(
        EmergencyStrike.phone == phone.strip()
    ).count()
    return count >= MAX_STRIKES


def get_strike_count(phone: str, db) -> int:
    """Return number of emergency strikes for this phone number."""
    from app.models import EmergencyStrike
    if not phone:
        return 0
    return db.query(EmergencyStrike).filter(
        EmergencyStrike.phone == phone.strip()
    ).count()


def add_strike(phone: str, token_id: str, reason: str, db,
               created_by: str = "system") -> int:
    """
    Add an emergency abuse strike for a phone number.
    Returns the new total strike count.
    """
    from app.models import EmergencyStrike
    strike = EmergencyStrike(
        phone      = phone.strip(),
        token_id   = token_id,
        reason     = reason,
        created_by = created_by
    )
    db.add(strike)
    db.commit()
    return get_strike_count(phone, db)


# ══════════════════════════════════════════════════════
# PRIORITY CALCULATION
# ══════════════════════════════════════════════════════

def calculate_priority(token, queue, db=None) -> PriorityLevel:
    """
    Determine priority for a token.
    Healthcare: emergency (score ≥ 8) > senior (HIGH) > normal
    Banking: VIP (HIGH) > senior (MEDIUM) > normal
    If phone has MAX_STRIKES, emergency is blocked.
    """
    if token.domain == Domain.HEALTHCARE:
        # Check if phone is blocked from emergency
        if (token.patient_phone and db and
                is_emergency_blocked(token.patient_phone, db)):
            return PriorityLevel.NORMAL   # silently downgraded

        if token.severity_score and token.severity_score >= 8:
            return PriorityLevel.EMERGENCY

        # Senior citizen check (from user profile if linked)
        if token.user and token.user.is_senior_citizen:
            return PriorityLevel.HIGH

    if token.domain == Domain.BANKING:
        if token.user and token.user.is_vip:
            return PriorityLevel.HIGH
        if token.user and token.user.is_senior_citizen:
            return PriorityLevel.MEDIUM

    return PriorityLevel.NORMAL