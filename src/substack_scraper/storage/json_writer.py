"""JSON file writer for persisting search results."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from ..models.search_result import SearchResult

logger = structlog.get_logger()


class JsonWriter:
    """Handles JSON file output for search results."""

    def __init__(self, output_dir: str = "./output"):
        """Initialize JSON writer.

        Args:
            output_dir: Directory for JSON output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized filename-safe string
        """
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r"[^\w\-]", "_", text)
        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Trim underscores from ends
        sanitized = sanitized.strip("_")
        # Limit length
        return sanitized[:50]

    def _generate_filename(self, keyword: str) -> str:
        """Generate unique filename for search result.

        Args:
            keyword: Search keyword

        Returns:
            Filename with timestamp
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_keyword = self._sanitize_filename(keyword)
        return f"{safe_keyword}_{timestamp}.json"

    async def write_search_result(self, result: SearchResult) -> str:
        """Write search result to JSON file.

        Args:
            result: SearchResult to save

        Returns:
            Path to the saved file
        """
        filename = self._generate_filename(result.keyword)
        filepath = self.output_dir / filename

        # Convert to JSON-serializable dict
        data = result.model_dump(mode="json")

        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

        logger.info("saved_search_result", filepath=str(filepath), posts=len(result.posts))
        return str(filepath)

    async def write_posts(
        self,
        posts: list[dict[str, Any]],
        keyword: str,
    ) -> str:
        """Write raw posts to JSON file.

        Args:
            posts: List of post dictionaries
            keyword: Search keyword

        Returns:
            Path to the saved file
        """
        filename = self._generate_filename(keyword)
        filepath = self.output_dir / filename

        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(json.dumps(posts, indent=2, ensure_ascii=False, default=str))

        logger.info("saved_posts", filepath=str(filepath), count=len(posts))
        return str(filepath)

    def write_search_result_sync(self, result: SearchResult) -> str:
        """Synchronously write search result to JSON file.

        Args:
            result: SearchResult to save

        Returns:
            Path to the saved file
        """
        filename = self._generate_filename(result.keyword)
        filepath = self.output_dir / filename

        data = result.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("saved_search_result", filepath=str(filepath), posts=len(result.posts))
        return str(filepath)

    def write_all_posts_combined(
        self,
        results: list[SearchResult],
        filename: str = "all_posts.json",
    ) -> str:
        """Write all posts from multiple results to a single file.

        Args:
            results: List of SearchResult objects
            filename: Output filename

        Returns:
            Path to the saved file
        """
        filepath = self.output_dir / filename

        # Combine all posts
        all_posts = []
        for result in results:
            for post in result.posts:
                all_posts.append(post.model_dump(mode="json"))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, indent=2, ensure_ascii=False)

        logger.info(
            "saved_combined_posts",
            filepath=str(filepath),
            total_posts=len(all_posts),
            keywords=len(results),
        )
        return str(filepath)
