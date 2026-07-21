"""
Rate Limiting Middleware for the AI Loan Decision Platform.

Uses slowapi to enforce rate limits on authentication and prediction endpoints.

Configuration:
- Auth endpoints: 5 requests per minute per IP
- Prediction endpoints: 10 requests per minute per IP
- Simulation endpoints: 20 requests per minute per IP

Requirements: 18.5, 18.6
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# Create limiter instance using client IP as key
limiter = Limiter(key_func=get_remote_address)

# Rate limit strings
AUTH_RATE_LIMIT = "5/minute"
PREDICTION_RATE_LIMIT = "10/minute"
SIMULATION_RATE_LIMIT = "20/minute"


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors.

    Returns 429 Too Many Requests with a descriptive message.
    Requirement 18.5.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please wait before trying again.",
            "retry_after": str(exc.detail),
        },
    )
