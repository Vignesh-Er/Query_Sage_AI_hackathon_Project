import json
import hashlib
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import get_db_context
from app.models import AuditLog

from starlette.middleware.trustedhost import TrustedHostMiddleware

def setup_cors(app):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

async def global_exception_handler(request: Request, exc: Exception):
    error_detail = {
        "error": str(exc),
        "detail": traceback.format_exception_only(type(exc), exc)[0].strip()
    }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail
    )

async def audit_logging_middleware(request: Request, call_next):
    # Only capture AI-related POST requests or streaming requests
    path = request.url.path
    if path in ["/api/analyze/stream", "/api/natural-language/generate"]:
        # Let the request proceed first, we will log in the endpoints or log here
        # Since reading body of stream request can block it, we can log in the endpoint
        # itself or check the path and log simple metadata
        response = await call_next(request)
        return response
        
    response = await call_next(request)
    return response
