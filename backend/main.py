from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from google import genai

# Load environment variables
load_dotenv()

# Initialize Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Think-LIE backend running (Gemini)"}

# ----- Chat schema -----
class ChatRequest(BaseModel):
    message: str

# ----- Chat endpoint -----
@app.post("/chat")
def chat(request: ChatRequest):

    # Mock mode if API key missing
    if not os.getenv("GEMINI_API_KEY"):
        return {
            "reply": "[MOCK AI] Arrays store elements in contiguous memory locations."
        }

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=request.message
        )

        return {
            "reply": response.text
        }

    except Exception:
        return {
            "reply": "[MOCK AI] Gemini API unavailable or quota exceeded."
        }