import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

# Load environment variables (locally from .env, on HF from 'Secrets')
load_dotenv()

# Initialize Gemini client
# Note: On Hugging Face, ensure you added GEMINI_API_KEY in Settings > Secrets
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

app = FastAPI()

# --- 1. CONFIGURE CORS ---
# This allows your GitHub Pages frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For testing, "*" allows all. Replace with your GitHub URL for better security.
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat schema
class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "Think-LIE backend is live and running"}

# --- 2. CHAT ENDPOINT ---
@app.post("/chat")
def chat(request: ChatRequest):
    # Mock mode if API key missing
    if not client:
        return {
            "reply": "[MOCK AI] Think-LIE: Please set your Gemini API Key in the backend secrets."
        }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request.message
        )

        return {
            "reply": response.text
        }

    except Exception as e:
        return {
            "reply": f"[Think-LIE Error]: {str(e)}"
        }

# --- 3. CONFIGURE FOR HUGGING FACE ---
if __name__ == "__main__":
    # Port 7860 is mandatory for Hugging Face Spaces
    uvicorn.run(app, host="0.0.0.0", port=7860)