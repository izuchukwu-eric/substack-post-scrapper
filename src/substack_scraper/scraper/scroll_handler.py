"""Infinite scroll handler for Substack search pages."""

import asyncio
from typing import Callable, Awaitable

from playwright.async_api import Page
import structlog

logger = structlog.get_logger()


class ScrollHandler:
    """Handles infinite scroll pagination on Substack search pages."""

    def __init__(
        self,
        scroll_delay_ms: int = 1000,
        timeout_ms: int = 30000,
        max_no_change_iterations: int = 3,
    ):
        """Initialize scroll handler.

        Args:
            scroll_delay_ms: Delay between scroll actions in milliseconds
            timeout_ms: Maximum time to wait for new content
            max_no_change_iterations: Stop after this many scrolls with no new content
        """
        self.scroll_delay_ms = scroll_delay_ms
        self.timeout_ms = timeout_ms
        self.max_no_change_iterations = max_no_change_iterations

    async def scroll_to_load_results(
        self,
        page: Page,
        target_count: int,
        get_current_count: Callable[[], Awaitable[int]],
    ) -> int:
        """Scroll until target_count results loaded or no new content appears.

        Args:
            page: Playwright page to scroll
            target_count: Target number of results to load
            get_current_count: Async function to get current result count

        Returns:
            Final count of loaded results
        """
        last_height = 0
        last_count = 0
        no_change_iterations = 0
        scroll_count = 0

        logger.info("starting_scroll", target_count=target_count)

        while True:
            current_count = await get_current_count()

            if current_count >= target_count:
                logger.info(
                    "target_reached",
                    current_count=current_count,
                    target_count=target_count,
                )
                break

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scroll_count += 1

            # Wait for scroll and potential content load
            await asyncio.sleep(self.scroll_delay_ms / 1000)

            # Wait for network to settle
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                # Timeout is OK, we'll check for new content anyway
                pass

            # Get new page height
            new_height = await page.evaluate("document.body.scrollHeight")
            new_count = await get_current_count()

            if new_height == last_height and new_count == last_count:
                no_change_iterations += 1
                logger.debug(
                    "no_new_content",
                    iterations=no_change_iterations,
                    current_count=new_count,
                )

                if no_change_iterations >= self.max_no_change_iterations:
                    logger.info(
                        "scroll_complete_no_more_content",
                        final_count=new_count,
                        scroll_count=scroll_count,
                    )
                    break
            else:
                no_change_iterations = 0
                logger.debug(
                    "content_loaded",
                    new_count=new_count,
                    previous_count=last_count,
                )

            last_height = new_height
            last_count = new_count

        return await get_current_count()

    async def scroll_for_time(
        self,
        page: Page,
        duration_seconds: float,
        get_current_count: Callable[[], Awaitable[int]] | None = None,
    ) -> int:
        """Scroll for a specified duration.

        Args:
            page: Playwright page to scroll
            duration_seconds: How long to scroll
            get_current_count: Optional function to get result count

        Returns:
            Final count of loaded results (or 0 if no counter provided)
        """
        import time

        start_time = time.time()
        scroll_count = 0

        while (time.time() - start_time) < duration_seconds:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scroll_count += 1
            await asyncio.sleep(self.scroll_delay_ms / 1000)

        logger.info("timed_scroll_complete", scroll_count=scroll_count)

        if get_current_count:
            return await get_current_count()
        return 0
