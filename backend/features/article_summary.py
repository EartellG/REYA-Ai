import requests
from readability import Document

def summarize_article(url):
    try:
        response = requests.get(url)
        doc = Document(response.text)
        title = doc.title()
        summary = doc.summary()
        return f"{title}\n{summary[:500]}..."  # Truncate for speaking
    except Exception:
        return "Couldn't summarize the article."
