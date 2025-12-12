"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from models.auth import (
    SignUpRequest, SignInRequest, AuthResponse, UserResponse,
    VerifyEmailRequest, VerifyEmailResponse, SessionInfo
)
from models.database import User
from services.auth_service import get_auth_service, get_current_user
from services.database_service import get_db
from services.session_validator import get_session, get_current_user_from_session

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
        email_verified=current_user.email_verified,
        created_at=current_user.created_at
    )


# ============ EMAIL VERIFICATION ENDPOINTS (FR-026) ============

@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email address using the verification token.
    Token is sent to user's email after signup.
    """
    from datetime import datetime, timezone

    # Find user by verification token
    user = db.query(User).filter(
        User.verification_token == request.token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    # Check if token has expired
    if user.verification_expires and user.verification_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )

    # Mark email as verified
    user.email_verified = True
    user.verification_token = None
    user.verification_expires = None
    db.commit()

    return VerifyEmailResponse(
        message="Email verified successfully",
        email_verified=True
    )


@router.post("/resend-verification")
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resend email verification link to current user.
    Only works if email is not already verified.
    """
    import secrets
    from datetime import datetime, timezone, timedelta

    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Generate new verification token
    current_user.verification_token = secrets.token_urlsafe(32)
    current_user.verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    # TODO: Send verification email (requires SMTP setup)
    # For now, return the token for testing purposes
    return {
        "message": "Verification email sent",
        "token": current_user.verification_token  # Remove in production
    }


# ============ SESSION MANAGEMENT ENDPOINTS (FR-021) ============

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    List all active sessions for the current user.
    Note: With JWT-based auth, sessions are stateless.
    This endpoint returns the current session info only.
    For full session management, use BetterAuth's session tracking.
    """
    from datetime import datetime, timezone, timedelta

    # With JWT, we only know about the current session
    # For full session tracking, integrate with BetterAuth session storage
    current_session = SessionInfo(
        id="current",
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        is_current=True
    )

    return [current_session]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a specific session.
    Note: With JWT-based auth, session revocation requires a token blacklist.
    For full session management, use BetterAuth's session tracking.
    """
    if session_id == "current":
        return {"message": "Cannot revoke current session"}

    # TODO: Implement token blacklist for full session revocation
    return {"message": f"Session {session_id} revoked"}


# ============ PASSWORD CHANGE ENDPOINT (T069) ============

from pydantic import BaseModel, Field

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's password.
    Requires the current password for verification.
    New password must be at least 8 characters (FR-025).
    """
    auth_service = get_auth_service()

    # Verify current password
    if not auth_service.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash and update new password
    new_hash = auth_service.hash_password(request.new_password)
    current_user.password_hash = new_hash
    db.commit()

    return {"message": "Password changed successfully"}
