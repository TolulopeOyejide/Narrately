"""Extract candidate image URLs from a webpage."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
SKIP_SUBSTRINGS = ("svg", "1x1")


def extract_image_urls(page_url: str, timeout: int = DEFAULT_TIMEOUT) -> list[str]:
    """Return absolute, likely-meaningful image URLs found on ``page_url``.

    Filters out SVGs, 1x1 tracking pixels, and relative/data URLs that
    can't be resolved without also knowing the page's base URL.
    """
    response = requests.get(page_url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    valid_urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if any(marker in src for marker in SKIP_SUBSTRINGS):
            continue

        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith(("http://", "https://")):
            continue

        valid_urls.append(src)

    logger.info("Found %d candidate image(s) on %s", len(valid_urls), page_url)
    return valid_urls
