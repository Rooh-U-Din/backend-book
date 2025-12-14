"""
Pydantic models for Skill API requests and responses.

Based on OpenAPI contract: specs/002-reusable-intelligence-subagents/contracts/api-openapi.yaml
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


class SkillInput(BaseModel):
    """Input parameters for skill invocation."""
    selected_text: Optional[str] = Field(None, max_length=25000, description="User-selected text content")
    code_or_error: Optional[str] = Field(None, max_length=10000, description="Code or error message for debug skill")
    chapter_id: Optional[str] = Field(None, description="Current chapter identifier")
    topic: Optional[str] = Field(None, description="Topic for navigation skill")
    preserve_terms: Optional[List[str]] = Field(None, description="Technical terms to preserve in translation")


class SkillInvokeRequest(BaseModel):
    """Request body for POST /api/skills/invoke."""
    skill_id: str = Field(..., description="Identifier of the skill to invoke")
    input: SkillInput = Field(..., description="Skill-specific input parameters")


class Citation(BaseModel):
    """Reference to related content."""
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    url: Optional[str] = None


class Suggestion(BaseModel):
    """Follow-up action suggestion."""
    type: str = Field(..., description="Type of suggestion: skill, chapter, topic")
    skill_id: Optional[str] = None
    label: str = Field(..., description="Display label")
    description: Optional[str] = None


class SkillResult(BaseModel):
    """Result from skill execution."""
    content: str = Field(..., description="Generated content/explanation")
    citations: Optional[List[Citation]] = Field(None, description="Related content references")
    suggestions: Optional[List[Suggestion]] = Field(None, description="Follow-up action suggestions")


class SkillInvokeResponse(BaseModel):
    """Response body for POST /api/skills/invoke."""
    skill_id: str = Field(..., description="Which skill was invoked")
    trace_id: UUID = Field(..., description="Unique trace ID for debugging")
    result: SkillResult = Field(..., description="Skill execution result")
    latency_ms: int = Field(..., description="Processing time in milliseconds")
    timestamp: datetime = Field(..., description="Response timestamp")


class SkillInfo(BaseModel):
    """Skill metadata for listing."""
    id: str
    name: str
    description: str
    version: str
    enabled: bool
    input_schema: Optional[Dict[str, Any]] = None


class SkillListResponse(BaseModel):
    """Response body for GET /api/skills."""
    skills: List[SkillInfo]


class SkillInvocationSummary(BaseModel):
    """Summary of a skill invocation for history."""
    trace_id: UUID
    skill_id: str
    status: str = Field(..., description="success, error, timeout, rate_limited")
    latency_ms: Optional[int] = None
    created_at: datetime


class SkillHistoryResponse(BaseModel):
    """Response body for GET /api/skills/history."""
    invocations: List[SkillInvocationSummary]
    total: int
    offset: int = 0
    limit: int = 20


class SkillInvocationDetail(BaseModel):
    """Detailed skill invocation for GET /api/skills/{trace_id}."""
    trace_id: UUID
    skill_id: str
    status: str
    latency_ms: Optional[int] = None
    created_at: datetime
    input_preview: Optional[str] = Field(None, description="Truncated input (first 500 chars)")
    output_preview: Optional[str] = Field(None, description="Truncated output (first 500 chars)")
    context: Optional[Dict[str, Any]] = Field(None, description="Context snapshot at invocation time")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    trace_id: Optional[UUID] = Field(None, description="Trace ID for debugging")
