import logging
import uuid
from fastapi import FastAPI, Request 
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: FastAPI,
            *,
            logger: logging.Logger
    ) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
       request_id = str(uuid.uuid4())
       self.logger.info(f"Request ID: {request_id} - {request.method} {request.url.path}")
       response = await call_next(request)
       self.logger.info(f"Request ID: {request_id} - {request.method} {request.url.path} - {response.status_code}")
       return response
    