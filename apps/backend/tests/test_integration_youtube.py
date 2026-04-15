"""Integration tests for YouTube import functionality."""
import pytest

from src.infrastructure.youtube.srt_parser import parse_srt


class TestSRTParserIntegration:
    """Integration tests for SRT parser."""

    def test_parse_srt_full_workflow(self):
        """Test complete SRT parsing with realistic subtitle content."""
        srt_content = """1
00:00:00,500 --> 00:00:07,000
English (US)

2
00:00:07,000 --> 00:00:11,000
[SILENCE]

3
00:00:11,000 --> 00:00:14,000
When you're learning a new language,

4
00:00:14,000 --> 00:00:17,500
one of the most important things to do
is listen to native speakers.

5
00:00:17,500 --> 00:00:20,000
That's why I created Slovo.
"""

        result = parse_srt(srt_content)

        assert len(result) == 5

        # Verify structure
        for sub in result:
            assert "line_number" in sub
            assert "start_ms" in sub
            assert "end_ms" in sub
            assert "text" in sub
            assert isinstance(sub["line_number"], int)
            assert isinstance(sub["start_ms"], int)
            assert isinstance(sub["end_ms"], int)
            assert isinstance(sub["text"], str)

        # Verify specific entries
        assert result[0]["line_number"] == 1
        assert result[0]["start_ms"] == 500
        assert result[0]["end_ms"] == 7000
        assert result[0]["text"] == "English (US)"

        assert result[3]["line_number"] == 4
        assert result[3]["start_ms"] == 14000
        assert result[3]["end_ms"] == 17500
        assert "multiple lines" in result[3]["text"]
        assert "listen to native speakers" in result[4]["text"]

    def test_parse_srt_with_special_characters(self):
        """Test SRT parsing with special characters."""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Café & Restaurant (2023-2024)

2
00:00:04,000 --> 00:00:06,000
"Hello," she said.
"""

        result = parse_srt(srt_content)

        assert len(result) == 2
        assert "Café & Restaurant" in result[0]["text"]
        assert '"Hello," she said.' in result[1]["text"]

    def test_parse_srt_edge_cases(self):
        """Test SRT parser with various edge cases."""
        # Large line number
        srt_content = """9999
00:00:01,000 --> 00:00:03,000
Test
"""
        result = parse_srt(srt_content)
        assert result[0]["line_number"] == 9999

        # Very long duration
        srt_content = """1
00:00:00,000 --> 23:59:59,999
Test
"""
        result = parse_srt(srt_content)
        assert result[0]["start_ms"] == 0
        expected_end = (23 * 3600 + 59 * 60 + 59) * 1000 + 999
        assert result[0]["end_ms"] == expected_end
