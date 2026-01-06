"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..scraper.browser import BrowserManager
from ..utils.logging import setup_logging
from .routers import health, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle.

    Starts browser on startup and stops it on shutdown.
    """
    # Setup logging
    setup_logging(settings.log_level)

    # Start browser
    browser = BrowserManager(headless=settings.headless)
    await browser.start()
    app.state.browser = browser

    yield

    # Cleanup
    await browser.stop()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Substack Post Scraper API",
        description="API for scraping Substack posts by keyword search",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])

    return app
