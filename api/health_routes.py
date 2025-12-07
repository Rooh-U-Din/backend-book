"""
Health Check API Routes

Provides health check endpoints for monitoring.

Author: Physical AI & Humanoid Robotics Course
License: MIT
"""

from fastapi import APIRouter
from models.query import HealthCheckResponse
from services.qdrant_service import get_qdrant_service
from services.gemini_service import get_gemini_service
from datetime import datetime
import asyncio

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def comprehensive_health_check():
    """
    Comprehensive health check for all services

    Checks:
    - Qdrant connectivity
    - Gemini API availability
    - Overall system health

    Returns:
        HealthCheckResponse with service statuses
    """
    services = {}

    # Check Qdrant
    try:
        qdrant = get_qdrant_service()
        qdrant_healthy = await qdrant.health_check()
        services["qdrant"] = "connected" if qdrant_healthy else "disconnected"
    except Exception as e:
        services["qdrant"] = f"error: {str(e)}"

    # Check Gemini API
    try:
        gemini = get_gemini_service()
        gemini_healthy = await gemini.health_check()
        services["gemini_api"] = "available" if gemini_healthy else "unavailable"
    except Exception as e:
        services["gemini_api"] = f"error: {str(e)}"

    # Determine overall status
    all_healthy = all(
        status in ["connected", "available"]
        for status in services.values()
    )

    return HealthCheckResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow(),
        services=services
    )
