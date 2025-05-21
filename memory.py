# memory.py
class Memory:
    def __init__(self, max_items=10):
        self.history = []
        self.max_items = max_items

    def remember(self, user_input, assistant_response):
        self.history.append((user_input, assistant_response))
        if len(self.history) > self.max_items:
            self.history.pop(0)

    def recall(self):
        return self.history

memory = Memory()

# memory.py

class ContextualMemory:
    def __init__(self):
        self.history = []

    def remember(self, user_input, response):
        """Store the user input and assistant's response."""
        self.history.append({"user": user_input, "assistant": response})
        # Optional: keep memory to last N interactions (like 10)
        if len(self.history) > 10:
            self.history.pop(0)

    def recall(self):
        """Return the last few interactions as context string."""
        return "\n".join([f"User: {h['user']}\nREYA: {h['assistant']}" for h in self.history])
