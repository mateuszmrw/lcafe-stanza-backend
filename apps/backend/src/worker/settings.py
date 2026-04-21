import logging

from arq.connections import RedisSettings

from src.core.config import get_settings
from src.infrastructure.stanza.client import StanzaConfig, get_stanza_client
from src.worker.tasks.align_smil_audio import align_smil_audio
from src.worker.tasks.generate_tts_audio import generate_tts_audio
from src.worker.tasks.import_youtube_subtitles import import_youtube_subtitles
from src.worker.tasks.retokenize_user_language_coref import retokenize_user_language_coref
from src.worker.tasks.import_cognate_pairs import import_cognate_pairs
from src.worker.tasks.tokenize_page import tokenize_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

_settings = get_settings()


async def startup(ctx: dict) -> None:
    logger.info("Worker starting up — loading Stanza models for: %s", _settings.languages)
    stanza_config = StanzaConfig(
        languages=_settings.languages,
        model_dir=_settings.model_dir,
        use_gpu=_settings.use_gpu,
    )
    ctx["stanza_client"] = get_stanza_client(stanza_config)
    logger.info("Stanza models loaded")


async def shutdown(ctx: dict) -> None:
    logger.info("Worker shutting down")


class WorkerSettings:
    functions = [
        import_youtube_subtitles,
        tokenize_page,
        align_smil_audio,
        generate_tts_audio,
        retokenize_user_language_coref,
        import_cognate_pairs,
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 4
    job_timeout = 600  # 10 min — SMIL alignment is fast (parsing only)
    retry_jobs = False
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
