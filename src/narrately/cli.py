"""Command-line interface for Narrately.

Examples
--------
Caption a local image::

    python -m narrately image path/to/photo.jpg

Caption every image found on a webpage, writing results to a file::

    python -m narrately webpage https://example.com --output captions.txt
"""

from __future__ import annotations

import argparse
import logging
import sys

from .captioner import CaptionGenerationError, DEFAULT_MODEL, ImageCaptioner
from .web_scraper import extract_image_urls

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrately",
        description="Generate AI captions for images using BLIP.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"BLIP model checkpoint to use (default: {DEFAULT_MODEL})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    image_parser = subparsers.add_parser("image", help="Caption a local image file")
    image_parser.add_argument("path", help="Path to an image file")

    url_parser = subparsers.add_parser("url", help="Caption a single image URL")
    url_parser.add_argument("url", help="Direct URL to an image")

    webpage_parser = subparsers.add_parser(
        "webpage", help="Caption every image found on a webpage"
    )
    webpage_parser.add_argument("url", help="URL of the webpage to scan")
    webpage_parser.add_argument(
        "--output",
        default="captions.txt",
        help="File to write '<image_url>: <caption>' lines to (default: captions.txt)",
    )
    webpage_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of images to caption (default: 20)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        captioner = ImageCaptioner(model_name=args.model)

        if args.command == "image":
            print(captioner.caption(args.path))

        elif args.command == "url":
            caption = captioner.caption_url(args.url)
            print(caption if caption else "Could not generate a caption for that URL.")

        elif args.command == "webpage":
            image_urls = extract_image_urls(args.url)[: args.limit]
            if not image_urls:
                logger.warning("No candidate images found on %s", args.url)
                return 0

            with open(args.output, "w", encoding="utf-8") as f:
                for image_url in image_urls:
                    caption = captioner.caption_url(image_url)
                    if caption:
                        f.write(f"{image_url}: {caption}\n")
                        logger.info("Captioned: %s", image_url)
            logger.info("Wrote captions to %s", args.output)

    except CaptionGenerationError as exc:
        logger.error(str(exc))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
