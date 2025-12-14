"""
User profile management service
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.database import User, UserProfile
from models.auth import UserProfileRequest, QuestionnaireRequest, UserProfileResponse


class ProfileService:
    """Service for managing user profiles"""

    def get_profile(self, user: User, db: Session) -> UserProfileResponse:
        """Get the current user's profile"""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        return UserProfileResponse(
            user_id=str(profile.user_id),
            expertise_level=profile.expertise_level,
            programming_languages=profile.programming_languages or [],
            learning_goals=profile.learning_goals,
            profile_completed=profile.profile_completed,
            updated_at=profile.updated_at
        )

    def update_profile(self, user: User, request: UserProfileRequest, db: Session) -> UserProfileResponse:
        """Update the current user's profile"""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

        if not profile:
            # Create profile if it doesn't exist
            profile = UserProfile(user_id=user.id)
            db.add(profile)

        # Update fields
        profile.expertise_level = request.expertise_level.value
        profile.programming_languages = request.programming_languages
        profile.learning_goals = request.learning_goals
        profile.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(profile)

        return UserProfileResponse(
            user_id=str(profile.user_id),
            expertise_level=profile.expertise_level,
            programming_languages=profile.programming_languages or [],
            learning_goals=profile.learning_goals,
            profile_completed=profile.profile_completed,
            updated_at=profile.updated_at
        )

    def submit_questionnaire(self, user: User, request: QuestionnaireRequest, db: Session) -> UserProfileResponse:
        """Submit the background questionnaire and complete the profile"""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

        if not profile:
            profile = UserProfile(user_id=user.id)
            db.add(profile)

        # Update profile with questionnaire data
        profile.expertise_level = request.expertise_level.value
        profile.programming_languages = request.programming_languages
        profile.learning_goals = request.learning_goals

        # Store full questionnaire responses as JSON
        profile.questionnaire_responses = {
            "version": 1,
            "completed_at": datetime.utcnow().isoformat(),
            "answers": {
                "expertise_level": request.expertise_level.value,
                "programming_languages": request.programming_languages,
                "learning_goals": request.learning_goals,
                "programming_experience_years": request.programming_experience_years,
                "robotics_experience": request.robotics_experience,
                "primary_interest": request.primary_interest,
                "preferred_learning_style": request.preferred_learning_style,
                "time_commitment": request.time_commitment
            }
        }

        profile.profile_completed = True
        profile.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(profile)

        return UserProfileResponse(
            user_id=str(profile.user_id),
            expertise_level=profile.expertise_level,
            programming_languages=profile.programming_languages or [],
            learning_goals=profile.learning_goals,
            profile_completed=profile.profile_completed,
            updated_at=profile.updated_at
        )

    def get_profile_by_user_id(self, user_id: UUID, db: Session) -> Optional[UserProfile]:
        """Get a profile by user ID (internal use)"""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


# Singleton instance
_profile_service: Optional[ProfileService] = None


def get_profile_service() -> ProfileService:
    """Get the profile service singleton"""
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService()
    return _profile_service
