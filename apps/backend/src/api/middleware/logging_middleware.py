import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with a correlation ID and duration.

    The request ID is attached to `request.state.request_id` so downstream
    handlers (and the error handler) can reference it. The ID is also returned
    in the `X-Request-ID` response header so operators can grep logs when a
    user reports a problem.
    """

    def __init__(self, app: FastAPI, *, logger: logging.Logger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            self.logger.exception(
                "%s %s — failed after %dms [rid=%s]",
                request.method, request.url.path, duration_ms, request_id,
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        self.logger.info(
            "%s %s %d %dms [rid=%s]",
            request.method, request.url.path, response.status_code, duration_ms, request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
