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
        paragraphs = re.split(r"\r?\n+", self.text)
        paragraphs = [p.replace("\xa0", " ").strip() for p in paragraphs if p.strip()]

        chunks: List[str] = []
        current_lines: List[str] = []
        current_size = 0

        for paragraph in paragraphs:
            for sentence in self._split_sentences(paragraph):
                size = len(sentence)
                if current_size + size > self.chunkSize and current_lines:
                    chunks.append("\r\n".join(current_lines))
                    current_lines = []
                    current_size = 0
                current_lines.append(sentence)
                current_size += size

        if current_lines:
            chunks.append("\r\n".join(current_lines))

        return chunks
