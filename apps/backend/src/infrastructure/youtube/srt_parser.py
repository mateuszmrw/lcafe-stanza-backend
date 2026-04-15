"""Parse SRT (SubRip) subtitle format."""
import re


def parse_srt(content: str) -> list[dict]:
    """Parse SRT subtitle content and return list of subtitle dictionaries.

    Args:
        content: Raw SRT file content as a string.

    Returns:
        List of dicts with keys: line_number, start_ms, end_ms, text
    """
    if not content.strip():
        return []

    subtitles: list[dict] = []

    # Split by double newlines to get subtitle blocks
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # First line: sequence number
        try:
            line_number = int(lines[0].strip())
        except ValueError:
            continue

        # Second line: timestamps "HH:MM:SS,ms --> HH:MM:SS,ms"
        timestamp_line = lines[1].strip()
        time_match = re.match(
            r"(\d{1,2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2}),(\d{3})",
            timestamp_line,
        )
        if not time_match:
            continue

        start_h, start_m, start_s, start_ms_str = (
            int(time_match.group(1)),
            int(time_match.group(2)),
            int(time_match.group(3)),
            int(time_match.group(4)),
        )
        end_h, end_m, end_s, end_ms_str = (
            int(time_match.group(5)),
            int(time_match.group(6)),
            int(time_match.group(7)),
            int(time_match.group(8)),
        )

        start_ms = (start_h * 3600 + start_m * 60 + start_s) * 1000 + start_ms_str
        end_ms = (end_h * 3600 + end_m * 60 + end_s) * 1000 + end_ms_str

        # Remaining lines: subtitle text (strip HTML tags from auto-captions)
        raw_text = "\n".join(lines[2:]).strip()
        text = re.sub(r"<[^>]+>", "", raw_text).strip()

        subtitles.append(
            {
                "line_number": line_number,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text,
            }
        )

    return subtitles
