import os
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError

# -----------------------------
# Supabase Config
# -----------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL environment variable not set")

JWKS_URL = f"{SUPABASE_URL}/auth/v1/keys"

# Fetch JWKS once at startup
jwks_response = requests.get(JWKS_URL)
if jwks_response.status_code != 200:
    raise RuntimeError("Failed to fetch Supabase JWKS")

JWKS = jwks_response.json()

# -----------------------------
# Verify Supabase JWT
# -----------------------------
def verify_supabase_token(token: str):
    try:
        payload = jwt.decode(
            token,
            JWKS,
            algorithms=["RS256"],
            audience="authenticated",  # Supabase audience
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

# -----------------------------
# FastAPI Dependency
# -----------------------------
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    payload = verify_supabase_token(token)

    user_id = payload.get("sub")  # Supabase user UUID

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )

    return user_id