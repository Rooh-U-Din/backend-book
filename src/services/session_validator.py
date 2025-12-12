"""
BetterAuth Session Validator (FR-027)

Validates BetterAuth session cookies sent from the Docusaurus frontend.
BetterAuth runs client-side; FastAPI validates cookies using shared secret.

Cookie format: base64url(payload).base64url(HMAC-SHA256(payload, secret))
"""

import hmac
import base64
import json
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, Request, Depends, status
from sqlalchemy.orm import Session

from models.database import User
from services.database_service import get_db


class BetterAuthSessionValidator:
    """Validates BetterAuth session cookies from the frontend"""

    def __init__(self):
        self.secret = os.getenv("BETTER_AUTH_SECRET", "").encode()
        if len(self.secret) < 32:
            # Allow startup but warn - will fail on validation
            print("WARNING: BETTER_AUTH_SECRET must be at least 32 characters for production")

    def _decode_base64url(self, data: str) -> bytes:
        """Decode base64url data with padding"""
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)

    async def validate_cookie(self, request: Request) -> dict:
        """
        Validate BetterAuth session cookie and return session data.

        Returns:
            dict with session data including:
            - user: {id, email, name, emailVerified}
            - expiresAt: ISO timestamp
            - createdAt: ISO timestamp

        Raises:
            HTTPException 401 for missing/invalid/expired sessions
        """
        cookie_name = "better-auth.session"
        cookie = request.cookies.get(cookie_name)

        if not cookie:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No session cookie"
            )

        if len(self.secret) < 32:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server authentication not configured"
            )

        try:
            # Split cookie into payload and signature
            parts = cookie.rsplit('.', 1)
            if len(parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session format"
                )

            payload_b64, signature_b64 = parts
            payload_bytes = self._decode_base64url(payload_b64)
            signature = self._decode_base64url(signature_b64)

            # Verify HMAC signature
            expected = hmac.new(self.secret, payload_bytes, 'sha256').digest()
            if not hmac.compare_digest(signature, expected):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session signature"
                )

            # Parse session data
            session = json.loads(payload_bytes.decode('utf-8'))

            # Check expiration
            expires_at = session.get('expiresAt')
            if expires_at:
                # Handle ISO format with Z suffix
                expires_str = expires_at.replace('Z', '+00:00')
                expires_dt = datetime.fromisoformat(expires_str)
                if expires_dt < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired"
                    )

            return session

        except HTTPException:
            raise
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session data"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid session: {str(e)}"
            )


# Singleton instance
_validator: Optional[BetterAuthSessionValidator] = None


def get_validator() -> BetterAuthSessionValidator:
    """Get the session validator singleton"""
    global _validator
    if _validator is None:
        _validator = BetterAuthSessionValidator()
    return _validator


# FastAPI Dependencies

async def get_session(request: Request) -> dict:
    """
    Dependency: Get validated session data from BetterAuth cookie.

    Usage:
        @app.get("/protected")
        async def protected_route(session: dict = Depends(get_session)):
            user_id = session["user"]["id"]
            ...
    """
    validator = get_validator()
    return await validator.validate_cookie(request)


async def get_session_optional(request: Request) -> Optional[dict]:
    """
    Dependency: Optionally get session data (returns None if not authenticated).

    Usage:
        @app.get("/maybe-protected")
        async def maybe_protected(session: Optional[dict] = Depends(get_session_optional)):
            if session:
                # Authenticated
            else:
                # Not authenticated
    """
    try:
        validator = get_validator()
        return await validator.validate_cookie(request)
    except HTTPException:
        return None


async def require_verified_email(session: dict = Depends(get_session)) -> dict:
    """
    Dependency: Require email verification (FR-026).

    Usage:
        @app.post("/api/personalize/chapter")
        async def personalize(session: dict = Depends(require_verified_email)):
            # Only verified users can access
            ...
    """
    user = session.get('user', {})
    if not user.get('emailVerified'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required for this feature"
        )
    return session


async def get_current_user_from_session(
    session: dict = Depends(get_session),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: Get User model from BetterAuth session.

    This bridges BetterAuth sessions with our SQLAlchemy User model.
    """
    user_data = session.get('user', {})
    user_id = user_data.get('id')

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session: no user ID"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_verified_user(
    session: dict = Depends(require_verified_email),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: Get verified User model (combines session + email verification + DB lookup).

    Usage:
        @app.post("/api/personalize/chapter")
        async def personalize(user: User = Depends(get_verified_user)):
            # user is authenticated and email-verified
            ...
    """
    return await get_current_user_from_session(session, db)
