"""Tests for SRT subtitle parser."""
import pytest


class TestParseSRT:
    """Test parsing of SRT subtitle format."""

    def test_parse_srt_valid_format(self):
        """Parse valid SRT content with multiple subtitle lines."""
        from src.infrastructure.youtube.srt_parser import parse_srt

        srt_content = """1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,000
How are you?
"""
        result = parse_srt(srt_content)

        assert len(result) == 2
        assert result[0]["line_number"] == 1
        assert result[0]["start_ms"] == 1000
        assert result[0]["end_ms"] == 3500
        assert result[0]["text"] == "Hello world"
        assert result[1]["line_number"] == 2
        assert result[1]["start_ms"] == 4000
        assert result[1]["end_ms"] == 6000
        assert result[1]["text"] == "How are you?"

    def test_parse_srt_multiline_text(self):
        """Parse SRT with multiline subtitle text."""
        from src.infrastructure.youtube.srt_parser import parse_srt

        srt_content = """1
00:00:01,000 --> 00:00:05,000
This is a long subtitle
that spans multiple lines
and goes on here

2
00:00:06,000 --> 00:00:08,000
Short one
"""
        result = parse_srt(srt_content)

        assert len(result) == 2
        assert result[0]["text"] == "This is a long subtitle\nthat spans multiple lines\nand goes on here"
        assert result[1]["text"] == "Short one"

    def test_parse_srt_with_extra_whitespace(self):
        """Parse SRT with extra blank lines and whitespace."""
        from src.infrastructure.youtube.srt_parser import parse_srt

        srt_content = """1
00:00:01,000 --> 00:00:03,500
Hello


2
00:00:04,000 --> 00:00:06,000
World
"""
        result = parse_srt(srt_content)

        assert len(result) == 2
        assert result[0]["text"] == "Hello"
        assert result[1]["text"] == "World"

    def test_parse_srt_empty_content(self):
        """Parse empty SRT content returns empty list."""
        from src.infrastructure.youtube.srt_parser import parse_srt

        result = parse_srt("")
        assert result == []

    def test_parse_srt_timestamps_with_hours(self):
        """Parse SRT with timestamps that include hours."""
        from src.infrastructure.youtube.srt_parser import parse_srt

        srt_content = """1
01:02:03,456 --> 01:02:10,789
Long video
"""
        result = parse_srt(srt_content)

        assert len(result) == 1
        # 1 hour = 3600000ms, 2 min = 120000ms, 3 sec = 3000ms, 456ms
        assert result[0]["start_ms"] == 3600000 + 120000 + 3000 + 456
        # 1 hour = 3600000ms, 2 min = 120000ms, 10 sec = 10000ms, 789ms
        assert result[0]["end_ms"] == 3600000 + 120000 + 10000 + 789
