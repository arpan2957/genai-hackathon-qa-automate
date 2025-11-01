import os
from typing import Dict, Any
from fastapi import Depends, HTTPException, Request, Header # Added Header
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from datetime import datetime
from audit import log_audit_event
from config import AGENT_API_KEY # Added AGENT_API_KEY import

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_user_from_request(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    try:
        token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        return None

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        decoded_token = auth.verify_id_token(token)
        log_audit_event(request, decoded_token, "user_login", details={})
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})

async def is_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Checks if the user has an 'admin' custom claim in their token."""
    if user.get('admin') is True:
        return user
    
    raise HTTPException(
        status_code=403, 
        detail="User is not authorized to perform this action."
    )

async def verify_agent_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> bool:
    """
    Verifies the API key provided in the X-API-Key header for agent access.
    """
    if not AGENT_API_KEY:
        raise HTTPException(status_code=500, detail="Agent API Key not configured on server.")
    if x_api_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Agent API Key.")
    return True
