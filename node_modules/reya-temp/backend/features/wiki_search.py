import wikipedia

def search_wikipedia(query):
    try:
        summary = wikipedia.summary(query, sentences=2)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple results found. Try being more specific: {e.options[:3]}"
    except wikipedia.exceptions.PageError:
        return "No page found for your query."
