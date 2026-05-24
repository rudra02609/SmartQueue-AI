"""
Database Models — SmartQueue AI
SAVE AS: app/models.py
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Float,
    Boolean, ForeignKey, Enum, Text, Date
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database.db import Base


# ══════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════

class UserRole(str, enum.Enum):
    PATIENT          = "patient"
    CUSTOMER         = "customer"
    ADMIN            = "admin"
    DOCTOR           = "doctor"
    BANK_STAFF       = "bank_staff"
    COUNTER_OPERATOR = "counter_operator"


class TokenStatus(str, enum.Enum):
    BOOKED     = "booked"
    CREATED    = "created"
    ACTIVE     = "active"
    IN_SERVICE = "in_service"
    COMPLETED  = "completed"
    EXPIRED    = "expired"
    CANCELLED  = "cancelled"


class PriorityLevel(str, enum.Enum):
    EMERGENCY = "emergency"
    HIGH      = "high"
    MEDIUM    = "medium"
    NORMAL    = "normal"


class Domain(str, enum.Enum):
    HEALTHCARE = "healthcare"
    BANKING    = "banking"


class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    FULL      = "full"
    CLOSED    = "closed"


class GrievanceStatus(str, enum.Enum):
    PENDING  = "pending"    # filed, awaiting admin review
    APPROVED = "approved"   # appeal granted — emergency restored
    REJECTED = "rejected"   # appeal denied — stays in normal queue


# ══════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id                = Column(Integer, primary_key=True, index=True)
    username          = Column(String, unique=True, index=True, nullable=False)
    email             = Column(String, unique=True, index=True, nullable=False)
    hashed_password   = Column(String, nullable=False)
    full_name         = Column(String)
    phone             = Column(String)
    role              = Column(Enum(UserRole), nullable=False, index=True)
    is_active         = Column(Boolean, default=True)
    is_senior_citizen = Column(Boolean, default=False)
    is_vip            = Column(Boolean, default=False)
    last_login        = Column(DateTime)
    refresh_token     = Column(String)
    created_at        = Column(DateTime, default=datetime.utcnow, index=True)

    tokens         = relationship("Token", back_populates="user")
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)


# ══════════════════════════════════════════════════════
# DOCTOR PROFILE
# ══════════════════════════════════════════════════════

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id                    = Column(Integer, primary_key=True, index=True)
    user_id               = Column(Integer, ForeignKey("users.id"), unique=True)
    specialization        = Column(String)
    department            = Column(String)
    is_available          = Column(Boolean, default=True)
    avg_consultation_time = Column(Integer, default=15)

    user   = relationship("User", back_populates="doctor_profile")
    queues = relationship("Queue", back_populates="doctor")


# ══════════════════════════════════════════════════════
# APPOINTMENT SLOT
# ══════════════════════════════════════════════════════

class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"

    id           = Column(Integer, primary_key=True, index=True)
    slot_date    = Column(Date, nullable=False, index=True)
    slot_time    = Column(String, nullable=False)
    slot_end     = Column(String, nullable=True)
    department   = Column(String, nullable=False, index=True)
    domain       = Column(Enum(Domain), nullable=False, index=True)
    doctor_id    = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    capacity     = Column(Integer, default=10)
    booked_count = Column(Integer, default=0)
    status       = Column(Enum(SlotStatus), default=SlotStatus.AVAILABLE, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Token", back_populates="slot")
    doctor   = relationship("DoctorProfile")


# ══════════════════════════════════════════════════════
# QUEUE
# ══════════════════════════════════════════════════════

class Queue(Base):
    __tablename__ = "queues"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False)
    domain         = Column(Enum(Domain), nullable=False, index=True)
    department     = Column(String)
    service_name   = Column(String)
    queue_type     = Column(String)
    doctor_id      = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    counter_number = Column(String, nullable=True)
    capacity       = Column(Integer, default=50)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow, index=True)

    doctor = relationship("DoctorProfile", back_populates="queues")
    tokens = relationship("Token", back_populates="queue")


# ══════════════════════════════════════════════════════
# TOKEN
# ══════════════════════════════════════════════════════

class Token(Base):
    __tablename__ = "tokens"

    id           = Column(Integer, primary_key=True, index=True)
    token_number = Column(String, unique=True, index=True, nullable=False)

    user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
    queue_id = Column(Integer, ForeignKey("queues.id"), nullable=True)
    slot_id  = Column(Integer, ForeignKey("appointment_slots.id"), nullable=True)

    domain   = Column(Enum(Domain), nullable=False, index=True)
    status   = Column(Enum(TokenStatus), default=TokenStatus.CREATED, index=True)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.NORMAL, index=True)
    position = Column(Integer)

    # Patient details
    patient_name      = Column(String)
    patient_phone     = Column(String, index=True)
    symptoms          = Column(Text)
    consultation_type = Column(String)
    service_name      = Column(String)

    # AI severity scoring (set when emergency token created)
    severity_score = Column(Integer)   # 1–10
    severity_flag  = Column(String)    # "likely_genuine" / "needs_check" / "suspicious"

    # Emergency rejection tracking
    emergency_rejected = Column(Boolean, default=False)
    rejection_reason   = Column(String, nullable=True)
    original_priority  = Column(String, nullable=True)  # priority before downgrade

    appointment_time = Column(DateTime, nullable=True)

    # Time tracking
    created_at           = Column(DateTime, default=datetime.utcnow, index=True)
    called_at            = Column(DateTime)
    service_started_at   = Column(DateTime)
    service_completed_at = Column(DateTime)
    expired_at           = Column(DateTime)

    # AI metrics
    estimated_wait_time   = Column(Integer)
    actual_wait_time      = Column(Integer)
    actual_service_time   = Column(Integer)
    prediction_confidence = Column(Float)
    ml_model_version      = Column(String)

    user       = relationship("User", back_populates="tokens")
    queue      = relationship("Queue", back_populates="tokens")
    slot       = relationship("AppointmentSlot", back_populates="bookings")
    audit_logs = relationship("AuditLog", back_populates="token")
    grievances = relationship("Grievance", back_populates="token")


# ══════════════════════════════════════════════════════
# EMERGENCY STRIKE  (abuse tracking per phone)
# ══════════════════════════════════════════════════════

class EmergencyStrike(Base):
    __tablename__ = "emergency_strikes"

    id         = Column(Integer, primary_key=True, index=True)
    phone      = Column(String, nullable=False, index=True)
    token_id   = Column(String, nullable=True)
    reason     = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


MAX_STRIKES = 3   # phone blocked from emergency after this many


# ══════════════════════════════════════════════════════
# GRIEVANCE  (appeal system for rejected emergency)
# ══════════════════════════════════════════════════════

class Grievance(Base):
    __tablename__ = "grievances"

    id          = Column(Integer, primary_key=True, index=True)
    token_id    = Column(Integer, ForeignKey("tokens.id"), nullable=False)

    # Filed by patient
    phone       = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    reason_code = Column(String, nullable=True)  # "chest_pain","accident","other"

    status = Column(Enum(GrievanceStatus), default=GrievanceStatus.PENDING, index=True)

    # Admin resolution
    resolved_by     = Column(String, nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at     = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    token = relationship("Token", back_populates="grievances")


# ══════════════════════════════════════════════════════
# SERVICE HISTORY
# ══════════════════════════════════════════════════════

class ServiceHistory(Base):
    __tablename__ = "service_history"

    id             = Column(Integer, primary_key=True, index=True)
    domain         = Column(Enum(Domain), nullable=False, index=True)
    department     = Column(String)
    service_name   = Column(String)
    doctor_id      = Column(Integer, nullable=True)
    counter_number = Column(String, nullable=True)
    service_time   = Column(Integer)
    wait_time      = Column(Integer)
    priority       = Column(Enum(PriorityLevel))
    queue_length   = Column(Integer)
    hour_of_day    = Column(Integer)
    day_of_week    = Column(Integer)
    created_at     = Column(DateTime, default=datetime.utcnow, index=True)


# ══════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, index=True)
    token_id   = Column(Integer, ForeignKey("tokens.id"))
    user_id    = Column(Integer, ForeignKey("users.id"))
    action     = Column(String, nullable=False)
    details    = Column(Text)
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    token = relationship("Token", back_populates="audit_logs")
    user  = relationship("User")


# ══════════════════════════════════════════════════════
# NOTIFICATION
# ══════════════════════════════════════════════════════

class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    token_id   = Column(Integer, ForeignKey("tokens.id"), nullable=True)
    type       = Column(String)
    subject    = Column(String)
    message    = Column(Text)
    sent_at    = Column(DateTime)
    status     = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user  = relationship("User")
    token = relationship("Token")