import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Optional

# --- DB & ROUTERS ---
from database import Base, engine, SessionLocal
from auth import router as auth_router
from models import User, ChatMessage

# Load environment variables
load_dotenv()

# --- GEMINI CONFIG (CORRECT SDK USAGE) ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

genai.configure(api_key=api_key)

# Use a stable model supported by google-generativeai
model = genai.GenerativeModel("gemini-pro")

# --- FASTAPI APP ---
app = FastAPI(title="Think-LIE Backend")

# --- CREATE DATABASE TABLES ---
Base.metadata.create_all(bind=engine)

# --- CORS CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTERS ---
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# --- DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = parts[1]
        SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- SCHEMAS ---
class ChatRequest(BaseModel):
    message: str

# --- ROOT ---
@app.get("/")
def root():
    return {
        "status": "Think-LIE backend is live and running",
        "version": "1.0.0"
    }

# --- CHAT ENDPOINT ---
@app.post("/chat")
def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save user message
    user_message = ChatMessage(
        user_id=user.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()

    # Generate AI response (CORRECT GEMINI CALL)
    try:
        response = model.generate_content(request.message)
        ai_response = response.text
    except Exception as e:
        ai_response = f"[Think-LIE Error] {str(e)}"

    # Save assistant message
    assistant_message = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=ai_response
    )
    db.add(assistant_message)
    db.commit()

    return {"reply": ai_response}

# --- CHAT HISTORY ---
@app.get("/chat/history")
def get_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

# --- CLEAR CHAT ---
@app.delete("/chat/clear")
def clear_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"message": "Chat history cleared successfully"}

# --- HF ENTRYPOINT ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)