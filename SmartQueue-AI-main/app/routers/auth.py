from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas import UserCreate, Token
from app.models import User
from app.auth.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash
)

router = APIRouter()


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_senior_citizen=user.is_senior_citizen,
        is_vip=user.is_vip
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}


@router.post("/login", response_model=Token)
def login(
    data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, data.username, data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.username})

    # 🔥 IMPORTANT CHANGE: return user_id
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id   # 🔥 needed for WebSocket
    }


@router.post("/seed-admin")
def seed_admin(db: Session = Depends(get_db)):
    """
    One-time endpoint to create the default admin user on the server.
    Safe to call multiple times — idempotent.
    """
    import traceback
    from app.models import UserRole
    from app.database.db import engine, Base
    from app.models import Base as ModelBase

    try:
        # Ensure all tables exist (important on fresh Render DB)
        ModelBase.metadata.create_all(bind=engine)

        existing = db.query(User).filter(User.username == "admin").first()
        # Hardcoded bcrypt hash for "admin123" to bypass passlib 72-byte bug on Render
        admin_hash = "$2b$12$W44EQGxjBISmmQQCZ1EKsu1v8DpiiPwtQVAcriNPlxJZm6agpOu6a"
        
        if existing:
            existing.role = UserRole.ADMIN
            existing.hashed_password = admin_hash
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return {
                "status": "updated",
                "message": "Admin user already exists — role enforced and password reset to admin123",
                "username": "admin"
            }

        admin = User(
            username="admin",
            email="admin@smartqueue.ai",
            hashed_password=admin_hash,
            full_name="System Admin",
            phone="0000000000",
            role=UserRole.ADMIN,
            is_active=True,
            is_senior_citizen=False,
            is_vip=False
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return {
            "status": "created",
            "message": "Admin user created successfully",
            "username": "admin",
            "password": "admin123"
        }

    except Exception as e:
        db.rollback()
        error_detail = traceback.format_exc()
        print(f"[seed-admin ERROR] {error_detail}")
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")