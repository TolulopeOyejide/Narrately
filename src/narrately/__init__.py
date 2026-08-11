"""Narrately.

A small, self-contained toolkit built on Salesforce's BLIP model for
generating natural-language captions for images — from a local file,
a direct image URL, or every image on a webpage.
"""

from .captioner import ImageCaptioner
from .web_scraper import extract_image_urls

__version__ = "1.0.0"
__all__ = ["ImageCaptioner", "extract_image_urls"]
