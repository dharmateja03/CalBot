"""
Authentication routes
Handles Google OAuth login/logout and token management
"""

from fastapi import APIRouter, HTTPException, Request, Response, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta
import secrets

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
import jwt

from app.services.database_service import DatabaseService

router = APIRouter()

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# Google OAuth Scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# Fallback in-memory storage for when database is not configured
user_tokens = {}
user_sessions = {}


class LoginRequest(BaseModel):
    google_token: str


class User(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


def create_jwt_token(user_id: str, email: str) -> str:
    """Create JWT token for session management"""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.get("/google")
async def google_auth_redirect():
    """
    Initiate Google OAuth flow
    Redirects user to Google consent screen
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env"
        )

    # Create OAuth flow
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Request refresh token
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )

    # Store state for security validation (TODO: use Redis/database)
    # For now, just store in memory
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_auth_callback(code: str, state: Optional[str] = None):
    """
    Handle Google OAuth callback
    Exchange authorization code for access token and refresh token
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    try:
        # Create OAuth flow
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )

        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user info from Google
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()

        google_user_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        # Create or update user in database
        user = DatabaseService.create_or_update_user(
            google_id=google_user_id,
            email=email,
            name=name,
            picture=picture
        )

        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        user_id = user['id']  # Use DB UUID, not Google ID

        # Store OAuth tokens in database
        DatabaseService.store_oauth_tokens(
            user_id=user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes,
            expires_at=credentials.expiry
        )

        # Fallback: Also store in memory for compatibility
        user_tokens[user_id] = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }

        # Create JWT session token
        session_token = create_jwt_token(user_id, email)

        # Store session in database
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        DatabaseService.create_session(user_id, session_token, expiration)

        # Fallback: Also store in memory
        user_sessions[session_token] = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'picture': picture,
            'created_at': datetime.utcnow().isoformat()
        }

        print(f"✅ User authenticated: {email}")

        # Redirect to frontend with token
        redirect_url = f"{FRONTEND_URL}/auth/success?token={session_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        print(f"❌ OAuth callback error: {str(e)}")
        error_url = f"{FRONTEND_URL}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Handle user logout and revoke tokens"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    # Remove from session storage
    if token in user_sessions:
        user_data = user_sessions[token]
        user_id = user_data.get('user_id')

        # Remove tokens
        if user_id in user_tokens:
            del user_tokens[user_id]

        del user_sessions[token]
        print(f"✅ User logged out: {user_data.get('email')}")

    return {"message": "Logged out successfully", "success": True}


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    # Verify JWT token
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Get user session
    if token not in user_sessions:
        raise HTTPException(status_code=401, detail="Session not found")

    user_data = user_sessions[token]

    return {
        "id": user_data['user_id'],
        "email": user_data['email'],
        "name": user_data['name'],
        "picture": user_data.get('picture')
    }


@router.get("/tokens/{user_id}")
async def get_user_tokens(user_id: str):
    """
    Get stored Google OAuth tokens for a user
    Used internally by calendar service
    """
    # Try database first
    tokens = DatabaseService.get_oauth_tokens(user_id)

    if tokens:
        # Convert database format to expected format
        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_uri': tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
            'client_id': tokens['client_id'],
            'client_secret': tokens['client_secret'],
            'scopes': tokens['scopes'],
            'expiry': tokens.get('expires_at')
        }

    # Fallback to in-memory storage
    if user_id in user_tokens:
        return user_tokens[user_id]

    raise HTTPException(status_code=404, detail="User tokens not found")


@router.post("/refresh")
async def refresh_google_token(user_id: str):
    """
    Refresh Google OAuth access token using refresh token
    """
    if user_id not in user_tokens:
        raise HTTPException(status_code=404, detail="User tokens not found")

    try:
        token_data = user_tokens[user_id]

        # Create credentials from stored data
        credentials = Credentials(
            token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )

        # Refresh the token
        credentials.refresh(GoogleRequest())

        # Update stored tokens
        user_tokens[user_id].update({
            'access_token': credentials.token,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        })

        print(f"✅ Refreshed token for user: {user_id}")

        return {
            "success": True,
            "access_token": credentials.token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }

    except Exception as e:
        print(f"❌ Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")
