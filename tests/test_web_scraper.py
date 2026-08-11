"""Tests for narrately.web_scraper.

These tests mock the HTTP call so they run fast and don't require
network access or a downloaded model.
"""

from unittest.mock import Mock, patch

from narrately.web_scraper import extract_image_urls

SAMPLE_HTML = """
<html><body>
    <img src="https://example.com/photo.jpg">
    <img src="//example.com/protocol-relative.png">
    <img src="/relative/path.png">
    <img src="tracker.svg">
    <img src="pixel-1x1.gif">
    <img>
</body></html>
"""


@patch("narrately.web_scraper.requests.get")
def test_extract_image_urls_filters_and_resolves(mock_get: Mock) -> None:
    mock_get.return_value = Mock(text=SAMPLE_HTML, raise_for_status=lambda: None)

    urls = extract_image_urls("https://example.com")

    assert "https://example.com/photo.jpg" in urls
    assert "https://example.com/protocol-relative.png" in urls
    assert not any("relative/path.png" in u for u in urls)
    assert not any("svg" in u for u in urls)
    assert not any("1x1" in u for u in urls)


@patch("narrately.web_scraper.requests.get")
def test_extract_image_urls_no_images(mock_get: Mock) -> None:
    mock_get.return_value = Mock(text="<html><body></body></html>", raise_for_status=lambda: None)

    assert extract_image_urls("https://example.com") == []
