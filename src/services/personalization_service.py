"""
Content Personalization Service using Gemini API
Adapts chapter content based on user profile
"""

import os
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

import google.generativeai as genai

from models.database import User, UserProfile, PersonalizedContent


class PersonalizationService:
    """Service for personalizing chapter content based on user profiles"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

        # Cache duration (7 days)
        self.cache_duration = timedelta(days=7)

    def _compute_profile_hash(self, profile: UserProfile) -> str:
        """Compute a hash of the profile for caching"""
        profile_str = f"{profile.expertise_level}:{','.join(sorted(profile.programming_languages or []))}:{profile.learning_goals or ''}"
        return hashlib.md5(profile_str.encode()).hexdigest()[:16]

    def _get_cached_content(
        self,
        chapter_id: str,
        profile_hash: str,
        db: Session
    ) -> Optional[PersonalizedContent]:
        """Get cached personalized content if available and not expired"""
        cached = db.query(PersonalizedContent).filter(
            PersonalizedContent.chapter_id == chapter_id,
            PersonalizedContent.profile_hash == profile_hash,
            PersonalizedContent.is_cached == True
        ).first()

        if cached and cached.expires_at and cached.expires_at > datetime.utcnow():
            return cached

        return None

    def _save_to_cache(
        self,
        chapter_id: str,
        user_id: str,
        profile_hash: str,
        content: str,
        db: Session
    ) -> PersonalizedContent:
        """Save personalized content to cache"""
        # Remove old cached versions for this chapter/profile
        db.query(PersonalizedContent).filter(
            PersonalizedContent.chapter_id == chapter_id,
            PersonalizedContent.profile_hash == profile_hash
        ).delete()

        cached = PersonalizedContent(
            chapter_id=chapter_id,
            user_id=user_id,
            profile_hash=profile_hash,
            personalized_content=content,
            is_cached=True,
            expires_at=datetime.utcnow() + self.cache_duration
        )
        db.add(cached)
        db.commit()
        db.refresh(cached)
        return cached

    def _build_personalization_prompt(
        self,
        profile: UserProfile,
        original_content: str
    ) -> str:
        """Build the prompt for Gemini to personalize content"""
        expertise_descriptions = {
            'beginner': 'a beginner who is new to programming and robotics',
            'intermediate': 'an intermediate learner with some programming experience',
            'expert': 'an expert with professional programming and robotics experience'
        }

        expertise_desc = expertise_descriptions.get(
            profile.expertise_level,
            'an intermediate learner'
        )

        languages = ', '.join(profile.programming_languages or ['Python'])
        goals = profile.learning_goals or 'learning about physical AI and humanoid robotics'

        prompt = f"""You are an expert educational content adapter. Your task is to personalize the following chapter content for a specific learner.

LEARNER PROFILE:
- Experience Level: {profile.expertise_level} ({expertise_desc})
- Programming Languages Known: {languages}
- Learning Goals: {goals}

ADAPTATION GUIDELINES:
1. **For Beginners**: Add more explanations, simplify technical jargon, include prerequisite concepts, use more analogies
2. **For Intermediate**: Balance theory and practice, add connections to their known languages
3. **For Experts**: Focus on advanced concepts, skip basics, add edge cases and optimization tips

IMPORTANT RULES:
- Preserve ALL code blocks exactly as they are (do not modify code syntax)
- Keep the same markdown structure (headers, lists, etc.)
- Preserve all images and diagrams references
- Keep the same overall length (within 20% variation)
- Adapt explanations, not the technical content itself
- Add relevant examples using their known programming languages when helpful
- Maintain educational accuracy

ORIGINAL CONTENT:
{original_content}

Please provide the personalized version of this content, adapted for the learner's profile while following all the rules above. Output only the personalized content in markdown format, no additional commentary."""

        return prompt

    async def personalize_content(
        self,
        user: User,
        chapter_id: str,
        original_content: str,
        db: Session
    ) -> tuple[str, bool, str]:
        """
        Personalize chapter content for a user based on their profile.

        Returns:
            tuple: (personalized_content, is_cached, profile_hash)
        """
        # Get user profile
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == user.id
        ).first()

        if not profile or not profile.profile_completed:
            # Return original content if no profile
            return original_content, False, ""

        profile_hash = self._compute_profile_hash(profile)

        # Check cache first
        cached = self._get_cached_content(chapter_id, profile_hash, db)
        if cached:
            return cached.personalized_content, True, profile_hash

        # Generate personalized content
        prompt = self._build_personalization_prompt(profile, original_content)

        try:
            response = self.model.generate_content(prompt)
            personalized_content = response.text

            # Save to cache
            self._save_to_cache(
                chapter_id=chapter_id,
                user_id=str(user.id),
                profile_hash=profile_hash,
                content=personalized_content,
                db=db
            )

            return personalized_content, False, profile_hash

        except Exception as e:
            print(f"Personalization failed: {e}")
            # Return original content on error
            return original_content, False, ""

    def get_personalization_status(
        self,
        user: User,
        chapter_id: str,
        db: Session
    ) -> dict:
        """Check if personalized content exists for a chapter"""
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == user.id
        ).first()

        if not profile or not profile.profile_completed:
            return {
                "chapter_id": chapter_id,
                "is_personalized": False,
                "profile_hash": None,
                "cached_at": None
            }

        profile_hash = self._compute_profile_hash(profile)
        cached = self._get_cached_content(chapter_id, profile_hash, db)

        return {
            "chapter_id": chapter_id,
            "is_personalized": cached is not None,
            "profile_hash": profile_hash if cached else None,
            "cached_at": cached.created_at.isoformat() if cached else None
        }


# Singleton instance
_personalization_service: Optional[PersonalizationService] = None


def get_personalization_service() -> PersonalizationService:
    """Get the personalization service singleton"""
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService()
    return _personalization_service
