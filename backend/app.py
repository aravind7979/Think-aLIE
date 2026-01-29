import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
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

# Initialize Gemini client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Create FastAPI app
app = FastAPI(title="Think-LIE Backend")

# --- CREATE DATABASE TABLES ---
Base.metadata.create_all(bind=engine)

# --- CORS CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
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

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Verify JWT token from Authorization header and return user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# --- SCHEMAS ---
class ChatRequest(BaseModel):
    message: str

# --- ROOT ---
@app.get("/")
def root():
    return {"status": "Think-LIE backend is live and running", "version": "1.0.0"}

# --- CHAT ENDPOINT (matches your original structure) ---
@app.post("/chat")
def chat(request: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send a message and get AI response"""
    
    # Save user message to database
    user_message = ChatMessage(
        user_id=user.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()
    
    # Get AI response
    if not client:
        ai_response = f"[Think-LIE] I received your message: '{request.message}'. However, Gemini API key is not configured."
    else:
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=request.message
            )
            ai_response = response.text
        except Exception as e:
            ai_response = f"[Think-LIE Error]: {str(e)}"
    
    # Save AI response to database
    assistant_message = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=ai_response
    )
    db.add(assistant_message)
    db.commit()
    
    return {"reply": ai_response}

# --- GET CHAT HISTORY ---
@app.get("/chat/history")
def get_chat_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get chat history for the current user"""
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == user.id
    ).order_by(ChatMessage.created_at).all()
    
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

# --- CLEAR CHAT HISTORY ---
@app.delete("/chat/clear")
def clear_chat_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Clear all chat messages for the current user"""
    
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    
    return {"message": "Chat history cleared successfully"}

# --- HF ENTRYPOINT ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)