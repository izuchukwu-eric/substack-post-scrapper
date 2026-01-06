"""Tests for Pydantic models."""

from datetime import datetime

import pytest


def test_substack_post_creation(sample_post_data):
    """Test creating a SubstackPost from dict."""
    from substack_scraper.models.post import SubstackPost

    post = SubstackPost(**sample_post_data)

    assert post.id == 123456
    assert post.title == "Test Post Title"
    assert post.keyword == "test"
    assert post.slug == "test-post-title"


def test_substack_post_with_optional_fields():
    """Test SubstackPost with minimal required fields."""
    from substack_scraper.models.post import SubstackPost

    post = SubstackPost(
        keyword="test",
        id=1,
        publication_id=1,
        title="Minimal Post",
        slug="minimal-post",
        canonical_url="https://example.substack.com/p/minimal",
        post_date=datetime.utcnow(),
    )

    assert post.title == "Minimal Post"
    assert post.type == "newsletter"  # default
    assert post.audience == "everyone"  # default


def test_search_result_creation(sample_search_result):
    """Test SearchResult model."""
    assert sample_search_result.keyword == "test"
    assert sample_search_result.total_results == 1
    assert len(sample_search_result.posts) == 1


def test_search_result_json_serialization(sample_search_result):
    """Test SearchResult JSON serialization."""
    json_data = sample_search_result.model_dump(mode="json")

    assert "keyword" in json_data
    assert "posts" in json_data
    assert len(json_data["posts"]) == 1
