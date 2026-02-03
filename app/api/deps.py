"""API dependencies (authentication, etc.)"""

from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.core.phi_redaction import sanitize_error_message

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
    
    Returns:
        Decoded token payload with user information
    
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        error_msg = "Could not validate credentials"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        error_msg = "Token missing user identifier"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert string user_id from JWT to UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        # If user_id is not a valid UUID, try to use it as-is (for backward compatibility)
        # But in this system, user_id should always be a UUID
        error_msg = "Invalid user identifier format"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract role from token payload
    role = payload.get("role", "USER")
    
    return {"user_id": user_id, "user_id_str": user_id_str, "role": role, **payload}


async def get_current_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Dependency to ensure the current user is an admin.
    
    Args:
        current_user: Current authenticated user from get_current_user
    
    Returns:
        User information if admin
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.get("role") != "ADMIN":
        error_msg = "Admin access required"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=safe_msg,
        )
    
    return current_user


def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from request"""
    # Check for forwarded IP (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to client host
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return None
