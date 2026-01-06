"""Playwright browser manager for Substack scraping."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright, Playwright
import structlog

logger = structlog.get_logger()


class BrowserManager:
    """Manages Playwright browser lifecycle."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, headless: bool = True):
        """Initialize browser manager.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Initialize and start the browser."""
        async with self._lock:
            if self._browser is not None:
                return

            logger.info("starting_browser", headless=self.headless)
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            logger.info("browser_started")

    async def stop(self) -> None:
        """Stop and clean up browser resources."""
        async with self._lock:
            if self._browser:
                logger.info("stopping_browser")
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
                logger.info("browser_stopped")

    @asynccontextmanager
    async def new_context(self) -> AsyncGenerator[BrowserContext, None]:
        """Create a new browser context.

        Yields:
            Browser context for creating pages
        """
        if self._browser is None:
            await self.start()

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self.USER_AGENT,
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(self) -> AsyncGenerator[Page, None]:
        """Create a new browser page.

        Yields:
            Browser page for navigation
        """
        async with self.new_context() as context:
            page = await context.new_page()

            # Block unnecessary resources to speed up loading
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot}",
                lambda route: route.abort()
            )

            try:
                yield page
            finally:
                await page.close()

    async def __aenter__(self) -> "BrowserManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
