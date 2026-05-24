"""
Notification Service — SmartQueue AI
SMS via Twilio
SAVE AS: app/services/notification_service.py

Setup:  pip install twilio
Enable: Set SMS_ENABLED = True and fill in credentials below.
"""

from twilio.rest import Client
from typing import Optional

# ══════════════════════════════════════════════════════
# TWILIO CREDENTIALS — fill these in
# ══════════════════════════════════════════════════════

SMS_ENABLED        = True                                 # ← True when ready
TWILIO_ACCOUNT_SID = "ACe78da0883e7842d77be673e9b5d2348b"  # console.twilio.com
TWILIO_AUTH_TOKEN  = "8b34663fd5f953089b3e131892fd0ff5"    # console.twilio.com
TWILIO_FROM_NUMBER = "+18146322052"                        # your Twilio number

APP_NAME = "SmartQueue"


# ══════════════════════════════════════════════════════
# CORE SENDER
# ══════════════════════════════════════════════════════

def _clean_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if len(phone) == 10:
        return f"+91{phone}"
    return phone


def send_sms(phone: str, message: str) -> bool:
    phone = _clean_phone(phone)
    print(f"\n[SMS] ──────────────────────────────")
    print(f"[SMS] To:  {phone}")
    print(f"[SMS] Msg: {message}")
    print(f"[SMS] ──────────────────────────────\n")

    if not SMS_ENABLED:
        print("[SMS] Dev mode — not sent. Set SMS_ENABLED=True to send real SMS.")
        return True

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message, from_=TWILIO_FROM_NUMBER, to=phone
        )
        print(f"[SMS] Sent! SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"[SMS] FAILED to {phone}: {e}")
        return False


# ══════════════════════════════════════════════════════
# SMS TEMPLATES
# ══════════════════════════════════════════════════════

def sms_otp(phone: str, otp: str) -> bool:
    """OTP for slot booking. Called: POST /api/slots/otp/send"""
    return send_sms(phone, (
        f"{APP_NAME}: Your OTP is {otp}. "
        f"Valid for 10 minutes. Do not share with anyone."
    ))


def sms_booking_confirmed(
    phone: str, token_id: str, department: str,
    appointment_date: str, slot_time: str, slot_position: int
) -> bool:
    """Pre-booking confirmed. Called: POST /api/slots/book"""
    return send_sms(phone, (
        f"{APP_NAME}: Appointment confirmed!\n"
        f"Token: {token_id} | {department.upper()}\n"
        f"Date: {appointment_date} at {slot_time}\n"
        f"Slot #{slot_position}. Arrive 5 min early.\n"
        f"Token expires 15 min after slot if unused."
    ))


def sms_walkin_created(
    phone: str, token_id: str, department: str,
    position: int, wait_mins: int
) -> bool:
    """Walk-in token issued. Called: POST /api/healthcare/token"""
    return send_sms(phone, (
        f"{APP_NAME}: Token issued!\n"
        f"Token: {token_id} | {department.upper()}\n"
        f"Position: #{position} | Est. wait: ~{wait_mins} min\n"
        f"You will be SMS'd when 3 people are ahead."
    ))


def sms_token_activated(
    phone: str, token_id: str, department: str,
    position: int, wait_mins: int
) -> bool:
    """Pre-booked token active today. Called: APScheduler"""
    return send_sms(phone, (
        f"{APP_NAME}: Your appointment is TODAY!\n"
        f"Token: {token_id} | {department.upper()}\n"
        f"Position: #{position} | Est. wait: ~{wait_mins} min\n"
        f"You will be SMS'd when 3 people are ahead."
    ))


def sms_almost_your_turn(
    phone: str, token_id: str, department: str,
    ahead: int, wait_mins: int
) -> bool:
    """3 or fewer people ahead. Called: queue_engine recalculate_queue"""
    return send_sms(phone, (
        f"{APP_NAME}: Almost your turn!\n"
        f"Token: {token_id} | {department.upper()}\n"
        f"Only {ahead} person{'s' if ahead != 1 else ''} ahead (~{wait_mins} min).\n"
        f"Please head to the hospital/counter NOW."
    ))


def sms_your_turn(
    phone: str, token_id: str, department: str,
    counter: Optional[str] = None
) -> bool:
    """Admin clicked Call. Called: PATCH /api/admin/tokens/{id}/call"""
    counter_text = f"Go to Counter {counter}" if counter else "Go to the counter"
    return send_sms(phone, (
        f"{APP_NAME}: IT'S YOUR TURN!\n"
        f"Token: {token_id} | {department.upper()}\n"
        f"{counter_text} immediately.\n"
        f"You have 5 minutes before your token expires."
    ))


def sms_token_expired(
    phone: str, token_id: str, department: str
) -> bool:
    """Token auto-expired. Called: APScheduler"""
    return send_sms(phone, (
        f"{APP_NAME}: Token expired.\n"
        f"Token {token_id} ({department.upper()}) expired — no check-in detected.\n"
        f"Please re-book at SmartQueue."
    ))


def sms_token_cancelled(
    phone: str, token_id: str, department: str
) -> bool:
    """Patient cancelled. Called: DELETE /api/tokens/{id}"""
    return send_sms(phone, (
        f"{APP_NAME}: Booking cancelled.\n"
        f"Token {token_id} ({department.upper()}) has been cancelled.\n"
        f"Re-book anytime at SmartQueue."
    ))


def sms_emergency_rejected(
    phone: str, token_id: str, new_position: int
) -> bool:
    """
    Emergency claim rejected by staff.
    Called: PATCH /api/admin/tokens/{id}/reject-emergency
    Includes appeal instructions.
    """
    return send_sms(phone, (
        f"{APP_NAME}: Emergency claim rejected.\n"
        f"Token {token_id}: not verified by staff.\n"
        f"Moved to position #{new_position} in normal queue.\n"
        f"If this was a genuine emergency, open SmartQueue "
        f"and tap 'File Appeal' within 30 minutes."
    ))


def sms_grievance_approved(
    phone: str, token_id: str, department: str
) -> bool:
    """
    Appeal approved — emergency restored.
    Called: PATCH /api/grievance/{id}/approve
    """
    return send_sms(phone, (
        f"{APP_NAME}: Appeal APPROVED!\n"
        f"Token {token_id} ({department.upper()}):\n"
        f"Your emergency claim was verified.\n"
        f"You have been moved to position #1 — please come to the counter NOW."
    ))


def sms_grievance_rejected_appeal(
    phone: str, token_id: str,
    strike_count: int, max_strikes: int
) -> bool:
    """
    Appeal rejected — stays in normal queue.
    Called: PATCH /api/grievance/{id}/reject
    """
    blocked_note = (
        " Emergency access has been BLOCKED on your number."
        if strike_count >= max_strikes else
        f" Warning: {strike_count}/{max_strikes} strikes on this number."
    )
    return send_sms(phone, (
        f"{APP_NAME}: Appeal rejected.\n"
        f"Token {token_id}: your appeal was reviewed and denied.\n"
        f"You remain in the normal queue.{blocked_note}"
    ))
