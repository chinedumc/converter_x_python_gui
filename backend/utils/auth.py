from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Initialize logger
log = logging.getLogger('auth')

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "5"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthError(Exception):
    def __init__(self, detail: str):
        self.detail = detail

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        log.info(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt
        
    except Exception as e:
        log.error(f"Failed to create access token: {str(e)}")
        raise AuthError("Could not create access token")

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
        
    except JWTError as e:
        log.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Security(oauth2_scheme)) -> dict:
    """Get current user from token."""
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise AuthError("Token missing user identifier")
            
        # Check token expiration
        exp = payload.get("exp")
        if not exp or datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise AuthError("Token has expired")
            
        return {"user_id": user_id}
        
    except Exception as e:
        log.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_session_timeout(token: str) -> bool:
    """Verify if the session has timed out."""
    try:
        payload = verify_token(token)
        exp = payload.get("exp")
        
        if not exp:
            return False
            
        # Check if token is within timeout window
        expiration = datetime.utcfromtimestamp(exp)
        current_time = datetime.utcnow()
        time_difference = expiration - current_time
        
        # Session is valid if within timeout window
        return time_difference <= timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    except Exception as e:
        log.warning(f"Session verification failed: {str(e)}")
        return False

def refresh_token(token: str) -> str:
    """Refresh an existing token if it's still valid."""
    try:
        # Verify current token
        payload = verify_token(token)
        
        # Create new token with updated expiration
        new_token = create_access_token(
            data={"sub": payload.get("sub")},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        log.info(f"Token refreshed for user: {payload.get('sub')}")
        return new_token
        
    except Exception as e:
        log.error(f"Token refresh failed: {str(e)}")
        raise AuthError("Could not refresh token")