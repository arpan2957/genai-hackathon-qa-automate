import os
from typing import Dict, Any
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from datetime import datetime
from audit import log_audit_event

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

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    print(f"Received token: {token[:30]}...") # Print first 30 chars of token
    try:
        decoded_token = auth.verify_id_token(token)
        print(f"Token successfully decoded for user: {decoded_token.get('email')}")
        log_audit_event({
            "user_id": decoded_token.get("uid"),
            "event_type": "user_login",
            "timestamp": datetime.now().isoformat(),
            "email": decoded_token.get("email")
        })
        return decoded_token
    except Exception as e:
        print(f"Error verifying token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}", headers={"WWW-Authenticate": "Bearer"})

async def is_admin(user: Dict[str, Any] = Depends(get_current_user)) -> bool:
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    print(f"user email: {user.get('email')}, admin email: {ADMIN_EMAIL}")
    if user.get("email") == ADMIN_EMAIL:
        return True
    raise HTTPException(status_code=403, detail="User is not authorized to perform this action.")
