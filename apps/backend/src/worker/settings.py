import logging

from arq.connections import RedisSettings

from src.core.config import get_settings
from src.infrastructure.stanza.client import StanzaConfig, get_stanza_client
from src.worker.tasks.tokenize_page import tokenize_page

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
    functions = [tokenize_page]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 4
    job_timeout = 300  # 5 min per page (generous for slow CPU)
    retry_jobs = False
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
