"""Main search scraper orchestrator for Substack."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote

import structlog
from playwright.async_api import Response

from ..models.post import SubstackPost
from ..models.search_result import SearchResult
from ..utils.rate_limiter import RateLimiter
from .browser import BrowserManager
from .data_extractor import DataExtractor
from .post_fetcher import PostFetcher
from .scroll_handler import ScrollHandler

logger = structlog.get_logger()


class SearchScraper:
    """Orchestrates the scraping process for Substack search."""

    SEARCH_URL_TEMPLATE = "https://substack.com/search/{keyword}?searching=all_posts"

    def __init__(
        self,
        browser_manager: BrowserManager,
        scroll_handler: ScrollHandler | None = None,
        data_extractor: DataExtractor | None = None,
        post_fetcher: PostFetcher | None = None,
        rate_limiter: RateLimiter | None = None,
        fetch_full_content: bool = True,
    ):
        """Initialize search scraper.

        Args:
            browser_manager: Browser manager instance
            scroll_handler: Scroll handler for infinite scroll
            data_extractor: Data extractor for search results
            post_fetcher: Post fetcher for full content
            rate_limiter: Rate limiter for requests
            fetch_full_content: Whether to fetch full post content
        """
        self.browser = browser_manager
        self.scroller = scroll_handler or ScrollHandler()
        self.extractor = data_extractor or DataExtractor()
        self.fetcher = post_fetcher or PostFetcher(browser_manager)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.fetch_full_content = fetch_full_content

    def _build_search_url(self, keyword: str) -> str:
        """Build search URL for keyword.

        Args:
            keyword: Search keyword

        Returns:
            Full search URL
        """
        encoded_keyword = quote(keyword, safe="")
        return self.SEARCH_URL_TEMPLATE.format(keyword=encoded_keyword)

    async def search(
        self,
        keyword: str,
        limit: int = 50,
        fetch_content: bool | None = None,
    ) -> SearchResult:
        """Search Substack for posts matching keyword.

        Args:
            keyword: Search term
            limit: Maximum number of posts to retrieve
            fetch_content: Whether to fetch full content (overrides instance default)

        Returns:
            SearchResult containing list of posts
        """
        start_time = time.time()
        should_fetch = fetch_content if fetch_content is not None else self.fetch_full_content

        # Apply rate limiting
        await self.rate_limiter.acquire()

        url = self._build_search_url(keyword)
        logger.info("starting_search", keyword=keyword, limit=limit, url=url)

        # Collect posts from API responses
        captured_posts: list[dict[str, Any]] = []

        async def handle_response(response: Response) -> None:
            """Capture posts from API responses."""
            try:
                if "api" in response.url or "search" in response.url:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type:
                        try:
                            data = await response.json()
                            # Look for posts in response
                            posts = None
                            if isinstance(data, list):
                                posts = data
                            elif isinstance(data, dict):
                                posts = data.get("posts") or data.get("results") or data.get("items")

                            if posts and isinstance(posts, list):
                                for post in posts:
                                    if isinstance(post, dict) and post.get("id"):
                                        captured_posts.append(post)
                                logger.debug("captured_api_posts", count=len(posts), url=response.url)
                        except Exception:
                            pass
            except Exception:
                pass

        async with self.browser.new_context() as context:
            page = await context.new_page()

            # Listen for API responses
            page.on("response", handle_response)

            # Navigate to search page
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                logger.warning("initial_load_timeout", error=str(e))

            # Wait a bit for initial data load
            await asyncio.sleep(2)

            # Wait for search results to appear
            try:
                await page.wait_for_selector(
                    '[class*="SearchResult"], [class*="post-preview"], article, [class*="reader2"]',
                    timeout=10000,
                )
            except Exception as e:
                logger.warning("no_results_found", keyword=keyword, error=str(e))

            # Define counter function for scroll handler
            async def get_post_count() -> int:
                return await self.extractor.get_post_count(page)

            # Scroll to load more results
            initial_count = await get_post_count()
            logger.info("initial_results", count=initial_count, captured=len(captured_posts))

            if len(captured_posts) < limit:
                await self.scroller.scroll_to_load_results(
                    page, limit, get_post_count
                )
                # Wait for any pending API responses
                await asyncio.sleep(1)
                logger.info("after_scroll", captured=len(captured_posts))

            # Use captured posts if available, otherwise try extraction
            raw_posts = captured_posts if captured_posts else []

            if not raw_posts:
                raw_posts = await self.extractor.extract_posts(page, keyword)

            # Add keyword and timestamp to each post
            scraped_at = datetime.utcnow().isoformat() + "Z"
            for post in raw_posts:
                post["keyword"] = keyword
                post["scrapedAt"] = scraped_at

            logger.info("raw_posts_extracted", count=len(raw_posts))

            await page.close()

        # Limit to requested count
        raw_posts = raw_posts[:limit]

        # Enrich with full content if requested
        if should_fetch and raw_posts:
            raw_posts = await self.fetcher.enrich_posts(raw_posts, fetch_content=True)

        # Parse into models
        posts = []
        for raw_post in raw_posts:
            try:
                post = SubstackPost(**raw_post)
                posts.append(post)
            except Exception as e:
                logger.warning(
                    "post_validation_failed",
                    post_id=raw_post.get("id"),
                    error=str(e),
                )
                # Try to create with minimal data
                try:
                    minimal_post = self._create_minimal_post(raw_post, keyword)
                    posts.append(minimal_post)
                except Exception:
                    pass

        duration = time.time() - start_time

        result = SearchResult(
            keyword=keyword,
            total_results=len(posts),
            posts=posts,
            scraped_at=datetime.utcnow(),
            duration_seconds=round(duration, 2),
        )

        logger.info(
            "search_complete",
            keyword=keyword,
            total_results=len(posts),
            duration=f"{duration:.2f}s",
        )

        return result

    def _create_minimal_post(self, raw_post: dict[str, Any], keyword: str) -> SubstackPost:
        """Create a minimal post from raw data.

        Args:
            raw_post: Raw post dictionary
            keyword: Search keyword

        Returns:
            SubstackPost with minimal required fields
        """
        return SubstackPost(
            keyword=keyword,
            id=raw_post.get("id", 0),
            publication_id=raw_post.get("publication_id", 0),
            title=raw_post.get("title", "Unknown"),
            slug=raw_post.get("slug", ""),
            canonical_url=raw_post.get("canonical_url", ""),
            post_date=raw_post.get("post_date", datetime.utcnow()),
            type=raw_post.get("type", "newsletter"),
            audience=raw_post.get("audience", "everyone"),
        )

    async def search_multiple(
        self,
        keywords: list[str],
        limit: int = 50,
        fetch_content: bool | None = None,
    ) -> list[SearchResult]:
        """Search for multiple keywords.

        Args:
            keywords: List of search keywords
            limit: Maximum number of posts per keyword
            fetch_content: Whether to fetch full content

        Returns:
            List of SearchResult objects
        """
        results = []

        for keyword in keywords:
            try:
                result = await self.search(
                    keyword=keyword,
                    limit=limit,
                    fetch_content=fetch_content,
                )
                results.append(result)
            except Exception as e:
                logger.error("search_failed", keyword=keyword, error=str(e))
                # Create empty result on error
                results.append(
                    SearchResult(
                        keyword=keyword,
                        total_results=0,
                        posts=[],
                        scraped_at=datetime.utcnow(),
                        duration_seconds=0,
                    )
                )

        return results
