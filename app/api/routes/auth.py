"""Authentication routes"""

from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.core.phi_redaction import sanitize_error_message

router = APIRouter()
security_basic = HTTPBasic()


# Mock user database (in production, this would be a real database)
# For demo purposes, we'll use a simple dict
# In production, passwords should be hashed and stored securely
MOCK_USERS = {
    "admin": {
        "user_id": UUID("850e8400-e29b-41d4-a716-446655440000"),  # UUID for admin user
        "hashed_password": "$2b$12$2d/PSQeAC16Gfjq2tCXp/OJxTGwuWP.WV9YzcFQ8rVG9pdjGsbe5O",  # "admin"
        "email": "admin@example.com",
        "role": "ADMIN",
    },
    "provider1": {
        "user_id": UUID("850e8400-e29b-41d4-a716-446655440001"),  # UUID for provider1 user
        "hashed_password": "$2b$12$2d/PSQeAC16Gfjq2tCXp/OJxTGwuWP.WV9YzcFQ8rVG9pdjGsbe5O",  # "admin"
        "email": "provider1@example.com",
        "role": "USER",
    },
}


class TokenResponse(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str = "bearer"


def verify_user(credentials: HTTPBasicCredentials) -> dict:
    """
    Verify user credentials.
    
    Args:
        credentials: Basic auth credentials
    
    Returns:
        User information if valid
    
    Raises:
        HTTPException: If credentials are invalid
    """
    username = credentials.username
    password = credentials.password
    
    user = MOCK_USERS.get(username)
    if user is None:
        error_msg = "Invalid username or password"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not verify_password(password, user["hashed_password"]):
        error_msg = "Invalid username or password"
        safe_msg = sanitize_error_message(error_msg)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=safe_msg,
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user


@router.post("/login", response_model=TokenResponse, tags=["authentication"])
async def login(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """
    Login endpoint to obtain JWT access token.
    
    Uses HTTP Basic Authentication. Returns a JWT token for use in subsequent requests.
    
    Example credentials:
    - Username: admin, Password: admin
    - Username: provider1, Password: admin
    """
    user = verify_user(credentials)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Convert UUID to string for JWT token (JWT doesn't support UUID type directly)
    user_id_str = str(user["user_id"])
    access_token = create_access_token(
        data={"sub": user_id_str, "email": user["email"], "role": user["role"]},
        expires_delta=access_token_expires,
    )
    
    return TokenResponse(access_token=access_token)
