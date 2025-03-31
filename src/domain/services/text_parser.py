from typing import List
import re

SENTENCE_ENDINGS = ['NEWLINE', '？', '！', '。', '?', '!', '.', '»', '«']
        
class TextParser:
    def __init__(self, text: str, chunkSize: int = 3000):
        self.text = text
        self.chunkSize = chunkSize

    def parse(self) -> list[str]:
        text = re.sub(r'\r?\n', ' NEWLINE ', self.text)
        text = text.replace('\xa0', ' ')

        sentence_pattern = '|'.join(map(re.escape, SENTENCE_ENDINGS))
        sentences = re.split(f'({sentence_pattern})', text)
        
        sentences = [''.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)]
        
        chunks: List[str] = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence.replace(' NEWLINE ', ''))
            
            if current_size + sentence_size > self.chunkSize and current_chunk:
                chunks.append(''.join(current_chunk).replace(' NEWLINE ', '\r\n'))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        if current_chunk:
            chunks.append(''.join(current_chunk).replace(' NEWLINE ', '\r\n'))

        return chunks