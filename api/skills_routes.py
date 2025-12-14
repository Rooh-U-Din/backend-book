"""
Skills API Routes

Provides endpoints for skill invocation and management.
All endpoints require BetterAuth authentication.

Endpoints:
- POST /api/skills/invoke - Invoke a skill
- GET /api/skills - List available skills
- GET /api/skills/history - Get user's invocation history
- GET /api/skills/{trace_id} - Get invocation details
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from models.skills import (
    SkillInvokeRequest,
    SkillInvokeResponse,
    SkillListResponse,
    SkillInfo,
    SkillHistoryResponse,
    SkillInvocationSummary,
    SkillInvocationDetail,
    ErrorResponse,
)
from models.database import SkillInvocation
from services.session_validator import get_session
from services.database_service import get_db
from services.agent_orchestrator import get_orchestrator
from services.skills.registry import skill_registry

router = APIRouter(prefix="/api/skills", tags=["Skills"])


@router.post(
    "/invoke",
    response_model=SkillInvokeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Skill not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def invoke_skill(
    request: SkillInvokeRequest,
    session: dict = Depends(get_session),
    db: Session = Depends(get_db),
):
    """
    Invoke a skill with provided input and context.

    Requires authentication. Returns generated content with trace ID for debugging.
    """
    # Validate skill exists
    if not skill_registry.is_registered(request.skill_id):
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{request.skill_id}' not found",
        )

    skill = skill_registry.get_enabled(request.skill_id)
    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{request.skill_id}' is disabled",
        )

    try:
        orchestrator = get_orchestrator()
        response = await orchestrator.invoke_skill(request, session, db)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill execution failed: {str(e)}")


@router.get(
    "",
    response_model=SkillListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def list_skills(
    session: dict = Depends(get_session),
):
    """
    List all available (enabled) skills.

    Returns skill metadata including ID, name, description, and input schema.
    """
    skills = skill_registry.list_all(enabled_only=True)
    return SkillListResponse(
        skills=[
            SkillInfo(
                id=s.skill_id,
                name=s.name,
                description=s.description,
                version=s.version,
                enabled=s.enabled,
                input_schema=s.input_schema,
            )
            for s in skills
        ]
    )


@router.get(
    "/history",
    response_model=SkillHistoryResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
async def get_skill_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    skill_id: Optional[str] = Query(default=None),
    session: dict = Depends(get_session),
    db: Session = Depends(get_db),
):
    """
    Get user's skill invocation history.

    Returns recent invocations with pagination support.
    Optionally filter by skill_id.
    """
    user_id = session.get('user', {}).get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in session")

    # Build query
    query = db.query(SkillInvocation).filter(SkillInvocation.user_id == user_id)

    if skill_id:
        query = query.filter(SkillInvocation.skill_id == skill_id)

    # Get total count
    total = query.count()

    # Get paginated results
    invocations = (
        query
        .order_by(SkillInvocation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return SkillHistoryResponse(
        invocations=[
            SkillInvocationSummary(
                trace_id=inv.trace_id,
                skill_id=inv.skill_id,
                status=inv.status or "success",
                latency_ms=inv.latency_ms,
                created_at=inv.created_at,
            )
            for inv in invocations
            if inv.trace_id  # Filter out old records without trace_id
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{trace_id}",
    response_model=SkillInvocationDetail,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Invocation not found"},
    },
)
async def get_skill_invocation(
    trace_id: UUID,
    session: dict = Depends(get_session),
    db: Session = Depends(get_db),
):
    """
    Get details of a specific skill invocation by trace ID.

    Only returns invocations belonging to the authenticated user.
    """
    user_id = session.get('user', {}).get('id')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in session")

    invocation = (
        db.query(SkillInvocation)
        .filter(
            SkillInvocation.trace_id == trace_id,
            SkillInvocation.user_id == user_id,
        )
        .first()
    )

    if not invocation:
        raise HTTPException(status_code=404, detail="Invocation not found")

    return SkillInvocationDetail(
        trace_id=invocation.trace_id,
        skill_id=invocation.skill_id,
        status=invocation.status or "success",
        latency_ms=invocation.latency_ms,
        created_at=invocation.created_at,
        input_preview=invocation.input_text[:500] if invocation.input_text else None,
        output_preview=invocation.output_text[:500] if invocation.output_text else None,
        context=invocation.context,
    )
