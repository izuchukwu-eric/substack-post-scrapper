"""Post content fetcher for getting full post body."""

import asyncio
import json
from typing import Any

from playwright.async_api import Page
import structlog

from .browser import BrowserManager

logger = structlog.get_logger()


class PostFetcher:
    """Fetches full post content from individual post URLs."""

    def __init__(self, browser_manager: BrowserManager, delay_ms: int = 500):
        """Initialize post fetcher.

        Args:
            browser_manager: Browser manager instance
            delay_ms: Delay between requests in milliseconds
        """
        self.browser = browser_manager
        self.delay_ms = delay_ms

    async def fetch_post_content(self, url: str) -> dict[str, Any]:
        """Fetch full content from a single post URL.

        Args:
            url: Post canonical URL

        Returns:
            Dictionary with body_html and other extracted content
        """
        logger.debug("fetching_post_content", url=url)

        try:
            async with self.browser.new_page() as page:
                # Re-enable images for post content pages
                await page.unroute("**/*")

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for content to load
                await page.wait_for_load_state("networkidle", timeout=10000)

                # Extract post content
                content = await self._extract_content(page)

                return content

        except Exception as e:
            logger.error("fetch_post_content_failed", url=url, error=str(e))
            return {}

    async def _extract_content(self, page: Page) -> dict[str, Any]:
        """Extract content from post page.

        Args:
            page: Playwright page

        Returns:
            Dictionary with extracted content
        """
        content = {}

        # Try to get body_html from Next.js data
        try:
            next_data = await page.evaluate('''
                () => {
                    const script = document.querySelector('script#__NEXT_DATA__');
                    if (script) {
                        return script.textContent;
                    }
                    return null;
                }
            ''')

            if next_data:
                data = json.loads(next_data)
                page_props = data.get("props", {}).get("pageProps", {})
                post = page_props.get("post", {})

                if post:
                    content["body_html"] = post.get("body_html")
                    content["body_json"] = post.get("body_json")
                    content["wordcount"] = post.get("wordcount")
                    # Also get any additional fields we might have missed
                    for key in ["reactions", "comment_count", "restacks", "audio_items"]:
                        if key in post and post[key]:
                            content[key] = post[key]

        except Exception as e:
            logger.debug("next_data_content_failed", error=str(e))

        # Fallback: extract from DOM
        if not content.get("body_html"):
            try:
                body_html = await page.evaluate('''
                    () => {
                        // Look for post body container
                        const selectors = [
                            '.body.markup',
                            '[class*="post-content"]',
                            '[class*="body-markup"]',
                            'article .body',
                            '.post-body',
                            '[class*="reader2-post-body"]'
                        ];

                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el) {
                                return el.innerHTML;
                            }
                        }

                        return null;
                    }
                ''')

                if body_html:
                    content["body_html"] = body_html

            except Exception as e:
                logger.debug("dom_content_failed", error=str(e))

        return content

    async def enrich_posts(
        self,
        posts: list[dict[str, Any]],
        fetch_content: bool = True,
        max_concurrent: int = 3,
    ) -> list[dict[str, Any]]:
        """Enrich posts with full content by visiting each URL.

        Args:
            posts: List of post dictionaries
            fetch_content: Whether to fetch full content
            max_concurrent: Maximum concurrent requests

        Returns:
            Enriched list of posts
        """
        if not fetch_content:
            return posts

        logger.info("enriching_posts", count=len(posts))

        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(post: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                url = post.get("canonical_url")
                if not url:
                    return post

                # Add delay to avoid rate limiting
                await asyncio.sleep(self.delay_ms / 1000)

                content = await self.fetch_post_content(url)
                post.update(content)
                return post

        # Fetch all posts concurrently with rate limiting
        tasks = [fetch_one(post) for post in posts]
        enriched_posts = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log errors
        result = []
        for i, post in enumerate(enriched_posts):
            if isinstance(post, Exception):
                logger.error("post_enrichment_failed", index=i, error=str(post))
                result.append(posts[i])  # Keep original post on error
            else:
                result.append(post)

        logger.info("posts_enriched", count=len(result))
        return result
