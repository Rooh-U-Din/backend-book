"""
Authentication service for JWT handling and user management
"""

import os
import bcrypt
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models.database import User, UserProfile
from models.auth import SignUpRequest, SignInRequest, AuthResponse, UserResponse
from services.database_service import get_db

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-min-32-chars-here")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

security = HTTPBearer(auto_error=False)


class AuthService:
    """Service for handling authentication operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        """Create a JWT token for a user"""
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def signup(self, request: SignUpRequest, db: Session) -> AuthResponse:
        """Register a new user"""
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create user with verification token (FR-026)
        password_hash = self.hash_password(request.password)
        verification_token = secrets.token_urlsafe(32)
        user = User(
            email=request.email,
            name=request.name,
            password_hash=password_hash,
            email_verified=False,
            verification_token=verification_token,
            verification_expires=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.add(user)
        db.flush()

        # TODO: Send verification email via SMTP
        # For development, the token is available in the database

        # Create empty profile
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(user)

        # Generate token
        token = self.create_token(str(user.id), user.email)

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            token=token,
            profile_completed=False
        )

    def signin(self, request: SignInRequest, db: Session) -> AuthResponse:
        """Sign in an existing user"""
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not self.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Get profile status
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        profile_completed = profile.profile_completed if profile else False

        # Generate token
        token = self.create_token(str(user.id), user.email)

        return AuthResponse(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            token=token,
            profile_completed=profile_completed
        )

    def get_user_by_id(self, user_id: str, db: Session) -> Optional[User]:
        """Get a user by their ID"""
        try:
            uuid_id = UUID(user_id)
            return db.query(User).filter(User.id == uuid_id).first()
        except ValueError:
            return None


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the auth service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    auth_service = get_auth_service()
    payload = auth_service.decode_token(credentials.credentials)

    user = auth_service.get_user_by_id(payload["user_id"], db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency to optionally get the current authenticated user"""
    if not credentials:
        return None

    try:
        auth_service = get_auth_service()
        payload = auth_service.decode_token(credentials.credentials)
        return auth_service.get_user_by_id(payload["user_id"], db)
    except HTTPException:
        return None
