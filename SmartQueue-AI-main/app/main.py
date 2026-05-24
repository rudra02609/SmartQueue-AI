from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.database.db import engine, Base, get_db
from app.routers import auth, tokens, queues, analytics, healthcare, banking, admin
from app.routers.slots     import router as slots_router
from app.routers.grievance import router as grievance_router
from app.services.websocket_manager import manager
from app.ai.predictor import WaitTimePredictor
from app.models import Token, TokenStatus, User, UserRole
from apscheduler.schedulers.asyncio import AsyncIOScheduler

predictor = WaitTimePredictor()
scheduler = AsyncIOScheduler()


async def run_expiry_check():
    db = next(get_db())
    try:
        from app.services.notification_service import sms_token_expired
        cutoff   = datetime.utcnow() - timedelta(minutes=15)
        no_shows = db.query(Token).filter(
            Token.status == TokenStatus.ACTIVE,
            Token.appointment_time != None,
            Token.appointment_time < cutoff,
            Token.service_started_at == None
        ).all()
        for t in no_shows:
            t.status     = TokenStatus.EXPIRED
            t.expired_at = datetime.utcnow()
            if t.patient_phone:
                sms_token_expired(t.patient_phone, t.token_number, t.service_name or "hospital")
        if no_shows:
            db.commit()
            print(f"[Scheduler] Expired {len(no_shows)} no-show token(s)")
    except Exception as e:
        print(f"[Scheduler] Expiry error: {e}")
    finally:
        db.close()


async def run_daily_activation():
    from datetime import date
    db = next(get_db())
    try:
        from app.models import AppointmentSlot
        from app.services.notification_service import sms_token_activated
        today  = date.today()
        booked = (
            db.query(Token).join(AppointmentSlot)
            .filter(AppointmentSlot.slot_date == today, Token.status == TokenStatus.BOOKED)
            .all()
        )
        for t in booked:
            t.status = TokenStatus.ACTIVE
            if t.patient_phone:
                sms_token_activated(
                    t.patient_phone, t.token_number,
                    t.service_name or "hospital",
                    t.position or 1, t.estimated_wait_time or 0
                )
        if booked:
            db.commit()
            print(f"[Scheduler] Activated {len(booked)} token(s) for {today}")
    except Exception as e:
        print(f"[Scheduler] Activation error: {e}")
    finally:
        db.close()


def seed_admin_user():
    """Create default admin user if it doesn't exist. Runs at every startup."""
    from app.auth.auth import get_password_hash
    db = next(get_db())
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                email="admin@smartqueue.ai",
                hashed_password="$2b$12$W44EQGxjBISmmQQCZ1EKsu1v8DpiiPwtQVAcriNPlxJZm6agpOu6a",
                full_name="System Admin",
                phone="0000000000",
                role=UserRole.ADMIN,
                is_active=True,
                is_senior_citizen=False,
                is_vip=False
            )
            db.add(admin)
            db.commit()
            print("[Seed] Admin user created — username: admin, password: admin123")
        else:
            print("[Seed] Admin user already exists — skipping.")
    except Exception as e:
        print(f"[Seed] Admin seed error: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin_user()           # ← ensure admin always exists
    predictor.train_initial_model()
    scheduler.add_job(run_expiry_check,     'interval', minutes=5,        id='expiry')
    scheduler.add_job(run_daily_activation, 'cron',     hour=0, minute=1, id='activate')
    scheduler.start()
    print("[Scheduler] Started — expiry every 5min, activation at 00:01")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="SmartQueue AI", version="2.0.0",
    description="AI Queue Management — Healthcare & Banking",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://smart-queue-ai.vercel.app"
    ], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["Auth"])
app.include_router(tokens.router,      prefix="/api/tokens",      tags=["Tokens"])
app.include_router(queues.router,      prefix="/api/queues",      tags=["Queues"])
app.include_router(healthcare.router,  prefix="/api/healthcare",  tags=["Healthcare"])
app.include_router(banking.router,     prefix="/api/banking",     tags=["Banking"])
app.include_router(analytics.router,   prefix="/api/analytics",   tags=["Analytics"])
app.include_router(admin.router,       prefix="/api/admin",       tags=["Admin"])
app.include_router(slots_router,       prefix="/api/slots",       tags=["Slots"])
app.include_router(grievance_router,   prefix="/api/grievance",   tags=["Grievance"])


@app.get("/")
async def root():
    return {"message": "SmartQueue AI", "version": "2.0.0", "status": "operational"}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client {client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)