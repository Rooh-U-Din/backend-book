"""
Personalization-related Pydantic models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class PersonalizeRequest(BaseModel):
    """Request to personalize chapter content"""
    chapter_id: str = Field(..., description="Chapter identifier (e.g., 'chapter-1-introduction')")
    original_content: str = Field(..., description="Original chapter content in markdown")


class PersonalizeResponse(BaseModel):
    """Response with personalized content"""
    chapter_id: str
    personalized_content: str
    is_cached: bool = False
    profile_hash: str


class PersonalizationStatus(BaseModel):
    """Status of personalization for a chapter"""
    chapter_id: str
    is_personalized: bool
    profile_hash: Optional[str] = None
    cached_at: Optional[str] = None
