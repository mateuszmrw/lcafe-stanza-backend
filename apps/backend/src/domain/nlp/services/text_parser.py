import re
from typing import List

SENTENCE_ENDINGS = re.compile(r"(?<=[.!?。！？])\s+|(?<=»)\s+")


class TextParser:
    def __init__(self, text: str, chunkSize: int = 3000):
        self.text = text
        self.chunkSize = chunkSize

    def _split_sentences(self, paragraph: str) -> List[str]:
        parts = SENTENCE_ENDINGS.split(paragraph)
        return [p.strip() for p in parts if p.strip()]

    def parse(self) -> List[str]:
        # Split on double newlines — the paragraph boundary marker written by BookParser.
        # Fall back to single newlines for older content stored without \n\n structure.
        paragraphs = re.split(r"\n\n+", self.text)
        if len(paragraphs) == 1:
            # Legacy format: single newlines or \r\n between sentences, no paragraph markers.
            paragraphs = re.split(r"\r?\n+", self.text)

        paragraphs = [p.replace("\xa0", " ").strip() for p in paragraphs if p.strip()]

        chunks: List[str] = []
        current_paragraphs: List[str] = []
        current_size = 0

        for paragraph in paragraphs:
            sentences = self._split_sentences(paragraph)
            # Single newline separates sentences within a paragraph.
            para_text = "\n".join(sentences) if sentences else paragraph
            size = len(para_text)

            if current_size + size > self.chunkSize and current_paragraphs:
                # Double newline separates paragraphs within a chunk.
                chunks.append("\n\n".join(current_paragraphs))
                current_paragraphs = []
                current_size = 0

            current_paragraphs.append(para_text)
            current_size += size

        if current_paragraphs:
            chunks.append("\n\n".join(current_paragraphs))

        return chunks
