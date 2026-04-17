from src.domain.content.service import ContentService
from src.domain.coverage.service import CoverageService
from src.infrastructure.db.repositories.audio_repo import AudioRepository
from src.infrastructure.db.repositories.content_page_repo import ContentPageRepository
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

content_service = ContentService()
coverage_service = CoverageService()
content_repo = ContentRepository()
page_repo = ContentPageRepository()
word_repo = WordRepository()
audio_repo = AudioRepository()
