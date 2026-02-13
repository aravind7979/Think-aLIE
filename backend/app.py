import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import google.generativeai as genai
from jose import jwt, JWTError
from sqlalchemy.orm import Session

# --- DB & ROUTERS ---
from . import database
from .auth.router import router as auth_router
from .media_projects import router as media_projects_router
from .models import User, ChatMessage

# -------------------------------------------------
# GEMINI CONFIG (SAFE FOR HUGGING FACE)
# -------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")
else:
    model = None  # backend must still run

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI()

# -------------------------------------------------
# STARTUP EVENT (DB SAFE INIT)
# -------------------------------------------------
@app.on_event("startup")
def startup():
    # Initialize DB engine lazily. If unreachable, log and continue so the
    # app doesn't crash during deploy where the DB may be temporarily
    # unreachable. Set raise_on_error=True if you want to fail fast.
    database.init_db(raise_on_error=False)
    if not database.engine:
        # Database not initialized; skip create_all and allow app to start.
        return

    try:
        database.Base.metadata.create_all(bind=database.engine)
        print("✅ Database initialized")
    except Exception as e:
        # Log but don't crash the whole app on transient DB errors at startup
        print(f"⚠️ Database initialization warning: {e}")

# -------------------------------------------------
# CORS
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# SERVE UPLOADED FILES
# -------------------------------------------------
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# -------------------------------------------------
# ROUTERS
# -------------------------------------------------
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(media_projects_router, tags=["user"])
 

# -------------------------------------------------
# DEPENDENCIES
# -------------------------------------------------
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        token = parts[1]
        SECRET = os.getenv("JWT_SECRET", "change-this-secret")
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------------------------------
# SCHEMAS
# -------------------------------------------------
class ChatRequest(BaseModel):
    message: str


# -------------------------------------------------
# ROOT
# -------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "Think-LIE backend is live",
        "version": "1.0.0",
    }


# -------------------------------------------------
# CHAT ENDPOINT
# -------------------------------------------------
@app.post("/chat")
def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Save user message
    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.commit()

    # Generate AI response
    if not model:
        ai_response = "[Think-LIE] Gemini API key not configured."
    else:
        try:
            response = model.generate_content(request.message)
            ai_response = response.text
        except Exception as e:
            ai_response = f"[Think-LIE Error] {str(e)}"

    # Save assistant message
    assistant_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=ai_response,
    )
    db.add(assistant_msg)
    db.commit()

    return {"reply": ai_response}


# -------------------------------------------------
# CHAT HISTORY
# -------------------------------------------------
@app.get("/chat/history")
def get_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
    }


# -------------------------------------------------
# CLEAR CHAT
# -------------------------------------------------
@app.delete("/chat/clear")
def clear_chat_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"message": "Chat history cleared successfully"}


# -------------------------------------------------
# HUGGING FACE ENTRYPOINT
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)