from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

from .config import config
from .routes import converter
from .middleware.security import SecurityMiddleware
from .utils.audit import audit_logger
from .models.schemas import ErrorResponse

# Create FastAPI app
app = FastAPI(
    title=config.PROJECT_NAME,
    version=config.XML_SCHEMA_VERSION,
    docs_url=f"{config.API_V1_PREFIX}/docs" if config.DEBUG else None,
    redoc_url=f"{config.API_V1_PREFIX}/redoc" if config.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # Implement simple rate limiting
    client_ip = request.client.host
    rate_limit_key = f"rate_limit:{client_ip}"
    
    # Check if client has exceeded rate limit
    if config.RATE_LIMIT_CALLS > 0:
        # This is a simplified rate limiting implementation
        # In production, you would want to use a proper caching system
        if not hasattr(request.state, "rate_limit_count"):
            request.state.rate_limit_count = 0
        
        if request.state.rate_limit_count >= config.RATE_LIMIT_CALLS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        request.state.rate_limit_count += 1
    
    response = await call_next(request)
    return response

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Include routers
app.include_router(converter.router)

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    show_details = os.getenv("SHOW_ERROR_DETAILS", "False").lower() == "true"

    error_response = ErrorResponse(
        message=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        timestamp=datetime.utcnow(),
        details=str(exc) if show_details else None
    )

    audit_logger.log_error(
        user_id=request.state.user.id if hasattr(request.state, "user") else "anonymous",
        action="http_error",
        error=exc,
        details={
            "status_code": exc.status_code,
            "path": request.url.path,
            "error_details": str(exc) if show_details else "hidden"
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict(exclude_none=True)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    show_details = os.getenv("SHOW_ERROR_DETAILS", "False").lower() == "true"

    error_response = ErrorResponse(
        message="Invalid request parameters" if not show_details else str(exc.errors()),
        error_code="VALIDATION_ERROR",
        timestamp=datetime.utcnow(),
        details=str(exc.errors()) if show_details else None
    )

    audit_logger.log_error(
        user_id=request.state.user.id if hasattr(request.state, "user") else "anonymous",
        action="validation_error",
        error=exc,
        details={
            "errors": exc.errors(),
            "path": request.url.path,
            "error_details": str(exc.errors()) if show_details else "hidden"
        }
    )

    return JSONResponse(
        status_code=422,
        content=error_response.dict(exclude_none=True)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    show_details = os.getenv("SHOW_ERROR_DETAILS", "False").lower() == "true"
    
    error_response = ErrorResponse(
        message="Internal server error" if not show_details else str(exc),
        error_code="INTERNAL_ERROR",
        timestamp=datetime.utcnow(),
        details=str(exc) if show_details else None
    )

    audit_logger.log_error(
        user_id=request.state.user.id if hasattr(request.state, "user") else "anonymous",
        action="internal_error",
        error=exc,
        details={
            "path": request.url.path,
            "error_details": str(exc) if show_details else "hidden"
        }
    )

    return JSONResponse(
        status_code=500,
        content=error_response.dict(exclude_none=True)
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application resources."""
    # Ensure required directories exist
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    audit_logger.log_security_event(
        user_id="system",
        action="application_startup",
        ip_address="localhost",
        details={
            "version": config.XML_SCHEMA_VERSION,
            "debug_mode": config.DEBUG
        }
    )

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application resources."""
    audit_logger.log_security_event(
        user_id="system",
        action="application_shutdown",
        ip_address="localhost"
    )