from llm_interface import classify_intent

test_phrases = [
    "Take a note to call mom",
    "Remind me to feed the cat at 6pm",
    "What's the weather like today?",
    "Hi there!",
    "Quit the assistant"
]

for phrase in test_phrases:
    intent = classify_intent(phrase)
    print(f"Input: {phrase} → Intent: {intent}")
