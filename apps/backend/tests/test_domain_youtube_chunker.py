"""Tests for the YouTubeSubtitleChunker domain service."""
import pytest

from src.domain.youtube.chunker import YouTubeSubtitleChunker


class TestYouTubeSubtitleChunker:
    """Test the subtitle chunking logic."""

    @pytest.fixture
    def chunker(self):
        return YouTubeSubtitleChunker()

    def test_chunk_empty_list(self, chunker):
        """Chunking an empty list returns an empty list."""
        result = chunker.chunk([])
        assert result == []

    def test_chunk_exactly_one_page(self, chunker):
        """20 subtitle lines fit in exactly one chunk."""
        lines = [
            {
                "line_number": i,
                "start_ms": i * 1000,
                "end_ms": (i + 1) * 1000,
                "text": f"Line {i}",
            }
            for i in range(20)
        ]
        result = chunker.chunk(lines, lines_per_page=20)
        assert len(result) == 1
        assert len(result[0]) == 20
        assert result[0] == lines

    def test_chunk_multiple_pages(self, chunker):
        """45 lines with 20 per page → [20, 20, 5]."""
        lines = [
            {
                "line_number": i,
                "start_ms": i * 1000,
                "end_ms": (i + 1) * 1000,
                "text": f"Line {i}",
            }
            for i in range(45)
        ]
        result = chunker.chunk(lines, lines_per_page=20)
        assert len(result) == 3
        assert len(result[0]) == 20
        assert len(result[1]) == 20
        assert len(result[2]) == 5

    def test_chunk_custom_size(self, chunker):
        """5 lines with 3 per page → [3, 2]."""
        lines = [
            {
                "line_number": i,
                "start_ms": i * 1000,
                "end_ms": (i + 1) * 1000,
                "text": f"Line {i}",
            }
            for i in range(5)
        ]
        result = chunker.chunk(lines, lines_per_page=3)
        assert len(result) == 2
        assert len(result[0]) == 3
        assert len(result[1]) == 2

    def test_chunk_preserves_timing(self, chunker):
        """Verify start_ms and end_ms are preserved in chunks."""
        lines = [
            {
                "line_number": 0,
                "start_ms": 100,
                "end_ms": 200,
                "text": "First",
            },
            {
                "line_number": 1,
                "start_ms": 200,
                "end_ms": 300,
                "text": "Second",
            },
        ]
        result = chunker.chunk(lines, lines_per_page=10)
        assert result[0][0]["start_ms"] == 100
        assert result[0][0]["end_ms"] == 200
        assert result[0][1]["start_ms"] == 200
        assert result[0][1]["end_ms"] == 300

    def test_chunk_single_line(self, chunker):
        """Single line → single chunk with single item."""
        lines = [
            {
                "line_number": 0,
                "start_ms": 0,
                "end_ms": 1000,
                "text": "Only line",
            }
        ]
        result = chunker.chunk(lines, lines_per_page=20)
        assert len(result) == 1
        assert len(result[0]) == 1
        assert result[0][0]["text"] == "Only line"
