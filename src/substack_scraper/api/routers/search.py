"""Search API endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...models.search_result import SearchResult
from ..dependencies import get_scraper, get_json_writer
from ...scraper.search_scraper import SearchScraper
from ...storage.json_writer import JsonWriter

router = APIRouter(prefix="/search", tags=["Search"])


class BatchSearchRequest(BaseModel):
    """Request body for batch search."""

    keywords: list[str] = Field(..., min_length=1, max_length=10)
    limit: int = Field(default=50, ge=1, le=200)
    fetch_content: bool = Field(default=True)
    save_to_file: bool = Field(default=False)


class BatchSearchResponse(BaseModel):
    """Response for batch search."""

    total_keywords: int
    total_posts: int
    results: list[SearchResult]
    saved_files: list[str] = []


@router.get("", response_model=SearchResult)
async def search_posts(
    keyword: Annotated[str, Query(description="Search keyword", min_length=1)],
    limit: Annotated[int, Query(ge=1, le=200, description="Max results")] = 50,
    fetch_content: Annotated[bool, Query(description="Fetch full post content")] = True,
    scraper: SearchScraper = Depends(get_scraper),
) -> SearchResult:
    """Search Substack for posts matching keyword.

    Args:
        keyword: Search term
        limit: Maximum number of posts to return (1-200)
        fetch_content: Whether to fetch full post body content
        scraper: Injected scraper instance

    Returns:
        SearchResult with list of matching posts
    """
    try:
        result = await scraper.search(
            keyword=keyword,
            limit=limit,
            fetch_content=fetch_content,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchSearchResponse)
async def batch_search(
    request: BatchSearchRequest,
    background_tasks: BackgroundTasks,
    scraper: SearchScraper = Depends(get_scraper),
    writer: JsonWriter = Depends(get_json_writer),
) -> BatchSearchResponse:
    """Search multiple keywords in batch.

    Args:
        request: Batch search request with keywords and options
        background_tasks: FastAPI background tasks
        scraper: Injected scraper instance
        writer: Injected JSON writer

    Returns:
        BatchSearchResponse with all results
    """
    try:
        results = await scraper.search_multiple(
            keywords=request.keywords,
            limit=request.limit,
            fetch_content=request.fetch_content,
        )

        saved_files = []

        if request.save_to_file:
            # Save results to files in background
            for result in results:
                filepath = writer.write_search_result_sync(result)
                saved_files.append(filepath)

        total_posts = sum(r.total_results for r in results)

        return BatchSearchResponse(
            total_keywords=len(request.keywords),
            total_posts=total_posts,
            results=results,
            saved_files=saved_files,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords", response_model=list[SearchResult])
async def search_multiple_keywords(
    keywords: Annotated[
        list[str],
        Query(description="List of keywords to search"),
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    fetch_content: Annotated[bool, Query()] = True,
    scraper: SearchScraper = Depends(get_scraper),
) -> list[SearchResult]:
    """Search multiple keywords via query parameters.

    Args:
        keywords: List of search terms
        limit: Maximum results per keyword
        fetch_content: Whether to fetch full content
        scraper: Injected scraper instance

    Returns:
        List of SearchResult objects
    """
    try:
        return await scraper.search_multiple(
            keywords=keywords,
            limit=limit,
            fetch_content=fetch_content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
