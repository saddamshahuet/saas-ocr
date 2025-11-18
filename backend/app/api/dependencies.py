"""API dependencies for authentication and authorization"""
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models import User, APIKey
import logging

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User object or None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)

        if payload is None:
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()
        return user

    except (JWTError, ValueError) as e:
        logger.warning(f"Invalid token: {e}")
        return None


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from API key

    Args:
        api_key: API key from header
        db: Database session

    Returns:
        User object or None
    """
    if not api_key:
        return None

    try:
        # Find API key in database
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        api_key_obj = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()

        if not api_key_obj:
            return None

        # Update last used
        from datetime import datetime
        api_key_obj.last_used_at = datetime.utcnow()
        api_key_obj.usage_count += 1
        db.commit()

        # Get user
        user = db.query(User).filter(User.id == api_key_obj.user_id).first()
        return user

    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return None


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """
    Get current user from either JWT token or API key

    Args:
        token_user: User from JWT token
        api_key_user: User from API key

    Returns:
        User object

    Raises:
        HTTPException: If no valid authentication provided
    """
    user = token_user or api_key_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (alias for backward compatibility)

    Args:
        current_user: Current user from authentication

    Returns:
        User object
    """
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current superuser (admin only)

    Args:
        current_user: Current user from authentication

    Returns:
        User object if superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superuser access required."
        )
    return current_user


def check_api_calls_remaining(user: User) -> bool:
    """
    Check if user has API calls remaining

    Args:
        user: User object

    Returns:
        True if user has calls remaining

    Raises:
        HTTPException: If user has no calls remaining
    """
    if user.api_calls_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"API call limit exceeded. You have used all {user.api_calls_total} calls. Please upgrade your plan or purchase additional calls."
        )
    return True


async def get_optional_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise (for optional auth)

    Args:
        token_user: User from JWT token
        api_key_user: User from API key

    Returns:
        User object or None
    """
    return token_user or api_key_user
