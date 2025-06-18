from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from time import sleep
from fastapi.responses import StreamingResponse

from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.llm_interface import get_response, get_structured_reasoning_prompt, query_ollama
from backend.features.advanced_features import ContextualMemory
from backend.intent import recognize_intent
from backend.features.stackoverflow_search import search_stackoverflow
from backend.features.youtube_search import get_youtube_metadata
from backend.features.reddit_search import search_reddit
from backend.features.web_search import search_web

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

# Test route
@app.get("/ping")
def ping():
    return {"message": "Pong from REYA backend!"}

# Chat route
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "")

    async def generate_stream():
        reply = f"Hi there! You said: {user_message}. This is REYA responding in a stream..."
        for word in reply.split():
            yield f"{word} "
            sleep(0.15)  # Simulate typing delay

    return StreamingResponse(generate_stream(), media_type="text/plain")

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
    context = memory.get_context()  # get recent memory context
    prompt = get_structured_reasoning_prompt(data.message, context, reya=reya)
    response = query_ollama(prompt)
    return {"response": response}


@app.post("/reya/project")
def multimodal_project_handler(data: MessageRequest):
    # You can later branch based on filetypes, etc.
    return {"response": f"Multimodal handler received: {data.message}"}

from fastapi.responses import JSONResponse

@app.get("/")
async def root():
    return JSONResponse(content={"message": "REYA API is running!"})