import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def search(query):
    url = f"https://duckduckgo.com/html/?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    results = soup.select('.result__snippet')
    if results:
        return results[0].text.strip()
    return "I couldn't find anything."



def search_web(query):
    print(f"🔎 Searching: {query}")
    with DDGS() as ddgs:
        results = ddgs.text(query)
        for r in results:
            if r.get("body"):
                return r["body"]
        return "Sorry, I couldn't find anything."
