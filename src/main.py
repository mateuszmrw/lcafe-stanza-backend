from fastapi import FastAPI
from src.api.middleware import setup_logging, setup_cors, setup_error_handling
from src.core import get_settings
from src.api.routes import models as models_router, health as health_router, tokenize as tokenize_router

settings = get_settings()
app = FastAPI(debug=settings.debug)

setup_logging(app)
setup_cors(app)
setup_error_handling(app)

app.include_router(models_router.router)
app.include_router(health_router.router)
app.include_router(tokenize_router.router)