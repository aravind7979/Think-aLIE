import os
import requests
from google import genai
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt
from supabase import create_client, Client
from auth.router import router as auth_router


# =================================================
# ENV CONFIG
# =================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase environment variables not set")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)

JWKS_URL = f"{SUPABASE_URL}/auth/v1/keys"

try:
    JWKS = requests.get(JWKS_URL).json()
except Exception as e:
    raise RuntimeError(f"Failed to fetch Supabase JWKS: {e}")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai.GenerativeModel('gemini-1.5-flash')
else:
    client = None

security = HTTPBearer()


# =================================================
# FASTAPI APP
# =================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "https://your-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router, prefix="/auth", tags=["auth"])


# =================================================
# AUTH
# =================================================

def verify_supabase_token(token: str):
    try:
        payload = jwt.decode(
            token,
            JWKS,
            algorithms=["RS256"],
            audience="authenticated",
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = verify_supabase_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user_id


# =================================================
# SCHEMAS
# =================================================

class ChatRequest(BaseModel):
    message: str


# =================================================
# ROOT
# =================================================

@app.get("/")
def root():
    return {
        "status": "Backend live (Supabase edition)",
        "version": "4.0.0",
    }


# =================================================
# 1️⃣ CREATE CHAT
# =================================================

@app.post("/chats")
def create_chat(user_id: str = Depends(get_current_user)):

    data = {
        "user_id": user_id,
        "title": "New Chat",
    }

    response = supabase.table("chats").insert(data).execute()

    if not response.data:
        raise HTTPException(status_code=400, detail="Failed to create chat")

    return {"chat_id": response.data[0]["id"]}


# =================================================
# 2️⃣ LIST USER CHATS
# =================================================

@app.get("/chats")
def list_chats(user_id: str = Depends(get_current_user)):

    response = (
        supabase.table("chats")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data


# =================================================
# 3️⃣ GET MESSAGES
# =================================================

@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str, user_id: str = Depends(get_current_user)):

    response = (
        supabase.table("messages")
        .select("*")
        .eq("chat_id", chat_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )

    return response.data


# =================================================
# 4️⃣ SEND MESSAGE
# =================================================

@app.post("/chats/{chat_id}/message")
def send_message(
    chat_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):

    # Save user message
    supabase.table("messages").insert({
        "chat_id": chat_id,
        "user_id": user_id,
        "role": "user",
        "content": request.message,
    }).execute()

    # Fetch full chat history
    history_response = (
        supabase.table("messages")
        .select("*")
        .eq("chat_id", chat_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )

    history = history_response.data

    context = "\n".join(
        [f"{m['role']}: {m['content']}" for m in history]
    )

    # Generate AI response
    if not client:
        ai_response = "Gemini API not configured."
    else:
        try:
            response = client.generate_content(context)
            ai_response = response.text
        except Exception as e:
            ai_response = f"[Gemini Error] {str(e)}"

    # Save assistant message
    supabase.table("messages").insert({
        "chat_id": chat_id,
        "user_id": user_id,
        "role": "assistant",
        "content": ai_response,
    }).execute()

    return {"reply": ai_response}