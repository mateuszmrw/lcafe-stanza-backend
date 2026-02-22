import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logging_middleware import LoggingMiddleware
from .error_handling import ErrorHandlingMiddleware

def setup_logging(app: FastAPI):
    app.add_middleware(LoggingMiddleware, logger=logging.getLogger(__name__))

def setup_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def setup_error_handling(app: FastAPI):
    app.add_middleware(ErrorHandlingMiddleware, logger=logging.getLogger(__name__))