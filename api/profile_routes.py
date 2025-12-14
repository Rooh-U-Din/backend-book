"""
User profile API routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.auth import UserProfileRequest, QuestionnaireRequest, UserProfileResponse
from models.database import User
from services.auth_service import get_current_user
from services.profile_service import get_profile_service
from services.database_service import get_db

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's profile.
    """
    profile_service = get_profile_service()
    return profile_service.get_profile(current_user, db)


@router.put("", response_model=UserProfileResponse)
async def update_profile(
    request: UserProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.
    """
    profile_service = get_profile_service()
    return profile_service.update_profile(current_user, request, db)


@router.post("/questionnaire", response_model=UserProfileResponse)
async def submit_questionnaire(
    request: QuestionnaireRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit the background questionnaire.
    This marks the profile as completed.
    """
    profile_service = get_profile_service()
    return profile_service.submit_questionnaire(current_user, request, db)
