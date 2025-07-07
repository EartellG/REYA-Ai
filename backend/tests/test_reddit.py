from features.reddit_search import search_reddit

query = "GPT-4 release site:reddit.com"
result = search_reddit(query)
print("Reddit Search Result:\n", result)
