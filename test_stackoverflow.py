from features.stackoverflow_search import search_stackoverflow

query = "How to reverse a list in python"
result = search_stackoverflow(query)
print("StackOverflow Search Result:\n", result)
