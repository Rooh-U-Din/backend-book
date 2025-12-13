"""
Agent Orchestrator Service

Central coordinator for skill invocations. Handles context building,
skill execution, logging, and error handling.
"""

import time
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models.database import SkillInvocation, UserProfile
from models.skills import SkillInvokeRequest, SkillInvokeResponse, SkillResult as PydanticSkillResult
from services.skills.base import AgentContext, SkillResult
from services.skills.registry import skill_registry


class AgentOrchestrator:
    """
    Orchestrates skill invocations.

    Responsibilities:
    - Build AgentContext from request and session data
    - Route requests to appropriate skills
    - Log invocations to database
    - Handle errors and timeouts
    """

    async def invoke_skill(
        self,
        request: SkillInvokeRequest,
        session: dict,
        db: Session,
    ) -> SkillInvokeResponse:
        """
        Invoke a skill with the given request and context.

        Args:
            request: The skill invocation request
            session: BetterAuth session data
            db: Database session for logging

        Returns:
            SkillInvokeResponse with result and metadata

        Raises:
            ValueError: If skill not found or invalid input
            Exception: If skill execution fails
        """
        start_time = time.time()
        trace_id = uuid.uuid4()
        user_data = session.get('user', {})

        # Get skill from registry
        skill = skill_registry.get_enabled(request.skill_id)
        if not skill:
            raise ValueError(f"Skill '{request.skill_id}' not found or disabled")

        # Build context
        context = self._build_context(
            user_data=user_data,
            request=request,
            trace_id=str(trace_id),
            db=db,
        )

        # Prepare input kwargs from request
        input_kwargs = self._extract_input_kwargs(request)

        # Validate input
        skill.validate_input(**input_kwargs)

        # Execute skill
        status = "success"
        error_message = None
        result: Optional[SkillResult] = None

        try:
            result = await skill.execute(context, **input_kwargs)
        except Exception as e:
            status = "error"
            error_message = str(e)
            raise
        finally:
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Log invocation
            self._log_invocation(
                db=db,
                user_id=user_data.get('id'),
                skill_id=request.skill_id,
                trace_id=trace_id,
                input_text=self._get_input_preview(input_kwargs),
                output_text=result.content if result else None,
                status=status,
                latency_ms=latency_ms,
                context=context.to_dict(),
                error_message=error_message,
            )

        # Build response
        return SkillInvokeResponse(
            skill_id=request.skill_id,
            trace_id=trace_id,
            result=PydanticSkillResult(
                content=result.content,
                citations=[
                    {"chapter_id": c.chapter_id, "chapter_title": c.chapter_title,
                     "section_title": c.section_title, "url": c.url}
                    for c in (result.citations or [])
                ] if result.citations else None,
                suggestions=[
                    {"type": s.type, "skill_id": s.skill_id, "label": s.label,
                     "description": s.description}
                    for s in (result.suggestions or [])
                ] if result.suggestions else None,
            ),
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
        )

    def _build_context(
        self,
        user_data: dict,
        request: SkillInvokeRequest,
        trace_id: str,
        db: Session,
    ) -> AgentContext:
        """Build AgentContext from session and request data."""
        user_id = user_data.get('id')

        # Fetch user profile if available (for personalization skill)
        user_profile = None
        if user_id:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile:
                user_profile = {
                    'expertise_level': profile.expertise_level,
                    'programming_languages': profile.programming_languages,
                    'learning_goals': profile.learning_goals,
                    'profile_completed': profile.profile_completed,
                }

        return AgentContext(
            user_id=user_id or "",
            user_email=user_data.get('email', ""),
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc),
            chapter_id=request.input.chapter_id,
            chapter_title=None,  # Could be fetched from content service
            selected_text=request.input.selected_text,
            user_profile=user_profile,
        )

    def _extract_input_kwargs(self, request: SkillInvokeRequest) -> Dict[str, Any]:
        """Extract input parameters from request as kwargs."""
        input_data = request.input
        kwargs = {}

        if input_data.selected_text is not None:
            kwargs['selected_text'] = input_data.selected_text
        if input_data.code_or_error is not None:
            kwargs['code_or_error'] = input_data.code_or_error
        if input_data.chapter_id is not None:
            kwargs['chapter_id'] = input_data.chapter_id
        if input_data.topic is not None:
            kwargs['topic'] = input_data.topic
        if input_data.preserve_terms is not None:
            kwargs['preserve_terms'] = input_data.preserve_terms

        return kwargs

    def _get_input_preview(self, input_kwargs: Dict[str, Any], max_length: int = 500) -> str:
        """Get a truncated preview of input for logging."""
        # Prioritize the main content fields
        for field in ['selected_text', 'code_or_error']:
            if field in input_kwargs and input_kwargs[field]:
                text = input_kwargs[field]
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text

        # Fallback to JSON representation
        preview = json.dumps(input_kwargs)
        if len(preview) > max_length:
            return preview[:max_length] + "..."
        return preview

    def _log_invocation(
        self,
        db: Session,
        user_id: Optional[str],
        skill_id: str,
        trace_id: uuid.UUID,
        input_text: Optional[str],
        output_text: Optional[str],
        status: str,
        latency_ms: int,
        context: Dict[str, Any],
        error_message: Optional[str],
    ) -> None:
        """Log skill invocation to database."""
        try:
            invocation = SkillInvocation(
                user_id=user_id,
                skill_id=skill_id,
                trace_id=trace_id,
                input_text=input_text,
                output_text=output_text[:2000] if output_text and len(output_text) > 2000 else output_text,
                status=status,
                latency_ms=latency_ms,
                context=context,
                error_message=error_message,
            )
            db.add(invocation)
            db.commit()

            # Structured logging
            log_data = {
                "event": "skill_invocation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": str(trace_id),
                "user_id": user_id,
                "skill_id": skill_id,
                "status": status,
                "latency_ms": latency_ms,
            }
            if error_message:
                log_data["error"] = error_message
            print(json.dumps(log_data))

        except Exception as e:
            # Don't fail the request if logging fails
            print(json.dumps({
                "event": "skill_invocation_log_error",
                "error": str(e),
                "trace_id": str(trace_id),
            }))


# Global singleton instance
agent_orchestrator = AgentOrchestrator()


def get_orchestrator() -> AgentOrchestrator:
    """Get the global orchestrator instance."""
    return agent_orchestrator
