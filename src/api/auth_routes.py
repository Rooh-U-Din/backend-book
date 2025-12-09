"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from models.auth import SignUpRequest, SignInRequest, AuthResponse, UserResponse
from models.database import User
from services.auth_service import get_auth_service, get_current_user
from services.database_service import get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    Returns a JWT token and creates an empty profile.
    """
    auth_service = get_auth_service()
    return auth_service.signup(request, db)


@router.post("/signin", response_model=AuthResponse)
async def signin(request: SignInRequest, db: Session = Depends(get_db)):
    """
    Sign in with email and password.
    Returns a JWT token.
    """
    auth_service = get_auth_service()
    return auth_service.signin(request, db)


@router.post("/signout")
async def signout(current_user: User = Depends(get_current_user)):
    """
    Sign out the current user.
    Note: With JWT, this is a client-side operation (discard token).
    This endpoint exists for API consistency.
    """
    return {"message": "Signed out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at
    )
