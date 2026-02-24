import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import database
from .schemas import SignupRequest, LoginRequest, TokenResponse
from .security import hash_password, verify_password, create_access_token


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

router = APIRouter()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token
    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(access_token=access_token, email=user.email)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        },
        json={
            "email": req.email,
            "password": req.password
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    data = response.json()

    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "email": req.email
    }