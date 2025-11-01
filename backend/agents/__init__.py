"""
AI Agents Module for Test Case Generation

This module provides AI-powered agents for generating comprehensive test cases
from software requirements with intelligent compliance framework detection.

Main Components:
- GenerationAgent: Main agent for test case generation
- ComplianceFrameworkHandler: Handles compliance framework detection and context
- ImageLoader: Utilities for loading images from various sources
- Safety configuration: Google AI safety settings following best practices

Usage:
    from agents.generation_agent import GenerationAgent
    from agents.compliance_handler import ComplianceFrameworkHandler
    from agents.safety_config import get_safety_settings_for_context
"""

from .generation_agent import GenerationAgent
from .compliance_handler import (
    ComplianceFrameworkHandler,
    detect_compliance_frameworks,
    build_compliance_context,
    create_dynamic_system_prompt_with_frameworks
)
from .image_utils import ImageLoader, load_image_from_url, load_images_from_urls
from .safety_config import (
    get_safety_settings,
    get_strict_safety_settings,
    get_permissive_safety_settings,
    get_safety_settings_for_context,
    SafetySettingsManager,
    safety_manager
)

__all__ = [
    'GenerationAgent',
    'ComplianceFrameworkHandler',
    'ImageLoader',
    'SafetySettingsManager',
    'detect_compliance_frameworks',
    'build_compliance_context',
    'create_dynamic_system_prompt_with_frameworks',
    'load_image_from_url',
    'load_images_from_urls',
    'get_safety_settings',
    'get_strict_safety_settings',
    'get_permissive_safety_settings',
    'get_safety_settings_for_context',
    'safety_manager'
]

__version__ = "2.0.0"
__author__ = "AI Test Case Generation Team"
