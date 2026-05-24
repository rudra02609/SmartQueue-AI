
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    PATIENT = "patient"
    CUSTOMER = "customer"
    ADMIN = "admin"
    DOCTOR = "doctor"
    BANK_STAFF = "bank_staff"
    COUNTER_OPERATOR = "counter_operator"

class TokenStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class PriorityLevel(str, Enum):
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    NORMAL = "normal"

class Domain(str, Enum):
    HEALTHCARE = "healthcare"
    BANKING = "banking"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    phone: str
    role: UserRole
    is_senior_citizen: Optional[bool] = False
    is_vip: Optional[bool] = False

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    is_senior_citizen: bool
    is_vip: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class QueueCreate(BaseModel):
    name: str
    domain: Domain
    department: Optional[str] = None
    service_type: Optional[str] = None
    doctor_id: Optional[int] = None
    counter_number: Optional[str] = None
    capacity: Optional[int] = 50

class QueueResponse(BaseModel):
    id: int
    name: str
    domain: Domain
    department: Optional[str]
    service_type: Optional[str]
    counter_number: Optional[str]
    is_active: bool
    current_queue_length: Optional[int] = 0
    avg_wait_time: Optional[int] = 0

    class Config:
        from_attributes = True

class TokenCreate(BaseModel):
    queue_id: int
    domain: Domain
    symptoms: Optional[str] = None
    consultation_type: Optional[str] = None
    service_required: Optional[str] = None

class TokenResponse(BaseModel):
    id: int
    token_number: str
    queue_id: int
    domain: Domain
    status: TokenStatus
    priority: PriorityLevel
    position: Optional[int]
    estimated_wait_time: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class TokenUpdate(BaseModel):
    status: Optional[TokenStatus] = None
    priority: Optional[PriorityLevel] = None

class EmergencyTokenCreate(BaseModel):
    symptoms: str
    severity_score: int = Field(ge=1, le=10)
    department: str

class DoctorAvailability(BaseModel):
    doctor_id: int
    is_available: bool
    avg_consultation_time: Optional[int] = None

class AppointmentCreate(BaseModel):
    doctor_id: int
    scheduled_time: datetime
    consultation_type: str
    symptoms: Optional[str] = None

class BankingTokenCreate(BaseModel):
    service_type: str
    department: str

class CounterStatus(BaseModel):
    counter_number: str
    is_active: bool
    current_token: Optional[str] = None
    tokens_served_today: int = 0

class QueueAnalytics(BaseModel):
    queue_id: int
    queue_name: str
    total_tokens_today: int
    avg_wait_time: float
    avg_service_time: float
    peak_hour: Optional[int] = None
    current_queue_length: int

class PerformanceMetrics(BaseModel):
    entity_id: int
    entity_name: str
    tokens_served: int
    avg_service_time: float
    customer_rating: Optional[float] = None
    efficiency_score: float

class NotificationCreate(BaseModel):
    user_id: int
    type: str
    subject: str
    message: str
    token_id: Optional[int] = None

class WaitTimePrediction(BaseModel):
    queue_id: int
    estimated_wait_time: int
    confidence_score: float
    factors: dict
