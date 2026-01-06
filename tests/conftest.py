"""Pytest fixtures for Substack Scraper tests."""

import pytest


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "keyword": "test",
        "id": 123456,
        "publication_id": 789,
        "title": "Test Post Title",
        "slug": "test-post-title",
        "canonical_url": "https://example.substack.com/p/test-post-title",
        "post_date": "2025-01-01T10:00:00.000Z",
        "type": "newsletter",
        "audience": "everyone",
        "subtitle": "A test subtitle",
        "description": "A test description",
        "wordcount": 1500,
    }


@pytest.fixture
def sample_search_result(sample_post_data):
    """Sample search result for testing."""
    from substack_scraper.models.post import SubstackPost
    from substack_scraper.models.search_result import SearchResult
    from datetime import datetime

    post = SubstackPost(**sample_post_data)
    return SearchResult(
        keyword="test",
        total_results=1,
        posts=[post],
        scraped_at=datetime.utcnow(),
        duration_seconds=1.5,
    )
