from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Think-LIE backend running"}

# ----- Chat schema -----
class ChatRequest(BaseModel):
    message: str

# ----- Chat endpoint -----
@app.post("/chat")
def chat(request: ChatRequest):

    # Explicit mock mode if key missing
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "reply": "[MOCK AI] Arrays are collections of elements stored contiguously in memory."
        }

    try:
        response = client.responses.create(
            model="gpt-5-nano",
            input=request.message
        )
        return {
            "reply": response.output_text
        }

    except Exception as e:
        # Covers quota exceeded, network issues, OpenAI downtime
        return {
            "reply": "[MOCK AI] AI service temporarily unavailable. Backend is running correctly."
        }
