# Narrately

Generate natural-language captions for images using Salesforce's [BLIP](https://arxiv.org/abs/2201.12086) model — from a local file, a direct image URL, or every image on a webpage.

## Features

- **Local images** — caption any file on disk.
- **Webpage scraping** — point it at a URL and it captions every meaningful image found on the page (filtering out icons, tracking pixels, and SVGs).
- **Web UI** — a plain HTML/CSS/JS frontend (no framework) talking to a FastAPI backend, with tabs for image upload and webpage scanning.
- **CLI** — the same functionality from the command line, for scripting and batch jobs.
- Model is loaded **once** and shared across the CLI, the API, and the library — no duplicate model downloads or memory.

## Project structure

```
narrately/
├── src/narrately/
│   ├── captioner.py       # BLIP model loading + inference (ImageCaptioner)
│   ├── web_scraper.py     # extract_image_urls() — pull <img> URLs from a page
│   ├── cli.py              # `narrately` command-line entry point
│   └── api.py              # FastAPI backend — serves the JSON API + the web/ frontend
├── web/                     # static frontend (HTML/CSS/JS, no build step)
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── tests/
│   └── test_web_scraper.py
├── data/sample.jpg         # sample image for trying things out
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/TolulopeOyejide/narrately.git 
cd narrately
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage

### Web app

```bash
uvicorn narrately.api:app --reload
```

Opens at `http://127.0.0.1:8000` — FastAPI serves both the JSON API and the static frontend in `web/` from the same origin, so no separate frontend server or build step is needed. Two tabs: upload an image, or paste a webpage URL to caption every image on it.

**API endpoints**, if you want to call the backend directly or build another frontend against it:

| Method | Path                    | Body                              |
|--------|--------------------------|------------------------------------|
| GET    | `/api/health`            | —                                   |
| POST   | `/api/caption/image`     | multipart file upload (`file`)     |
| POST   | `/api/caption/url`       | `{"url": "..."}`                   |
| POST   | `/api/caption/webpage`   | `{"url": "...", "limit": 8}`       |

Interactive docs are auto-generated at `/docs`.

### Command line

```bash
# Caption a local file
narrately image data/sample.jpg

# Caption a single image URL
narrately url https://example.com/photo.jpg

# Caption every image on a webpage, writing results to captions.txt
narrately webpage https://example.com --output captions.txt --limit 10
```

### As a library

```python
from narrately import ImageCaptioner

captioner = ImageCaptioner()  # defaults to blip-image-captioning-base
print(captioner.caption("data/sample.jpg"))
print(captioner.caption_url("https://example.com/photo.jpg"))
```

Use the larger, more accurate checkpoint if latency isn't a concern:

```python
captioner = ImageCaptioner(model_name="Salesforce/blip-image-captioning-large")
```

## Docker

```bash
docker build -t narrately .
docker run -p 8000:8000 narrately
```

Then open `http://127.0.0.1:8000`.

## Development

```bash
pip install -r requirements-dev.txt
pip install -e .
ruff check src tests   # lint
pytest                 # test
```

CI (`.github/workflows/ci.yml`) runs lint and tests on every push and pull request.

## Notes on the model

Captioning runs locally via Hugging Face `transformers` — no API key needed, but the first run downloads the BLIP checkpoint (~1 GB for the base model) from the Hugging Face Hub. Inference runs on GPU (CUDA), Apple Silicon (MPS), or CPU automatically, whichever is available.

## License

[MIT](LICENSE)

---
Developed by [Tolulope Oyejide](https://github.com/TolulopeOyejide)
