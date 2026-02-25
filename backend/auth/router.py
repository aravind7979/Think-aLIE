import os
import requests
from fastapi import APIRouter, HTTPException
from .schemas import SignupRequest, LoginRequest, TokenResponse


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

router = APIRouter()

@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest):
    """Register a new user with Supabase"""
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
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
        error_data = response.json()
        raise HTTPException(status_code=400, detail=error_data.get("msg", "Signup failed"))

    data = response.json()

    return {
        "access_token": data["access_token"],
        "token_type": "bearer",
        "email": req.email
    }

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Login user with Supabase"""
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