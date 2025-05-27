from duckduckgo_search import DDGS

def search_reddit(query):
    search_query = f"{query} site:reddit.com"
    with DDGS() as ddgs:
        results = ddgs.text(search_query)
        for r in results:
            if r.get("body"):
                return r["body"]
        return "No relevant Reddit threads found."
