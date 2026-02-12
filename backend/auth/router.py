from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from .schemas import SignupRequest, LoginRequest, TokenResponse
from .security import hash_password, verify_password, create_access_token

router = APIRouter()

def get_db():
    db = SessionLocal()
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
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login existing user"""
    # Find user
    user = db.query(User).filter(User.email == req.email).first()
    
    # Verify password
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create access token
    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(access_token=access_token, email=user.email)