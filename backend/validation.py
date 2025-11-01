"""
Input validation middleware and utilities for secure API endpoints.
"""
import re
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, Request
from pydantic import BaseModel, field_validator
import html
import bleach

# Allowed HTML tags for sanitization (very restrictive)
ALLOWED_TAGS = []
ALLOWED_ATTRIBUTES = {}

# Regex patterns for validation
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?()]+$')

class ValidationError(Exception):
    """Custom validation error"""
    pass

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing HTML tags and limiting length.
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    if len(value) > max_length:
        raise ValidationError(f"String too long (max {max_length} characters)")
    
    # Remove HTML tags and decode HTML entities
    sanitized = bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    sanitized = html.unescape(sanitized)
    
    return sanitized.strip()

def validate_email(email: str) -> str:
    """
    Validate email format.
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email is required and must be a string")
    
    email = email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValidationError("Invalid email format")
    
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("Email too long")
    
    return email

def validate_user_id(user_id: str) -> str:
    """
    Validate user ID format (Firebase UID format).
    """
    if not user_id or not isinstance(user_id, str):
        raise ValidationError("User ID is required and must be a string")
    
    user_id = user_id.strip()
    if len(user_id) < 10 or len(user_id) > 128:
        raise ValidationError("Invalid user ID length")
    
    # Firebase UIDs are alphanumeric
    if not re.match(r'^[a-zA-Z0-9]+$', user_id):
        raise ValidationError("Invalid user ID format")
    
    return user_id

def validate_event_type(event_type: str) -> str:
    """
    Validate event type for audit logs.
    """
    if not event_type or not isinstance(event_type, str):
        raise ValidationError("Event type is required and must be a string")
    
    event_type = event_type.strip()
    if not ALPHANUMERIC_PATTERN.match(event_type):
        raise ValidationError("Event type must be alphanumeric with underscores and hyphens only")
    
    if len(event_type) > 50:
        raise ValidationError("Event type too long (max 50 characters)")
    
    return event_type

def validate_json_string(value: str, max_length: int = 10000) -> str:
    """
    Validate and sanitize JSON string content.
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    if len(value) > max_length:
        raise ValidationError(f"JSON string too long (max {max_length} characters)")
    
    # Basic JSON structure validation (not parsing to avoid injection)
    if value.count('{') != value.count('}') or value.count('[') != value.count(']'):
        raise ValidationError("Malformed JSON structure")
    
    return sanitize_string(value, max_length)

def validate_filter_params(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate filter parameters for audit log queries.
    """
    validated = {}
    
    if user_id:
        validated['user_id'] = validate_user_id(user_id)
    
    if event_type:
        validated['event_type'] = validate_event_type(event_type)
    
    if start_date:
        # ISO 8601 date format validation (supports various formats)
        # Matches: YYYY-MM-DDTHH:MM:SS[.fff][Z] or YYYY-MM-DD HH:MM:SS[+/-HH:MM]
        if not re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$', start_date):
            raise ValidationError(f"Invalid start_date format (expected ISO 8601). Received: '{start_date}'")
        validated['start_date'] = start_date
    
    if end_date:
        # ISO 8601 date format validation (supports various formats)
        # Matches: YYYY-MM-DDTHH:MM:SS[.fff][Z] or YYYY-MM-DD HH:MM:SS[+/-HH:MM]
        if not re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$', end_date):
            raise ValidationError(f"Invalid end_date format (expected ISO 8601). Received: '{end_date}'")
        validated['end_date'] = end_date
    
    return validated

def validate_request_size(request: Request, max_size: int = 10 * 1024 * 1024):  # 10MB default
    """
    Validate request content length.
    """
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > max_size:
        raise HTTPException(status_code=413, detail="Request too large")

def validate_ip_address(ip: str) -> str:
    """
    Validate IP address format.
    """
    if not ip or not isinstance(ip, str):
        return "unknown"
    
    # Basic IPv4/IPv6 validation
    ip = ip.strip()
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip) or re.match(r'^([0-9a-fA-F:]+)$', ip):
        return ip
    
    return "unknown"

def validate_user_agent(user_agent: str) -> str:
    """
    Validate and sanitize user agent string.
    """
    if not user_agent or not isinstance(user_agent, str):
        return "unknown"
    
    # Limit length and sanitize
    user_agent = user_agent[:500]  # Reasonable limit
    return sanitize_string(user_agent, 500)

class AdminFilterRequest(BaseModel):
    """
    Validated request model for admin filter parameters.
    """
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id_field(cls, v):
        if v:
            return validate_user_id(v)
        return v
    
    @field_validator('event_type')
    @classmethod
    def validate_event_type_field(cls, v):
        if v:
            return validate_event_type(v)
        return v
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_fields(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$', v):
            raise ValueError("Invalid date format (expected ISO 8601)")
        return v

def validate_admin_request(request: Request):
    """
    Comprehensive validation for admin requests.
    """
    # Validate request size
    validate_request_size(request)
    
    # Validate IP address
    ip = request.client.host if request.client else "unknown"
    validated_ip = validate_ip_address(ip)
    
    # Validate user agent
    user_agent = request.headers.get("user-agent", "unknown")
    validated_user_agent = validate_user_agent(user_agent)
    
    return {
        "ip_address": validated_ip,
        "user_agent": validated_user_agent
    }
