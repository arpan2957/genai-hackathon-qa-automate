"""
Refactored GenerationAgent - Clean, modular, and maintainable.
This is the main agent class that orchestrates test case generation using specialized modules.
"""

import json
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from google.adk.agents import Agent

from config import GENAI_MODEL, GENAI_VISION_MODEL
from .prompts import (
    GENERATE_SYSTEM_PROMPT, 
    SEGMENTATION_PROMPT, 
    CLASSIFICATION_PROMPT
)
from .compliance_handler import ComplianceFrameworkHandler
from .safety_config import get_safety_settings_for_context, safety_manager
from .image_utils import ImageLoader


class GenerationAgent(Agent):
    """
    AI-powered test case generation agent.
    
    This agent specializes in generating comprehensive test cases from software requirements,
    with intelligent compliance framework detection and dynamic prompt adaptation.
    """
    
    vision_model: str
    compliance_handler: Optional[ComplianceFrameworkHandler] = None
    image_loader: Optional[ImageLoader] = None
    
    def __init__(self, model_name: str = GENAI_MODEL, vision_model: str = GENAI_VISION_MODEL):
        """
        Initialize the GenerationAgent.
        
        Args:
            model_name: The Gemini model to use for text generation
            vision_model: The Gemini model to use for vision tasks
        """
        super().__init__(
            name="generation_agent",
            model=model_name,
            vision_model=vision_model,
            tools=[
                self.generate_initial_test_cases,
                self.refine_test_cases,
                self.segment_requirements,
                self.classify_requirements,
                self.detect_compliance_frameworks,
            ]
        )
        self.model = model_name
        self.vision_model = vision_model
        self.compliance_handler = ComplianceFrameworkHandler(model_name)
        self.image_loader = ImageLoader()
    
    def segment_requirements(self, document_text: str) -> str:
        """
        Analyzes a large text document and segments it into individual requirements.
        
        Args:
            document_text: The document text to segment
            
        Returns:
            JSON string containing array of individual requirements
        """
        model = genai.GenerativeModel(
            self.model,
            system_instruction=SEGMENTATION_PROMPT
        )
        
        user_prompt = f"""**Document Text to be Segmented:**
{document_text}"""
        
        safety_settings = get_safety_settings_for_context("document_processing")
        
        try:
            response = model.generate_content(user_prompt, safety_settings=safety_settings)
            return response.text
        except Exception as e:
            safety_manager.handle_safety_block(e, "document_segmentation")
            raise
    
    def classify_requirements(self, product_name: str, requirements: List[str]) -> str:
        """
        Classifies requirements into logical domains for testing purposes.
        
        Args:
            product_name: Name of the product/system
            requirements: List of individual requirements
            
        Returns:
            JSON string containing classified requirements by domain
        """
        model = genai.GenerativeModel(
            self.model,
            system_instruction=CLASSIFICATION_PROMPT
        )
        
        requirements_json = json.dumps(requirements, indent=2)
        user_prompt = f'''**Product Name:** "{product_name}"
**Requirements:**
{requirements_json}'''
        
        safety_settings = get_safety_settings_for_context("internal")
        
        try:
            response = model.generate_content(user_prompt, safety_settings=safety_settings)
            return response.text
        except Exception as e:
            safety_manager.handle_safety_block(e, "requirement_classification")
            raise
    
    def generate_initial_test_cases(
        self, 
        requirement: str, 
        images: Optional[List[str]] = None, 
        detected_frameworks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generates comprehensive test cases from a software requirement.
        
        Args:
            requirement: The software requirement to test
            images: Optional list of image URLs for context
            detected_frameworks: Optional list of detected compliance frameworks
            
        Returns:
            JSON string containing generated test cases
        """
        # Use dynamic prompt based on compliance frameworks
        if detected_frameworks:
            system_prompt = self.compliance_handler.create_dynamic_system_prompt(detected_frameworks)
        else:
            system_prompt = GENERATE_SYSTEM_PROMPT
        
        model = genai.GenerativeModel(
            self.vision_model if images else self.model,
            system_instruction=system_prompt
        )
        
        # Prepare content for the model
        contents = [f'''**Requirement to test:**
"{requirement}"''']
        
        # Load and add images if provided
        if images:
            loaded_images = self._load_images_safely(images)
            contents.extend(loaded_images)
        
        safety_settings = get_safety_settings_for_context("test_generation")
        
        try:
            response = model.generate_content(contents, safety_settings=safety_settings)
            return response.text
        except Exception as e:
            safety_manager.handle_safety_block(e, "test_case_generation")
            raise
    
    def refine_test_cases(
        self, 
        requirement: str, 
        test_cases: str, 
        refinement_prompt: str, 
        images: Optional[List[str]] = None
    ) -> str:
        """
        Refines existing test cases based on user feedback.
        
        Args:
            requirement: Original requirement
            test_cases: Existing test cases (JSON string)
            refinement_prompt: User's refinement instructions
            images: Optional list of image URLs for context
            
        Returns:
            JSON string containing refined test cases
        """
        model = genai.GenerativeModel(
            self.vision_model if images else self.model,
            system_instruction=GENERATE_SYSTEM_PROMPT
        )
        
        contents = [f'''**Original Requirement:**
"{requirement}"

**Existing Test Cases:**
```json
{json.dumps(test_cases, indent=2)}
```

**Refinement Prompt:**
"{refinement_prompt}"

Please refine the existing test cases based on the refinement prompt. The output **MUST** be a valid JSON array of objects, following the same schema as before.''']
        
        # Load and add images if provided
        if images:
            loaded_images = self._load_images_safely(images)
            contents.extend(loaded_images)
        
        safety_settings = get_safety_settings_for_context("test_generation")
        
        try:
            response = model.generate_content(contents, safety_settings=safety_settings)
            return response.text
        except Exception as e:
            safety_manager.handle_safety_block(e, "test_case_refinement")
            raise
    
    def detect_compliance_frameworks(self, text: str) -> List[Dict[str, Any]]:
        """
        Detects compliance frameworks mentioned in the given text.
        
        Args:
            text: Text to analyze for compliance frameworks
            
        Returns:
            List of detected compliance frameworks with metadata
        """
        return self.compliance_handler.detect_compliance_frameworks(text)
    
    def _build_compliance_context(self, frameworks: Optional[List[Dict[str, Any]]]) -> str:
        """Build compliance-specific context (delegated to compliance handler)."""
        return self.compliance_handler.build_compliance_context(frameworks)
    
    def _create_dynamic_system_prompt(self, compliance_context: str) -> str:
        """Create dynamic system prompt (delegated to compliance handler)."""
        return self.compliance_handler.create_dynamic_system_prompt(compliance_context)
    
    def _load_images_safely(self, image_urls: List[str]) -> List:
        """
        Safely load images from URLs with error handling.
        
        Args:
            image_urls: List of image URLs to load
            
        Returns:
            List of successfully loaded PIL Image objects
        """
        loaded_images = []
        for url in image_urls:
            try:
                image = self.image_loader.load_image_from_url(url)
                # Prepare image for AI processing
                optimized_image = self.image_loader.prepare_image_for_ai(image)
                loaded_images.append(optimized_image)
            except Exception as e:
                print(f"Error loading image {url}: {e}")
                # Continue without this image rather than failing completely
                continue
        
        return loaded_images
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the agent's performance and safety.
        
        Returns:
            Dictionary containing agent statistics
        """
        return {
            "model": self.model,
            "vision_model": self.vision_model,
            "safety_stats": safety_manager.get_safety_stats(),
            "tools_available": len(self.tools) if hasattr(self, 'tools') else 0
        }


# Backward compatibility - maintain the same interface
def _load_image_from_url(url: str):
    """Backward compatibility function."""
    return ImageLoader.load_image_from_url(url)
