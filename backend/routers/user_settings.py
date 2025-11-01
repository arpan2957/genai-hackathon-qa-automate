from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
import json
from security import get_current_user
from audit import log_audit_event

router = APIRouter()

# In-memory storage for demo purposes (in production, use a database)
user_settings_store = {}

@router.get("/api/user/settings", tags=["User Settings"], summary="Get User Settings")
async def get_user_settings(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get user settings and preferences.
    """
    try:
        user_id = user.get("uid")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        # Get settings from store or return defaults
        settings = user_settings_store.get(user_id, {
            "preferences": {
                "emailNotifications": True,
                "pushNotifications": False,
                "weeklyReports": True,
                "testCaseUpdates": True
            },
            "integrations": {
                "jira": {"enabled": False, "url": "", "username": "", "token": ""},
                "azure": {"enabled": False, "url": "", "token": ""},
                "slack": {"enabled": False, "webhook": ""}
            },
            "system": {
                "aiModel": "gpt-4",
                "maxTestCases": 50,
                "autoSave": True,
                "dataRetention": 90
            }
        })
        
        log_audit_event(request, user, "get_user_settings", details={})
        return settings
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")

@router.put("/api/user/settings", tags=["User Settings"], summary="Update User Settings")
async def update_user_settings(
    request: Request,
    settings_update: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user settings and preferences.
    """
    try:
        user_id = user.get("uid")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        # Get existing settings or create new
        current_settings = user_settings_store.get(user_id, {
            "preferences": {},
            "integrations": {},
            "system": {}
        })
        
        # Update only the provided sections
        for section, data in settings_update.items():
            if section in ["preferences", "integrations", "system", "profile"]:
                if section == "profile":
                    # Handle profile updates (display name, etc.)
                    current_settings[section] = {**current_settings.get(section, {}), **data}
                else:
                    current_settings[section] = {**current_settings.get(section, {}), **data}
        
        # Store updated settings
        user_settings_store[user_id] = current_settings
        
        log_audit_event(request, user, "update_user_settings", details={
            "sections_updated": list(settings_update.keys())
        })
        
        return {"message": "Settings updated successfully", "settings": current_settings}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.post("/api/integrations/{integration_type}/test", tags=["User Settings"], summary="Test Integration")
async def test_integration(
    request: Request,
    integration_type: str,
    integration_config: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Test an integration connection (JIRA, Azure DevOps, etc.).
    """
    try:
        # Mock integration testing - in production, implement actual API calls
        if integration_type == "jira":
            if not integration_config.get("url") or not integration_config.get("username") or not integration_config.get("token"):
                raise HTTPException(status_code=400, detail="Missing JIRA configuration")
            # Mock successful connection
            result = {"status": "success", "message": "JIRA connection successful"}
            
        elif integration_type == "azure":
            if not integration_config.get("url") or not integration_config.get("token"):
                raise HTTPException(status_code=400, detail="Missing Azure DevOps configuration")
            # Mock successful connection
            result = {"status": "success", "message": "Azure DevOps connection successful"}
            
        elif integration_type == "slack":
            if not integration_config.get("webhook"):
                raise HTTPException(status_code=400, detail="Missing Slack webhook URL")
            # Mock successful connection
            result = {"status": "success", "message": "Slack connection successful"}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")
        
        log_audit_event(request, user, "test_integration", details={
            "integration_type": integration_type,
            "status": result["status"]
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log_audit_event(request, user, "test_integration", details={
            "integration_type": integration_type,
            "status": "failed",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Integration test failed: {str(e)}")

@router.get("/api/user/profile", tags=["User Settings"], summary="Get User Profile")
async def get_user_profile(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get user profile information.
    """
    try:
        profile = {
            "uid": user.get("uid"),
            "email": user.get("email"),
            "display_name": user.get("name") or user.get("display_name"),
            "email_verified": user.get("email_verified", False),
            "created_at": user.get("auth_time"),
            "last_sign_in": user.get("auth_time")
        }
        
        log_audit_event(request, user, "get_user_profile", details={})
        return profile
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve profile: {str(e)}")
