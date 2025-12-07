"""
Translation API Routes

Handles chapter translation requests.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from models.translation import SupportedLanguage, TranslationResponse
from services.translation_service import get_translation_service

router = APIRouter(prefix="/api/chapter", tags=["translation"])


class TranslateRequest(BaseModel):
    """Request body for translation endpoint"""
    chapterId: str = Field(..., description="Chapter identifier")
    targetLanguage: str = Field(default="urdu", description="Target language")
    content: str = Field(..., description="Chapter content to translate")


class TranslateResponse(BaseModel):
    """Response body for translation endpoint"""
    chapterId: str
    urduContent: str
    cached: bool
    translatedAt: str
    latencyMs: int


class PreferenceRequest(BaseModel):
    """Request body for setting language preference"""
    chapterId: str
    language: str = Field(default="english")


class PreferenceResponse(BaseModel):
    """Response body for language preference"""
    chapterId: str
    language: str
    updatedAt: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_chapter(request_data: TranslateRequest, request: Request):
    """
    Translate chapter content to Urdu.

    Args:
        request_data: Translation request with chapterId, targetLanguage, content

    Returns:
        TranslateResponse with translated content
    """
    try:
        # Validate target language
        try:
            target_lang = SupportedLanguage(request_data.targetLanguage.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request_data.targetLanguage}. Supported: urdu, english"
            )

        # Validate content
        if not request_data.content or len(request_data.content.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Content must be at least 10 characters"
            )

        # Get translation service
        translation_service = get_translation_service()

        # Perform translation
        response, latency_ms = await translation_service.translate_chapter(
            chapter_id=request_data.chapterId,
            content=request_data.content,
            target_language=target_lang
        )

        return TranslateResponse(
            chapterId=response.chapter_id,
            urduContent=response.translated_content,
            cached=response.cached,
            translatedAt=response.translated_at.isoformat(),
            latencyMs=latency_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Translation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/preference", response_model=PreferenceResponse)
async def set_language_preference(request_data: PreferenceRequest, request: Request):
    """
    Set user's language preference for a chapter.

    Args:
        request_data: Preference request with chapterId and language

    Returns:
        PreferenceResponse with updated preference
    """
    try:
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID", "anonymous")

        # Validate language
        try:
            language = SupportedLanguage(request_data.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request_data.language}"
            )

        # Get translation service
        translation_service = get_translation_service()

        # Set preference
        preference = translation_service.set_user_preference(
            session_id=session_id,
            chapter_id=request_data.chapterId,
            language=language
        )

        return PreferenceResponse(
            chapterId=preference.chapter_id,
            language=preference.preferred_language.value,
            updatedAt=preference.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Preference error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set preference: {str(e)}"
        )


@router.get("/preference/{chapter_id}")
async def get_language_preference(chapter_id: str, request: Request):
    """
    Get user's language preference for a chapter.

    Args:
        chapter_id: Chapter identifier

    Returns:
        User's language preference or default (english)
    """
    try:
        session_id = request.headers.get("X-Session-ID", "anonymous")
        translation_service = get_translation_service()

        preference = translation_service.get_user_preference(
            session_id=session_id,
            chapter_id=chapter_id
        )

        if preference:
            return {
                "chapterId": preference.chapter_id,
                "language": preference.preferred_language.value,
                "updatedAt": preference.updated_at.isoformat()
            }

        # Default to English
        return {
            "chapterId": chapter_id,
            "language": "english",
            "updatedAt": None
        }

    except Exception as e:
        print(f"Get preference error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get preference: {str(e)}"
        )


@router.get("/translation-stats")
async def get_translation_stats():
    """Get translation cache statistics"""
    try:
        translation_service = get_translation_service()
        return translation_service.get_cache_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )
