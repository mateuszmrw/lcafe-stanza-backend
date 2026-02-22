import logging
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware    

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, *, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)