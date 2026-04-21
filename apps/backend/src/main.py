import logging
import os
import warnings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

# `register` is a domain field (language register) that shadows BaseModel.register.
# Suppress before Pydantic models are imported via src.api / src.domain modules.
warnings.filterwarnings(
    "ignore", message="Field name \"register\".*shadows an attribute in parent"
)

from src.api.middleware import setup_cors, setup_error_handling, setup_logging  # noqa: E402
from src.api.routes import all_routers  # noqa: E402
from src.core import get_settings  # noqa: E402
from src.infrastructure.stanza.client import (  # noqa: E402
    StanzaClient,
    StanzaConfig,
    set_stanza_client,
)

settings = get_settings()

log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    books_dir = os.path.join(settings.storage_root, "books")
    os.makedirs(books_dir, exist_ok=True)

    if settings.load_stanza:
        app.state.stanza = StanzaClient(
            StanzaConfig(
                languages=settings.languages,
                model_dir=settings.model_dir,
                use_gpu=settings.use_gpu,
            )
        )
        set_stanza_client(app.state.stanza)
    else:
        app.state.stanza = None

    app.state.redis = Redis.from_url(settings.redis_url)
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    yield

    await app.state.redis.aclose()
    await app.state.arq.aclose()


app = FastAPI(debug=settings.debug, lifespan=lifespan)

setup_logging(app)
setup_cors(app)
setup_error_handling(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


for _router in all_routers:
    app.include_router(_router)
