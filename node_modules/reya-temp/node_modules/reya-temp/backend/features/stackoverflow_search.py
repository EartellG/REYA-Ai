from duckduckgo_search import DDGS

def search_stackoverflow(query):
    search_query = f"{query} site:stackoverflow.com"
    with DDGS() as ddgs:
        results = ddgs.text(search_query)
        for r in results:
            if r.get("body"):
                return r["body"]
        return "No helpful StackOverflow results found."
