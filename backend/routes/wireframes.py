# backend/routes/wireframes.py
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pathlib import Path
from uuid import uuid4
from typing import Optional
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import time
import os

router = APIRouter(prefix="/wireframes", tags=["wireframes"])

# where wireframes live (and are served via app.mount("/static", ...))
STATIC_DIR = Path("static/wireframes")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
ALLOWED_EXT  = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_BYTES    = 10 * 1024 * 1024  # 10 MB

def _infer_ext_with_pillow(data: bytes, fallback_name: str) -> str:
    """
    Try to determine extension using Pillow; fallback to filename or .png.
    Note: Pillow does not parse SVG (text XML), so we don't try it here.
    """
    # filename hint first
    lower = (fallback_name or "").lower()
    for ext in ALLOWED_EXT:
        if lower.endswith(ext):
            return ext

    # binary sniff
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt == "PNG":
                return ".png"
            if fmt in ("JPEG", "JPG"):
                return ".jpg"
            if fmt == "WEBP":
                return ".webp"
            # add more if you need (BMP, GIF …) and allow them above
    except UnidentifiedImageError:
        pass

    # final default
    return ".png"

def _looks_like_svg(data: bytes) -> bool:
    # quick check: XML + <svg
    head = data[:4096].decode("utf-8", errors="ignore")
    return "<svg" in head.lower()

@router.post("/upload")
async def upload_wireframe(
    file: UploadFile = File(...),
    project_id: str = Form(default="default")
):
    try:
        # quick MIME allowlist
        if file.content_type not in ALLOWED_MIME:
            return JSONResponse(
                {"detail": f"Unsupported type: {file.content_type}. Allowed: {sorted(ALLOWED_MIME)}"},
                status_code=415,
            )

        data = await file.read()
        if len(data) > MAX_BYTES:
            return JSONResponse({"detail": "File too large (max 10 MB)."}, status_code=413)

        # Decide extension
        if file.content_type == "image/svg+xml" or _looks_like_svg(data):
            ext = ".svg"
        else:
            ext = _infer_ext_with_pillow(data, file.filename or "")

        # name & write
        stamp = int(time.time())
        name = f"{project_id}_{uuid4().hex}_{stamp}{ext}"
        out_path = UPLOAD_DIR / name
        out_path.write_bytes(data)

        # Return URL path (served from /static)
        return {"url": f"/static/wireframes/uploads/{name}", "size": len(data), "content_type": file.content_type}
    except Exception as e:
        return JSONResponse({"detail": f"Upload failed: {e}"}, status_code=500)
