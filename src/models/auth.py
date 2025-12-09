"""
Pydantic models for authentication and user profiles
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ExpertiseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


# ============ AUTH REQUEST/RESPONSE MODELS ============

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str]
    token: str
    profile_completed: bool


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    created_at: datetime


# ============ PROFILE REQUEST/RESPONSE MODELS ============

class UserProfileRequest(BaseModel):
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    programming_languages: List[str] = Field(default_factory=list, max_length=20)
    learning_goals: Optional[str] = Field(None, max_length=1000)


class QuestionnaireRequest(BaseModel):
    expertise_level: ExpertiseLevel
    programming_languages: List[str] = Field(default_factory=list)
    learning_goals: Optional[str] = None
    programming_experience_years: Optional[int] = Field(None, ge=0, le=50)
    robotics_experience: Optional[str] = Field(None, pattern="^(none|hobbyist|professional)$")
    primary_interest: Optional[str] = Field(None, pattern="^(simulation|hardware|ai|all)$")
    preferred_learning_style: Optional[str] = Field(None, pattern="^(examples|theory|projects)$")
    time_commitment: Optional[str] = Field(None, pattern="^(casual|moderate|intensive)$")


class UserProfileResponse(BaseModel):
    user_id: str
    expertise_level: ExpertiseLevel
    programming_languages: List[str]
    learning_goals: Optional[str]
    profile_completed: bool
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ PERSONALIZATION MODELS ============

class PersonalizeRequest(BaseModel):
    chapter_id: str = Field(..., pattern="^[a-z0-9-]+$", max_length=100)
    content: str = Field(..., min_length=100)


class PersonalizeResponse(BaseModel):
    chapter_id: str
    personalized_content: str
    profile_hash: str
    cached: bool
    latency_ms: int


# ============ SKILLS MODELS ============

class SkillInfo(BaseModel):
    id: str
    name: str
    description: str


class SkillRequest(BaseModel):
    skill_id: str = Field(..., pattern="^(code-explainer|concept-simplifier|prerequisite-finder)$")
    input_text: str = Field(..., min_length=10, max_length=5000)
    chapter_context: Optional[str] = None


class SkillResponse(BaseModel):
    skill_id: str
    output: str
    latency_ms: int
