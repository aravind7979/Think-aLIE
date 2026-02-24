import os
import uvicorn
import requests
import google.generativeai as genai
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt


# --- DB & MODELS ---
from . import database
from .models import Chat, Message
from .media_projects import router as media_projects_router


# =================================================
# ENV CONFIG
# =================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL not set")

JWKS_URL = f"{SUPABASE_URL}/auth/v1/keys"

try:
    JWKS = requests.get(JWKS_URL).json()
except Exception as e:
    raise RuntimeError(f"Failed to fetch Supabase JWKS: {e}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

security = HTTPBearer()


# =================================================
# FASTAPI APP
# =================================================

app = FastAPI()


# =================================================
# STARTUP
# =================================================

@app.on_event("startup")
def startup():
    database.init_db(raise_on_error=True)
    print("✅ Database connected")


# =================================================
# CORS
# =================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "https://your-app.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =================================================
# STATIC FILES
# =================================================

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# =================================================
# ROUTERS
# =================================================

app.include_router(media_projects_router, tags=["user"])


# =================================================
# DB DEPENDENCY
# =================================================

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =================================================
# SUPABASE AUTH VERIFICATION
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

    return user_id  # Supabase UUID


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
        "status": "Think-LIE backend is live",
        "version": "3.0.0",
    }


# =================================================
# 1️⃣ CREATE CHAT
# =================================================

@app.post("/chats")
def create_chat(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_chat = Chat(user_id=user_id, title="New Chat")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {"chat_id": str(new_chat.id)}


# =================================================
# 2️⃣ LIST USER CHATS
# =================================================

@app.get("/chats")
def list_chats(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(chat.id),
            "title": chat.title,
            "created_at": chat.created_at,
        }
        for chat in chats
    ]


# =================================================
# 3️⃣ GET MESSAGES OF A CHAT
# =================================================

@app.get("/chats/{chat_id}/messages")
def get_messages(
    chat_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id,
            Message.user_id == user_id
        )
        .order_by(Message.created_at)
        .all()
    )

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]


# =================================================
# 4️⃣ SEND MESSAGE (ChatGPT-style)
# =================================================

@app.post("/chats/{chat_id}/message")
def send_message(
    chat_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Save user message
    user_msg = Message(
        chat_id=chat_id,
        user_id=user_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.commit()

    # Get full chat history for context
    history = (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id,
            Message.user_id == user_id
        )
        .order_by(Message.created_at)
        .all()
    )

    context = "\n".join(
        [f"{m.role}: {m.content}" for m in history]
    )

    # Generate AI response
    if not client:
        ai_response = "Gemini API not configured."
    else:
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=context,
            )
            ai_response = response.text
        except Exception as e:
            ai_response = f"[Gemini Error] {str(e)}"

    # Save assistant response
    assistant_msg = Message(
        chat_id=chat_id,
        user_id=user_id,
        role="assistant",
        content=ai_response,
    )
    db.add(assistant_msg)
    db.commit()

    return {"reply": ai_response}


# =================================================
# ENTRYPOINT
# =================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)