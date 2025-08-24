from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from fastapi.responses import StreamingResponse
from backend.voice.edge_tts import speak_with_voice_style
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

class SpeakRequest(BaseModel):
    message: str

@app.post("/speak")
async def speak_endpoint(data: SpeakRequest):
    text = (data.message or "").strip()
    if not text:
        return {"ok": False, "error": "Empty message"}
    # run TTS off the event loop so we don't block FastAPI
    asyncio.create_task(asyncio.to_thread(speak_with_voice_style, text, reya))
    return {"ok": True}

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()

    if "run diagnostics" in user_message.lower():
        # Perform diagnostic scan
        def run_diagnostics():
            results = []
            try:
                # Test personality
                results.append(f"🧠 Personality loaded: Traits={reya.traits}, Style={reya.style}")

                # Test memory
                context_test = memory.get_context()
                results.append("💾 Memory context accessible ✅")

                # Test LLM call
                prompt = get_structured_reasoning_prompt("test diagnostics", context_test, reya=reya)
                response = query_ollama(prompt)
                results.append("📡 LLM response received ✅")

                # Test memory saving
                memory.remember("diagnostics check", response)
                results.append("📘 Memory save successful ✅")

                return "\n".join(results)

            except Exception as e:
                return f"❌ Diagnostics failed with error:\n{e}"

        diagnostics_report = run_diagnostics()

        async def stream_report():
            for line in diagnostics_report.split("\n"):
                yield line + "\n"
                await asyncio.sleep(0.1)  # ✅ Non-blocking sleep

        return StreamingResponse(stream_report(), media_type="text/plain")

    # ✨ Normal REYA response flow
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)
    full_response = query_ollama(prompt)
    memory.remember(user_message, full_response)

    async def generate_stream():
        for word in full_response.split():
            yield f"{word} "
            await asyncio.sleep(0.05)  # ✅ Non-blocking sleep

    return StreamingResponse(generate_stream(), media_type="text/plain")



# Routes
@app.get("/status")
def status():
    return {"status": "REYA backend is running."}

@app.post("/reya/respond")
def respond_endpoint(data: MessageRequest):
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


# ✨ Normal REYA response flow
context = memory.get_context()
prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)
full_response = query_ollama(prompt)
memory.remember(user_message, full_response)

# 🔊 Speak without blocking the stream
asyncio.create_task(asyncio.to_thread(speak_with_voice_style, full_response, reya))

async def generate_stream():
    for word in full_response.split():
        yield f"{word} "
        await asyncio.sleep(0.05)
    return StreamingResponse(generate_stream(), media_type="text/plain")




#Use cases and calls

result = search_stackoverflow("Search Stackoverflow for?")

result = get_youtube_metadata("search youtube for?")

result = search_reddit("search reddit for?")

result = search_web("search web for?")   