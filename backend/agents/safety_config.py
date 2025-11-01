"""
Google AI safety settings configuration following best practices.
This module provides comprehensive safety settings for Gemini API usage.
"""

from typing import List, Dict, Any
import google.generativeai as genai


def get_safety_settings() -> List[Dict[str, Any]]:
    """
    Returns comprehensive safety settings following Google AI best practices.
    
    These settings are configured for enterprise healthcare software development
    where we need to balance safety with functionality for legitimate business use cases.
    
    Returns:
        List of safety setting configurations for Gemini API
    """
    return [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"  # Block medium and high harassment
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH", 
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"  # Block medium and high hate speech
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"  # Block medium and high sexually explicit content
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"  # Block medium and high dangerous content
        }
    ]


def get_strict_safety_settings() -> List[Dict[str, Any]]:
    """
    Returns strict safety settings for highly sensitive operations.
    Use this for user-facing content or when processing external documents.
    
    Returns:
        List of strict safety setting configurations
    """
    return [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_LOW_AND_ABOVE"  # Block low, medium and high harassment
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_LOW_AND_ABOVE"  # Block low, medium and high hate speech
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_LOW_AND_ABOVE"  # Block low, medium and high sexually explicit content
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_LOW_AND_ABOVE"  # Block low, medium and high dangerous content
        }
    ]


def get_permissive_safety_settings() -> List[Dict[str, Any]]:
    """
    Returns permissive safety settings for internal technical content generation.
    Use this only for technical documentation and test case generation where
    legitimate technical terms might be flagged incorrectly.
    
    WARNING: Use with caution and only for internal, non-user-facing content.
    
    Returns:
        List of permissive safety setting configurations
    """
    return [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"  # Block only high harassment
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_ONLY_HIGH"  # Block only high hate speech
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"  # Block only high sexually explicit content
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"  # Still block medium+ dangerous content
        }
    ]


def get_safety_settings_for_context(context: str = "default") -> List[Dict[str, Any]]:
    """
    Returns appropriate safety settings based on the usage context.
    
    Args:
        context: The usage context ("default", "strict", "permissive", "user_facing", "internal")
    
    Returns:
        Appropriate safety settings for the given context
    """
    context_mapping = {
        "default": get_safety_settings,
        "strict": get_strict_safety_settings,
        "permissive": get_permissive_safety_settings,
        "user_facing": get_strict_safety_settings,  # Always use strict for user-facing
        "internal": get_safety_settings,  # Use default for internal operations
        "test_generation": get_permissive_safety_settings,  # Permissive for test generation
        "compliance_detection": get_safety_settings,  # Default for compliance detection
        "document_processing": get_strict_safety_settings,  # Strict for external documents
    }
    
    return context_mapping.get(context, get_safety_settings)()


class SafetySettingsManager:
    """
    Manager class for handling safety settings with logging and monitoring.
    Provides additional safety features like content filtering and audit logging.
    """
    
    def __init__(self, default_context: str = "default"):
        self.default_context = default_context
        self.blocked_content_count = 0
        self.total_requests = 0
    
    def get_settings(self, context: str = None) -> List[Dict[str, Any]]:
        """Get safety settings for a specific context with logging."""
        context = context or self.default_context
        self.total_requests += 1
        return get_safety_settings_for_context(context)
    
    def handle_safety_block(self, response, context: str = "unknown"):
        """
        Handle when content is blocked by safety filters.
        
        Args:
            response: The Gemini API response
            context: The context where the block occurred
        """
        self.blocked_content_count += 1
        
        # Log the safety block for monitoring
        print(f"Safety filter triggered in context: {context}")
        print(f"Total blocks: {self.blocked_content_count}/{self.total_requests}")
        
        # Check if we have safety ratings in the response
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'safety_ratings'):
                for rating in candidate.safety_ratings:
                    if rating.probability in ["MEDIUM", "HIGH"]:
                        print(f"Safety concern: {rating.category} - {rating.probability}")
    
    def get_safety_stats(self) -> Dict[str, Any]:
        """Get safety statistics for monitoring."""
        return {
            "total_requests": self.total_requests,
            "blocked_content_count": self.blocked_content_count,
            "block_rate": self.blocked_content_count / max(self.total_requests, 1)
        }


# Global safety manager instance
safety_manager = SafetySettingsManager()


# Best practices documentation
SAFETY_BEST_PRACTICES = """
Google AI Safety Settings Best Practices:

1. **Context-Appropriate Settings**: Use different safety levels based on content type
   - Strict for user-facing content
   - Default for internal operations  
   - Permissive only for technical content generation

2. **Monitor Safety Blocks**: Track when content is blocked to identify patterns
   - Log blocked content for review
   - Adjust settings if legitimate content is blocked
   - Monitor block rates for anomalies

3. **Content Validation**: Implement additional validation layers
   - Validate JSON outputs for structure
   - Check for appropriate technical terminology
   - Implement custom content filters for domain-specific needs

4. **Audit and Compliance**: Maintain audit logs for safety decisions
   - Log safety setting choices
   - Track blocked content incidents
   - Regular review of safety configurations

5. **Fallback Strategies**: Have fallback plans when content is blocked
   - Retry with different prompts
   - Use alternative generation approaches
   - Provide meaningful error messages to users

6. **Regular Review**: Periodically review and update safety settings
   - Monitor false positive rates
   - Update based on new Google AI guidelines
   - Adjust for changing business requirements
"""
