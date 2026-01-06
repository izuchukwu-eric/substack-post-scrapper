"""Search result wrapper model."""

from datetime import datetime

from pydantic import BaseModel, Field

from .post import SubstackPost


class SearchResult(BaseModel):
    """Wrapper for search results from a single keyword."""

    keyword: str
    total_results: int
    posts: list[SubstackPost]
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0


class BatchSearchResult(BaseModel):
    """Wrapper for batch search results from multiple keywords."""

    keywords: list[str]
    total_results: int
    results: list[SearchResult]
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
