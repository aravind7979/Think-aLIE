from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session
import os
from . import database
from models import User

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
ALGO = "HS256"

# ---------- Schemas ----------
class Signup(BaseModel):
    email: EmailStr
    password: str

class Login(BaseModel):
    email: EmailStr
    password: str

# ---------- Database Dependency ----------
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Utils ----------
def hash_pw(pw):
    return pwd.hash(pw)

def verify_pw(pw, h):
    return pwd.verify(pw, h)

def create_token(user_id):
    return jwt.encode({"sub": str(user_id)}, SECRET, algorithm=ALGO)

# ---------- Routes ----------
@router.post("/signup")
def signup(data: Signup, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    new_user = User(
        email=data.email,
        password_hash=hash_pw(data.password)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"access_token": create_token(new_user.id), "user_id": new_user.id}

@router.post("/login")
def login(data: Login, db: Session = Depends(get_db)):
    # Get user from database
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_pw(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"access_token": create_token(user.id), "user_id": user.id}

@router.get("/verify")
def verify_token(token: str):
    """Verify if a token is valid"""
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return {"valid": True, "user_id": payload.get("sub")}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")