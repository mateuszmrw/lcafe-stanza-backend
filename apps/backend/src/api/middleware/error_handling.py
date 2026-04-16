import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, *, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            # Generate a correlation ID so the user can reference the failure
            # without us exposing internal error details (stack traces, DB errors, paths).
            error_id = uuid.uuid4().hex[:12]
            self.logger.exception(
                "Unhandled error [%s] %s %s",
                error_id,
                request.method,
                request.url.path,
            )
            return JSONResponse(
                content={
                    "error": "Internal server error",
                    "error_id": error_id,
                },
                status_code=500,
            )
