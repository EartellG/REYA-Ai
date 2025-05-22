from features.web_search import search_web
from voice.tts import speak

query = "What is the capital of Ghana?"
result = search_web(query)
print(f"📄 Result: {result}")
speak(result)
