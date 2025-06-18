from features.youtube_search import get_youtube_metadata

url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example video
info = get_youtube_metadata(url)
print("YouTube Metadata:\n", info)

