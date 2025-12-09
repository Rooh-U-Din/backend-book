"""
Chapter Translation Models

Database models for caching chapter translations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SupportedLanguage(str, Enum):
    """Supported translation languages"""
    URDU = "urdu"
    ENGLISH = "english"


class TranslationRequest(BaseModel):
    """Request model for chapter translation"""
    chapter_id: str = Field(..., description="Unique chapter identifier (e.g., 'ros2-fundamentals')")
    target_language: SupportedLanguage = Field(default=SupportedLanguage.URDU)
    content: Optional[str] = Field(None, description="Chapter content to translate (optional if cached)")


class TranslationResponse(BaseModel):
    """Response model for chapter translation"""
    chapter_id: str
    language: SupportedLanguage
    translated_content: str
    cached: bool = Field(default=False, description="Whether result was from cache")
    translated_at: datetime


class ChapterTranslation(BaseModel):
    """Database model for cached translations"""
    id: Optional[str] = None
    chapter_id: str
    language: SupportedLanguage
    original_content_hash: str  # MD5 hash to detect content changes
    translated_content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserTranslationPreference(BaseModel):
    """User's translation preference for a chapter"""
    session_id: str
    chapter_id: str
    preferred_language: SupportedLanguage = SupportedLanguage.ENGLISH
    updated_at: datetime = Field(default_factory=datetime.utcnow)
