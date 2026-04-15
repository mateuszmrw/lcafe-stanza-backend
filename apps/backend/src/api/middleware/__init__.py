import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .error_handling import ErrorHandlingMiddleware
from .logging_middleware import LoggingMiddleware


def setup_logging(app: FastAPI):
    app.add_middleware(LoggingMiddleware, logger=logging.getLogger(__name__))


def setup_cors(app: FastAPI):
    # allow_credentials is intentionally omitted (defaults to False).
    # The app uses Authorization: Bearer headers — no cookies are sent cross-origin.
    # allow_origins=["*"] is only valid without credentials per CORS spec.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_error_handling(app: FastAPI):
    app.add_middleware(ErrorHandlingMiddleware, logger=logging.getLogger(__name__))
