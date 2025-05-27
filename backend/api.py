from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from llm_interface import get_response, get_structured_reasoning_prompt, query_ollama
from features.advanced_features import ContextualMemory
from intent import recognize_intent
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web

# Initialize app
app = FastAPI()

# CORS for local React frontend (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Personality and memory
reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
)
memory = ContextualMemory()

# Request models
class MessageRequest(BaseModel):
    message: str

# Routes
@app.get("/status")
def status():
    return {"status": "REYA backend is running."}

@app.post("/reya/respond")
def chat_endpoint(data: MessageRequest):
    user_input = data.message
    intent = recognize_intent(user_input)
    context = memory.get_context()
    response = get_response(user_input, reya, context)
    memory.update_context(user_input, response)
    return {"response": response}

@app.post("/reya/logic")
def logic_layer(data: MessageRequest):
    prompt = get_structured_reasoning_prompt(data.message)
    response = query_ollama(prompt)
    return {"response": response}

@app.post("/reya/project")
def multimodal_project_handler(data: MessageRequest):
    # You can later branch based on filetypes, etc.
    return {"response": f"Multimodal handler received: {data.message}"}
