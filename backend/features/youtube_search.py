import yt_dlp

def get_youtube_metadata(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "description": info.get("description")[:300] + "...",
                "duration": info.get("duration_string")
            }
        except Exception:
            return "Could not retrieve YouTube metadata."
