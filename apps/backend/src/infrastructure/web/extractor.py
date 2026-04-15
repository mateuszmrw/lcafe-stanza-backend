"""Article extraction from web URLs using trafilatura."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import trafilatura


@dataclass
class ArticleResult:
    title: str
    text: str
    author: str | None
    excerpt: str


class ExtractionError(Exception):
    """Raised when article extraction fails."""


class WebArticleExtractor:
    """Extract article text from a URL using trafilatura."""

    def _extract_sync(self, url: str, timeout: int = 10) -> ArticleResult:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ExtractionError("Could not access this URL")

        text = trafilatura.extract(downloaded)
        if not text or len(text.strip()) < 50:
            raise ExtractionError("No readable content found at this URL")

        metadata = trafilatura.extract(
            downloaded,
            output_format="json",
            with_metadata=True,
        )

        title = "Untitled"
        author = None
        if metadata:
            import json
            try:
                meta = json.loads(metadata)
                title = meta.get("title") or "Untitled"
                author = meta.get("author") or None
            except (json.JSONDecodeError, TypeError):
                pass

        excerpt = text[:200].rsplit(" ", 1)[0] + "..." if len(text) > 200 else text

        return ArticleResult(
            title=title,
            text=text,
            author=author,
            excerpt=excerpt,
        )

    async def extract(self, url: str, timeout: int = 10) -> ArticleResult:
        """Extract article from URL. Runs trafilatura in a thread."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._extract_sync, url, timeout),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise ExtractionError("Request timed out") from None
