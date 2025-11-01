"""
Compliance framework detection and context building for test case generation.
This module handles the detection of compliance frameworks and builds appropriate context.
"""

import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from .prompts import COMPLIANCE_DETECTION_PROMPT, create_dynamic_system_prompt
from .safety_config import get_safety_settings


class ComplianceFrameworkHandler:
    """Handles compliance framework detection and context building."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def detect_compliance_frameworks(self, text: str) -> List[Dict[str, Any]]:
        """Detects compliance frameworks mentioned in the given text."""
        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=COMPLIANCE_DETECTION_PROMPT
        )
        
        user_prompt = f"""**Text to Analyze:**
{text}"""
        
        response = model.generate_content(user_prompt, safety_settings=get_safety_settings())
        
        try:
            frameworks = json.loads(response.text.strip())
            return frameworks if isinstance(frameworks, list) else []
        except json.JSONDecodeError:
            # Fallback: return empty list if parsing fails
            print(f"Warning: Failed to parse compliance frameworks from response: {response.text}")
            return []
    
    def build_compliance_context(self, frameworks: Optional[List[Dict[str, Any]]]) -> str:
        """Builds compliance-specific context for the AI prompt."""
        if not frameworks:
            return self._get_default_healthcare_context()
        
        context_parts = []
        for framework in frameworks:
            framework_name = framework.get("framework", "")
            sections = framework.get("sections", [])
            
            context_part = self._get_framework_specific_context(framework_name)
            
            if sections:
                context_part += f" Pay special attention to sections: {', '.join(sections)}."
            
            context_parts.append(context_part)
        
        return " ".join(context_parts)
    
    def create_dynamic_system_prompt(self, frameworks: Optional[List[Dict[str, Any]]]) -> str:
        """Creates a dynamic system prompt based on detected compliance frameworks."""
        compliance_context = self.build_compliance_context(frameworks)
        return create_dynamic_system_prompt(compliance_context)
    
    def _get_default_healthcare_context(self) -> str:
        """Returns default healthcare industry context when no specific frameworks are detected."""
        return ("The software is for the healthcare industry, so you must consider factors like "
                "data privacy (HIPAA), security, user roles (e.g., doctor, nurse, admin, patient), "
                "and data integrity. Be aware of standards like ISO 13485 and ISO 27001 in your thinking.")
    
    def _get_framework_specific_context(self, framework_name: str) -> str:
        """Returns framework-specific context based on the framework name."""
        framework_contexts = {
            "FDA": "This software must comply with {framework}. Focus on electronic records, electronic signatures, audit trails, and validation requirements.",
            "21 CFR": "This software must comply with {framework}. Focus on electronic records, electronic signatures, audit trails, and validation requirements.",
            "ISO 13485": "This software must comply with {framework}. Focus on quality management systems for medical devices, risk management, and design controls.",
            "ISO 27001": "This software must comply with {framework}. Focus on information security management, access controls, and security monitoring.",
            "HIPAA": "This software must comply with {framework}. Focus on protected health information (PHI) security, access controls, and audit logging.",
            "GDPR": "This software must comply with {framework}. Focus on data protection, consent management, data subject rights, and privacy by design.",
            "IEC 62304": "This software must comply with {framework}. Focus on medical device software lifecycle processes, risk classification, and software safety classification.",
            "SOX": "This software must comply with {framework}. Focus on financial reporting controls, audit trails, and data integrity.",
            "Sarbanes": "This software must comply with {framework}. Focus on financial reporting controls, audit trails, and data integrity.",
            "PCI": "This software must comply with {framework}. Focus on payment card data protection, secure transmission, and access controls.",
        }
        
        # Find matching framework context
        for key, context_template in framework_contexts.items():
            if key in framework_name:
                return context_template.format(framework=framework_name)
        
        # Generic compliance framework handling
        return f"This software must comply with {framework_name}. Ensure test cases address the specific requirements and controls defined by this standard."


# Convenience functions for backward compatibility
def detect_compliance_frameworks(model_name: str, text: str) -> List[Dict[str, Any]]:
    """Convenience function for detecting compliance frameworks."""
    handler = ComplianceFrameworkHandler(model_name)
    return handler.detect_compliance_frameworks(text)


def build_compliance_context(frameworks: Optional[List[Dict[str, Any]]]) -> str:
    """Convenience function for building compliance context."""
    handler = ComplianceFrameworkHandler("")  # Model name not needed for this function
    return handler.build_compliance_context(frameworks)


def create_dynamic_system_prompt_with_frameworks(frameworks: Optional[List[Dict[str, Any]]]) -> str:
    """Convenience function for creating dynamic system prompt."""
    handler = ComplianceFrameworkHandler("")  # Model name not needed for this function
    return handler.create_dynamic_system_prompt(frameworks)
