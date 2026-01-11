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
    if os.getenv("OPENAI_API_KEY") is None:
        return {
            "reply": "[MOCK AI] Arrays store elements in contiguous memory."
        }

    try:
        response = client.responses.create(
            model="gpt-5-nano",
            input=request.message
        )
        return {"reply": response.output_text}
    except Exception:
        return {
            "reply": "[MOCK AI] AI quota unavailable. Continue learning arrays."
        }