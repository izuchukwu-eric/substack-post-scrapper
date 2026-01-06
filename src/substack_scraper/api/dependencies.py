"""Dependency injection for FastAPI."""

from fastapi import Request

from ..config import settings
from ..scraper.browser import BrowserManager
from ..scraper.data_extractor import DataExtractor
from ..scraper.post_fetcher import PostFetcher
from ..scraper.scroll_handler import ScrollHandler
from ..scraper.search_scraper import SearchScraper
from ..storage.json_writer import JsonWriter
from ..utils.rate_limiter import RateLimiter


# Shared instances
_scroll_handler = ScrollHandler(
    scroll_delay_ms=settings.scroll_delay_ms,
    timeout_ms=settings.scroll_timeout_ms,
)
_extractor = DataExtractor()
_rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
_json_writer = JsonWriter(settings.output_dir)


async def get_scraper(request: Request) -> SearchScraper:
    """Get configured scraper instance.

    Args:
        request: FastAPI request object

    Returns:
        SearchScraper instance
    """
    browser: BrowserManager = request.app.state.browser
    post_fetcher = PostFetcher(browser)

    return SearchScraper(
        browser_manager=browser,
        scroll_handler=_scroll_handler,
        data_extractor=_extractor,
        post_fetcher=post_fetcher,
        rate_limiter=_rate_limiter,
        fetch_full_content=True,
    )


async def get_json_writer() -> JsonWriter:
    """Get JSON writer instance.

    Returns:
        JsonWriter instance
    """
    return _json_writer
