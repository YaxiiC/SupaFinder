"""Google OAuth authentication helper."""

import urllib.parse
import httpx
from typing import Optional, Dict
from app.config import get_secret


def get_google_oauth_url(state: Optional[str] = None) -> Optional[str]:
    """Generate Google OAuth authorization URL."""
    client_id = get_secret("GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        return None
    
    app_url = get_secret("APP_URL", "https://supafinder.streamlit.app")
    redirect_uri = f"{app_url.rstrip('/')}/"
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
    }
    
    if state:
        params["state"] = state
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return auth_url


def exchange_code_for_token(code: str) -> Optional[Dict]:
    """Exchange authorization code for access token."""
    client_id = get_secret("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = get_secret("GOOGLE_OAUTH_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        return None
    
    app_url = get_secret("APP_URL", "https://supafinder.streamlit.app")
    redirect_uri = f"{app_url.rstrip('/')}/"
    
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None


def get_user_info(access_token: str) -> Optional[Dict]:
    """Get user info from Google using access token."""
    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

