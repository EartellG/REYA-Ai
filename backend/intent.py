def recognize_intent(command):
    command = command.lower()

    if "exit" in command or "quit" in command:
        return "exit"
    elif "hello" in command or "hi" in command:
        return "greeting"
    elif "stackoverflow" in command or "how to" in command or "error" in command:
        return "stackoverflow_help"
    elif "youtube" in command and ("link" in command or "video" in command or "metadata" in command):
        return "youtube_info"
    elif "reddit" in command:
        return "reddit_search"
    elif "who is" in command or "what is" in command:
        return "web_search"
    else:
        return "web_search"
