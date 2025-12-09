"""
Content Personalization API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import User
from models.personalization import (
    PersonalizeRequest,
    PersonalizeResponse,
    PersonalizationStatus
)
from services.auth_service import get_current_user
from services.personalization_service import get_personalization_service
from services.database_service import get_db

router = APIRouter(prefix="/api/personalize", tags=["Personalization"])


@router.post("", response_model=PersonalizeResponse)
async def personalize_content(
    request: PersonalizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Personalize chapter content based on user profile.

    This endpoint takes original chapter content and returns a personalized
    version adapted to the user's expertise level and learning preferences.
    """
    personalization_service = get_personalization_service()

    personalized_content, is_cached, profile_hash = await personalization_service.personalize_content(
        user=current_user,
        chapter_id=request.chapter_id,
        original_content=request.original_content,
        db=db
    )

    return PersonalizeResponse(
        chapter_id=request.chapter_id,
        personalized_content=personalized_content,
        is_cached=is_cached,
        profile_hash=profile_hash
    )


@router.get("/status/{chapter_id}", response_model=PersonalizationStatus)
async def get_personalization_status(
    chapter_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if personalized content exists for a chapter.

    Returns whether cached personalized content is available for the user's
    current profile.
    """
    personalization_service = get_personalization_service()

    status = personalization_service.get_personalization_status(
        user=current_user,
        chapter_id=chapter_id,
        db=db
    )

    return PersonalizationStatus(**status)


@router.delete("/cache/{chapter_id}")
async def clear_personalization_cache(
    chapter_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear cached personalized content for a chapter.

    Use this to force regeneration of personalized content.
    """
    from models.database import PersonalizedContent

    deleted = db.query(PersonalizedContent).filter(
        PersonalizedContent.chapter_id == chapter_id,
        PersonalizedContent.user_id == current_user.id
    ).delete()

    db.commit()

    return {
        "message": f"Cleared {deleted} cached entries for chapter {chapter_id}",
        "chapter_id": chapter_id
    }
