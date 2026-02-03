"""API dependencies (authentication, etc.)"""

from typing import Optional
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
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        error_msg = "Token missing user identifier"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"user_id": user_id, **payload}


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
