"""Parser for CC-CEDICT Chinese–English dictionary.

Source:  https://www.mdbg.net/chinese/dictionary?page=cc-cedict
Format:  ZIP containing a plain-text .u8 or .txt file.
         Also accepts the raw unzipped text file or a gzipped file (.gz).

Line format (one entry per line):
    Traditional Simplified [pinyin] /def1/def2/.../

Lines starting with # are comments.

Example:
    愛 爱 [ai4] /to love/love/affection/to be fond of/
    中文 中文 [Zhong1 wen2] /Chinese language/
"""
from __future__ import annotations

import gzip
import io
import re
import zipfile

_ENTRY_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$"
)


def _decode_content(content: bytes) -> str:
    """Return the raw text from content that may be ZIP, GZip, or plain text."""
    # ZIP: extract the first .txt / .u8 entry
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if name.endswith((".txt", ".u8", ".csv")):
                    return zf.read(name).decode("utf-8", errors="replace")
            # Fall back to first entry
            return zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")

    # GZip
    try:
        return gzip.decompress(content).decode("utf-8", errors="replace")
    except (gzip.BadGzipFile, OSError):
        pass

    # Plain text
    return content.decode("utf-8", errors="replace")



def parse_cc_cedict(
    content: bytes, source_lang: str, _target_lang: str
) -> list[dict]:
    """Parse a CC-CEDICT file into row dicts for cc_cedict_entries.

    Args:
        content:      Raw bytes — ZIP, GZip, or plain text.
        source_lang:  Must be "zh".
        _target_lang: Accepted but ignored; CC-CEDICT is zh→en only.
    """
    if source_lang.lower() != "zh":
        raise ValueError(
            f"CC-CEDICT only supports source_lang='zh', got '{source_lang}'"
        )

    text = _decode_content(content)
    result: list[dict] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            continue

        traditional, simplified, pinyin, defs_raw = m.groups()
        glosses = [d.strip() for d in defs_raw.split("/") if d.strip()]
        if not glosses:
            continue

        result.append({
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": pinyin,
            "glosses": glosses,
            "source_dict": "cc-cedict",
        })

    return result
