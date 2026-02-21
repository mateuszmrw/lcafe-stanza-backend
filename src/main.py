import logging

from fastapi import FastAPI

from src.api.middleware import setup_cors, setup_error_handling, setup_logging
from src.api.routes import health as health_router
from src.api.routes import models as models_router
from src.api.routes import tokenize as tokenize_router
from src.core import get_settings

settings = get_settings()

log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(debug=settings.debug)

setup_logging(app)
setup_cors(app)
setup_error_handling(app)

app.include_router(models_router.router)
app.include_router(health_router.router)
app.include_router(tokenize_router.router)
