"""Core captioning logic built on the BLIP model family.

All model loading and inference lives here so it happens exactly once,
instead of being duplicated across a CLI script and a UI script (as in
the original version of this project).
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Union

import requests
import torch
from PIL import Image, UnidentifiedImageError
from transformers import BlipForConditionalGeneration, BlipProcessor

logger = logging.getLogger(__name__)

ImageInput = Union[str, Path, Image.Image]

# Images below this pixel area are almost always tracking pixels, icons,
# or decorative assets rather than meaningful photos.
MIN_IMAGE_AREA = 400

DEFAULT_MODEL = "Salesforce/blip-image-captioning-base"


class CaptionGenerationError(RuntimeError):
    """Raised when an image cannot be fetched, decoded, or captioned."""


class ImageCaptioner:
    """Loads a BLIP model once and generates captions for images.

    Parameters
    ----------
    model_name:
        Any BLIP checkpoint on the Hugging Face Hub, e.g.
        ``"Salesforce/blip-image-captioning-base"`` (fast, default) or
        ``"Salesforce/blip-image-captioning-large"`` (slower, higher quality).
    device:
        ``"cuda"``, ``"mps"``, or ``"cpu"``. Auto-detected if not given.
    request_timeout:
        Timeout in seconds for any HTTP fetch of a remote image.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        request_timeout: int = 15,
    ) -> None:
        self.model_name = model_name
        self.device = device or self._detect_device()
        self.request_timeout = request_timeout

        logger.info("Loading %s on %s ...", self.model_name, self.device)
        self.processor = BlipProcessor.from_pretrained(self.model_name)
        self.model = BlipForConditionalGeneration.from_pretrained(self.model_name).to(
            self.device
        )
        self.model.eval()
        logger.info("Model ready.")

    @staticmethod
    def _detect_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():  # Apple Silicon
            return "mps"
        return "cpu"

    def caption(self, image: ImageInput, max_new_tokens: int = 50) -> str:
        """Generate a caption for a local path, PIL image, or in-memory image."""
        pil_image = self._to_pil(image)
        return self._run_model(pil_image, max_new_tokens)

    def caption_url(self, image_url: str, max_new_tokens: int = 50) -> str | None:
        """Generate a caption for an image at a URL.

        Returns ``None`` (instead of raising) when the image is too small
        to be meaningful or cannot be decoded, since this is the common,
        expected case when scraping arbitrary webpages.
        """
        try:
            response = requests.get(image_url, timeout=self.request_timeout)
            response.raise_for_status()
            pil_image = Image.open(BytesIO(response.content))
        except (requests.RequestException, UnidentifiedImageError) as exc:
            logger.debug("Skipping %s: %s", image_url, exc)
            return None

        if pil_image.size[0] * pil_image.size[1] < MIN_IMAGE_AREA:
            return None

        return self._run_model(pil_image.convert("RGB"), max_new_tokens)

    def _run_model(self, pil_image: Image.Image, max_new_tokens: int) -> str:
        inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        return self.processor.decode(output_ids[0], skip_special_tokens=True)

    @staticmethod
    def _to_pil(image: ImageInput) -> Image.Image:
        if isinstance(image, Image.Image):
            return image.convert("RGB")
        try:
            return Image.open(image).convert("RGB")
        except (FileNotFoundError, UnidentifiedImageError) as exc:
            raise CaptionGenerationError(f"Could not open image: {image}") from exc
