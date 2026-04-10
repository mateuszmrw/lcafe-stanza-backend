import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator


from fastapi import FastAPI

from src.api.middleware import setup_cors, setup_error_handling, setup_logging
from src.api.routes import content as content_router
from src.api.routes import health as health_router
from src.api.routes import nlp as nlp_router
from src.api.routes import stanza as stanza_router
from src.api.routes import auth as auth_router
from src.api.routes import books as books_router
from src.api.routes import dictionary as dictionary_router
from src.api.routes import translation as translation_router
from src.api.routes import grammar as grammar_router
from src.api.routes import users as users_router
from src.api.routes import languages as languages_router
from src.api.routes import vocabulary as vocabulary_router
from src.api.routes.admin import languages as admin_languages_router
from src.api.routes.admin import providers as admin_providers_router
from src.api.routes.admin import users as admin_users_router
from src.api.routes.admin import dictionary as admin_dictionary_router
from src.api.routes.admin import system_keys as admin_system_keys_router
from src.api.routes.admin import deepl_instances as admin_deepl_instances_router
from src.api.routes.admin import llm as admin_llm_router
from src.api.routes.admin import data as admin_data_router
from src.api.routes.admin import frequencies as admin_frequencies_router
from src.api.routes import setup as setup_router  # noqa: E402
from src.core import get_settings

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
    yield


app = FastAPI(debug=settings.debug, lifespan=lifespan)

setup_logging(app)
setup_cors(app)
setup_error_handling(app)

app.include_router(health_router.router)
app.include_router(stanza_router.router)
app.include_router(nlp_router.router)
app.include_router(content_router.router)
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(books_router.router)
app.include_router(languages_router.router)
app.include_router(vocabulary_router.router)
app.include_router(dictionary_router.router)
app.include_router(translation_router.router)
app.include_router(grammar_router.router)
app.include_router(admin_languages_router.router)
app.include_router(admin_providers_router.router)
app.include_router(admin_users_router.router)
app.include_router(admin_dictionary_router.router)
app.include_router(admin_system_keys_router.router)
app.include_router(admin_deepl_instances_router.router)
app.include_router(admin_llm_router.router)
app.include_router(admin_data_router.router)
app.include_router(admin_frequencies_router.router)
app.include_router(setup_router.router)
