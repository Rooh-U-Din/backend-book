"""
FastAPI Backend for Physical AI & Humanoid Robotics Book
Production-ready server with middleware and rate limiting
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import time
import json
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from typing import Dict

# Load environment variables
load_dotenv()

# Rate limiting storage (in-memory - use Redis for production)
rate_limit_storage: Dict[str, list] = defaultdict(list)
RATE_LIMIT_QUERIES = 10  # queries per minute
RATE_LIMIT_WINDOW = 60  # seconds

app = FastAPI(
    title="Physical AI & Humanoid Robotics RAG API",
    description="Backend API for RAG chatbot with Gemini integration",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://*.github.io",  # GitHub Pages
]

if os.getenv("ENVIRONMENT") == "development":
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)

    # Structured logging
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "process_time_ms": int(process_time * 1000)
    }
    print(json.dumps(log_data))

    return response


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit by session ID"""
    # Skip rate limiting for health check and docs
    if request.url.path in ["/api/health", "/api/docs", "/api/redoc", "/"]:
        return await call_next(request)

    # Get session ID from header or create new one
    session_id = request.headers.get("X-Session-ID", "anonymous")

    # Clean old entries
    now = time.time()
    rate_limit_storage[session_id] = [
        t for t in rate_limit_storage[session_id]
        if now - t < RATE_LIMIT_WINDOW
    ]

    # Check rate limit
    if len(rate_limit_storage[session_id]) >= RATE_LIMIT_QUERIES:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Maximum {RATE_LIMIT_QUERIES} queries per minute",
                "retry_after": int(RATE_LIMIT_WINDOW - (now - rate_limit_storage[session_id][0]))
            }
        )

    # Record this request
    rate_limit_storage[session_id].append(now)

    return await call_next(request)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Physical AI & Humanoid Robotics RAG API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """Comprehensive health check endpoint"""
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    qdrant_url_set = bool(os.getenv("QDRANT_URL"))
    neon_url_set = bool(os.getenv("NEON_DATABASE_URL"))

    # Check service connectivity (basic check)
    services = {
        "gemini_api": "configured" if gemini_key_set else "missing",
        "qdrant": "configured" if qdrant_url_set else "missing",
        "neon_postgres": "configured" if neon_url_set else "missing"
    }

    all_configured = all(v == "configured" for v in services.values())

    return {
        "status": "healthy" if all_configured else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": services
    }


@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "Test endpoint working!",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "framework": "FastAPI",
            "python_version": "3.11+",
            "features": [
                "RAG chatbot",
                "Vector search with Qdrant",
                "Gemini AI integration",
                "Rate limiting (10 queries/min)",
                "CORS enabled",
                "Structured JSON logging"
            ]
        }
    }


# Include API routers
from api.query_routes import router as query_router
from api.health_routes import router as health_router
from api.translation_routes import router as translation_router

app.include_router(query_router)
app.include_router(health_router)
app.include_router(translation_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )
