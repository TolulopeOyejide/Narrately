"""FastAPI backend for Narrately.

Serves the JSON API the web frontend (in ``web/``) talks to, and serves
the frontend itself as static files.

Run with::

    uvicorn narrately.api:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from .captioner import CaptionGenerationError, ImageCaptioner
from .web_scraper import extract_image_urls

app = FastAPI(title="Narrately")

# Frontend runs from a static HTML/CSS/JS page; loosen CORS so it can be
# served from a different origin/port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_captioner: ImageCaptioner | None = None


def get_captioner() -> ImageCaptioner:
    """Lazily load the model on first request instead of at import time.

    Keeps `uvicorn --reload` and the OpenAPI docs fast to load; the model
    is still only ever loaded once, on the first captioning request.
    """
    global _captioner
    if _captioner is None:
        _captioner = ImageCaptioner()
    return _captioner


class UrlRequest(BaseModel):
    url: str = Field(..., description="Direct URL to an image")


class WebpageRequest(BaseModel):
    url: str = Field(..., description="URL of the webpage to scan")
    limit: int = Field(8, ge=1, le=30, description="Max number of images to caption")


class CaptionResponse(BaseModel):
    caption: str


class WebpageResult(BaseModel):
    image_url: str
    caption: str


class WebpageResponse(BaseModel):
    results: list[WebpageResult]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/caption/image", response_model=CaptionResponse)
async def caption_image(file: UploadFile = File(...)) -> CaptionResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        image = Image.open(file.file)
        caption = get_captioner().caption(image)
    except CaptionGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CaptionResponse(caption=caption)


@app.post("/api/caption/url", response_model=CaptionResponse)
def caption_url(payload: UrlRequest) -> CaptionResponse:
    caption = get_captioner().caption_url(payload.url)
    if caption is None:
        raise HTTPException(
            status_code=422, detail="Could not generate a caption for that URL."
        )
    return CaptionResponse(caption=caption)


@app.post("/api/caption/webpage", response_model=WebpageResponse)
def caption_webpage(payload: WebpageRequest) -> WebpageResponse:
    try:
        image_urls = extract_image_urls(payload.url)[: payload.limit]
    except Exception as exc:  # noqa: BLE001 - surface as a client-facing error
        raise HTTPException(status_code=422, detail=f"Could not read that page: {exc}") from exc

    captioner = get_captioner()
    results = []
    for image_url in image_urls:
        caption = captioner.caption_url(image_url)
        if caption:
            results.append(WebpageResult(image_url=image_url, caption=caption))

    return WebpageResponse(results=results)


# --- Static frontend -------------------------------------------------------
_web_dir = Path(__file__).resolve().parent.parent.parent / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=_web_dir, html=True), name="frontend")
