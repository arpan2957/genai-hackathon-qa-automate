import json
from typing import List, Optional
import google.generativeai as genai
from google.adk.agents import Agent
from config import GENAI_MODEL, GENAI_VISION_MODEL
import requests
from PIL import Image
import io
import base64

# System prompt for generating test cases from a single requirement
GENERATE_SYSTEM_PROMPT = """
As an expert QA Engineer specializing in regulated healthcare software, your task is to analyze a software requirement and generate a comprehensive set of test cases.

**Context:**
The software is for the healthcare industry, so you must consider factors like data privacy (HIPAA), security, user roles (e.g., doctor, nurse, admin, patient), and data integrity. Be aware of standards like ISO 13485 and ISO 27001 in your thinking.

**Instructions:**
1.  Generate between 8 and 10 test cases for the given requirement.
2.  Include a mix of **Positive** ("happy path") and **Negative** (error conditions, invalid input) test cases.
3.  Include test cases for edge conditions, boundary values, and security aspects like access control.
4.  For each test case, suggest a relevant compliance tag (e.g., "HIPAA-164.312(b)", "ISO-27001-A.9.2.2").
5.  The output **MUST** be a valid JSON array of objects. Do not include any text, comments, or markdown formatting before or after the JSON array. The response must start with `[` and end with `]`

**JSON Schema:**
Each object in the array must follow this exact schema:
{
  "test_case_id": "string (e.g., TC-001)",
  "title": "string",
  "type": "string ('Positive' or 'Negative')",
  "priority": "string ('Critical', 'High', 'Medium', or 'Low')",
  "steps": [
    {
      "step": "integer",
      "action": "string",
      "expected_result": "string"
    }
  ],
  "compliance_tag": "string"
}
"""

# System prompt for segmenting a large document into individual requirements
SEGMENTATION_PROMPT = """
As an expert Business Analyst specializing in software requirements engineering, your task is to analyze a large text document containing software requirements and break it down into a list of distinct, individual requirements.

**Instructions:**
1.  Read the entire document text provided.
2.  Identify each discrete functional or non-functional requirement.
3.  Each requirement should be a self-contained statement.
4.  The output **MUST** be a valid JSON array of strings. Each string in the array is a single, complete requirement.
5.  Do not include any text, comments, or markdown formatting before or after the JSON array. The response must start with `[` and end with `]`

**Example Input Text:**
"The system shall allow users to log in with their username and password. After logging in, users should be able to see their dashboard. The system must also support password reset via email. All passwords must be stored securely."

**Example JSON Output:**
[
  "The system shall allow users to log in with their username and password.",
  "After logging in, users should be able to see their dashboard.",
  "The system must also support password reset via email.",
  "All passwords must be stored securely."
]
"""

# System prompt for classifying requirements into domains
CLASSIFICATION_PROMPT = """
As an expert QA Architect who specializes in categorizing software requirements into logical domains for testing purposes.

**Instructions:**
1.  You will be given a product name and a JSON list of individual software requirements.
2.  Analyze each requirement and classify it into one of the following domains: ["Authentication", "User Management", "File Operations", "Security", "UI/UX", "Performance", "Data Management", "Other"].
3.  Group the requirements by their classified domain.
4.  The output **MUST** be a single valid JSON object. Do not include any text, comments, or markdown formatting before or after the JSON.
5.  The JSON object should have a `product_name` key and a `domains` key.
6.  The `domains` key will contain an object where each key is a domain name, and the value is an array of the requirements that belong to that domain.

**Example Input:**
Product Name: "HealthRecord Pro"
Requirements: 
[
  "The system shall allow users to log in with their username and password.",
  "Users should be able to upload PDF documents.",
  "The user interface must be responsive on mobile devices.",
  "All patient data must be encrypted at rest.",
  "The system must support password reset via email."
]

**Example JSON Output:**
{
  "product_name": "HealthRecord Pro",
  "domains": {
    "Authentication": [
      "The system shall allow users to log in with their username and password.",
      "The system must support password reset via email."
    ],
    "File Operations": [
      "Users should be able to upload PDF documents."
    ],
    "UI/UX": [
      "The user interface must be responsive on mobile devices."
    ],
    "Security": [
      "All patient data must be encrypted at rest."
    ]
  }
}
"""

class GenerationAgent(Agent):
    vision_model: str

    def __init__(self, model_name: str = GENAI_MODEL, vision_model: str = GENAI_VISION_MODEL):
        super().__init__(
            name="generation_agent",
            model=model_name,
            vision_model=vision_model,
            tools=[
                self.generate_initial_test_cases,
                self.refine_test_cases,
                self.segment_requirements,
                self.classify_requirements,
            ]
        )
        self.model = model_name
        self.vision_model = GENAI_VISION_MODEL

    def _load_image_from_url(self, url: str) -> Image.Image:
        if url.startswith("gs://"):
            try:
                # e.g., gs://my-bucket/path/to/image.jpg
                bucket_name = url.split("/")[2]
                blob_name = "/".join(url.split("/")[3:])
                
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                
                image_bytes = blob.download_as_bytes()
                return Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                print(f"Error loading image from GCS URL {url}: {e}")
                # Return a placeholder image or raise an exception
                return Image.new('RGB', (60, 30), color = 'grey')
        elif url.startswith("http://") or url.startswith("https://"):
            response = requests.get(url)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        elif url.startswith("data:image/"):
            # Handle base64 encoded image
            header, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(data))
        else:
            raise ValueError(f"Unsupported image URL format: {url}")

    def segment_requirements(self, document_text: str) -> str:
        """Analyzes a large text document and segments it into a list of individual requirements."""
        model = genai.GenerativeModel(
            self.model,
            system_instruction=SEGMENTATION_PROMPT
        )
        user_prompt = f"""**Document Text to be Segmented:**
{document_text}"""
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(user_prompt, safety_settings=safety_settings)
        return response.text

    def classify_requirements(self, product_name: str, requirements: List[str]) -> str:
        """Classifies a list of requirements into domains and associates them with a product name."""
        model = genai.GenerativeModel(
            self.model,
            system_instruction=CLASSIFICATION_PROMPT
        )
        # Format the requirements list into a JSON string for the prompt
        requirements_json_string = json.dumps(requirements, indent=2)
        user_prompt = f'''**Product Name:** "{product_name}"
**Requirements:**
{requirements_json_string}'''
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(user_prompt, safety_settings=safety_settings)
        return response.text

    def generate_initial_test_cases(self, requirement: str, images: Optional[List[str]] = None) -> str:
        """Generates the initial set of test cases based on a given requirement and optional images."""
        model = genai.GenerativeModel(
            self.vision_model if images else self.model,
            system_instruction=GENERATE_SYSTEM_PROMPT
        )
        
        contents = [f'''**Requirement to test:**
"{requirement}"''']
        if images:
            for img_url in images:
                try:
                    img = self._load_image_from_url(img_url)
                    contents.append(img)
                except Exception as e:
                    print(f"Error loading image {img_url}: {e}")

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(contents, safety_settings=safety_settings)
        return response.text

    def refine_test_cases(self, requirement: str, test_cases: str, refinement_prompt: str, images: Optional[List[str]] = None) -> str:
        """Refines the existing test cases based on a user's refinement prompt and optional images."""
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
        if images:
            for img_url in images:
                try:
                    img = self._load_image_from_url(img_url)
                    contents.append(img)
                except Exception as e:
                    print(f"Error loading image {img_url}: {e}")

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(contents, safety_settings=safety_settings)
        return response.text