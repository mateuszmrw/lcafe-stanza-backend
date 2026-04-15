"""Subtitle chunking for YouTube video imports."""


class YouTubeSubtitleChunker:
    """Split subtitle lines into pages for processing."""

    def chunk(self, subtitle_lines: list[dict], lines_per_page: int = 20) -> list[list[dict]]:
        """Split subtitle lines into pages of ~lines_per_page lines each.

        Args:
            subtitle_lines: List of {line_number, start_ms, end_ms, text}
            lines_per_page: Target lines per page (default 20)

        Returns:
            List of pages, each page is a list of subtitle line dicts.
            Last page may have fewer lines.
        """
        if not subtitle_lines:
            return []

        chunks: list[list[dict]] = []
        for i in range(0, len(subtitle_lines), lines_per_page):
            chunk = subtitle_lines[i : i + lines_per_page]
            chunks.append(chunk)

        return chunks
