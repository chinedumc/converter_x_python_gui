from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
from ..utils.audit import audit_logger
from ..utils.auth import verify_session_timeout
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SecurityMiddleware:
    def __init__(self):
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        self.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024  # Convert to bytes

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
        try:
            # CORS validation
            origin = request.headers.get("origin")
            if origin and origin not in self.allowed_origins:
                raise HTTPException(status_code=403, detail="Origin not allowed")

            # Content-Type validation
            content_type = request.headers.get("content-type", "")
            if request.method == "POST" and not self._is_valid_content_type(content_type):
                raise HTTPException(status_code=415, detail="Unsupported media type")

            # File size validation for uploads
            if content_type and "multipart/form-data" in content_type:
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > self.max_upload_size:
                    raise HTTPException(status_code=413, detail="File too large")

            # Session timeout check
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                if not verify_session_timeout(token):
                    raise HTTPException(status_code=440, detail="Session has expired")

            # XSS protection
            self._check_xss(request)

            # Get client IP for logging
            client_ip = self._get_client_ip(request)

            # Log request
            audit_logger.log_security_event(
                user_id=request.state.user.id if hasattr(request.state, "user") else "anonymous",
                action="incoming_request",
                ip_address=client_ip,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params)
                }
            )

            # Process request
            response = await call_next(request)

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = self._get_csp_header()

            return response

        except HTTPException as exc:
            # Log security violations
            audit_logger.log_security_event(
                user_id=request.state.user.id if hasattr(request.state, "user") else "anonymous",
                action="security_violation",
                ip_address=self._get_client_ip(request),
                status="error",
                details={
                    "error_code": exc.status_code,
                    "error_detail": exc.detail
                }
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

    def _is_valid_content_type(self, content_type: str) -> bool:
        """Validate allowed content types."""
        allowed_types = [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded"
        ]
        return any(allowed in content_type.lower() for allowed in allowed_types)

    def _check_xss(self, request: Request) -> None:
        """Check for potential XSS attacks in request parameters."""
        # XSS pattern matching
        xss_patterns = [
            r"<script[^>]*>[\s\S]*?</script>",
            r"javascript:",
            r"onerror=",
            r"onload=",
            r"eval\(",
            r"document\.cookie"
        ]

        # Check query parameters
        for param in request.query_params.values():
            if any(re.search(pattern, param, re.IGNORECASE) for pattern in xss_patterns):
                raise HTTPException(status_code=400, detail="Potential XSS attack detected")

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request headers."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_csp_header(self) -> str:
        """Generate Content Security Policy header."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )