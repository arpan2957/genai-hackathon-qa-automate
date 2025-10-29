import time
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List, Optional
import json
import base64
import io
from PIL import Image

from models import GenerateResponse, RequirementRequest, DomainGroup, TestCase, ManualTestCaseDetailsRequest, ManualTestCaseDetailsResponse
from security import get_current_user
from agents.generation_agent import GenerationAgent
from utils import get_generation_agent
from utils import _clean_json_response
from config import GENAI_MODEL, PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE, GENAI_VISION_MODEL
from database import db, get_bq_client
from vertexai.language_models import TextEmbeddingModel
from vertexai.vision_models import MultiModalEmbeddingModel, Image as VMImage
import google.generativeai as genai
from google.cloud import aiplatform
import vertexai

from audit import log_audit_event

router = APIRouter()

async def _get_multimodal_embedding(text: Optional[str] = None, image_data: Optional[str] = None) -> List[float]:
    """Generates a multi-modal embedding for the given text and/or image data."""
    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location="us-central1")
        
        # Load the multimodal embedding model
        model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")
        
        image = None
        if image_data:
            # Assuming image_data is base64 encoded string
            if image_data.startswith("data:image/"):
                # Handle data URL format
                image_bytes = base64.b64decode(image_data.split(",", 1)[1])
            else:
                # Handle raw base64
                image_bytes = base64.b64decode(image_data)
            
            # Create a temporary file-like object for the image
            image_io = io.BytesIO(image_bytes)
            # Save temporarily to load with VMImage
            temp_path = f"/tmp/temp_image_{hash(image_data)}.jpg"
            with open(temp_path, "wb") as f:
                f.write(image_bytes)
            image = VMImage.load_from_file(temp_path)
            # Clean up temp file
            os.remove(temp_path)

        if not text and not image:
            return []

        embeddings = model.get_embeddings(
            contextual_text=text,
            image=image,
            dimension=1408
        )
        
        # Return the appropriate embedding based on what was provided
        if image and text:
            # If both are provided, return image embedding (as it's more specific)
            return embeddings.image_embedding
        elif image:
            return embeddings.image_embedding
        else:
            return embeddings.text_embedding

    except Exception as e:
        print(f"Error generating multi-modal embedding: {e}")
        # Fallback to a zero-vector or handle appropriately
        return [0.0] * 1408 # Dimension for multimodalembedding


@router.post("/api/generate", response_model=GenerateResponse, tags=["AI Generation"], summary="Generate Test Cases",
    description="Generates test cases from either a single requirement string or a full document's text.")
async def generate_test_cases(req: Request, request: RequirementRequest, user: Dict[str, Any] = Depends(get_current_user), agent: GenerationAgent = Depends(get_generation_agent), bq_client = Depends(get_bq_client)):
    try:
        product_name = request.product_name or "General Product"
        requirements = []
        context_text = ""
        context_images = [] # List to store retrieved image URLs or data

        # Determine the primary input for query embedding
        primary_input_text = request.refinement_prompt or request.requirement
        primary_input_image_data = request.image_data # This could be the query image itself

        query_embedding_values = []
        if primary_input_text or primary_input_image_data:
            query_embedding_values = await _get_multimodal_embedding(
                text=primary_input_text,
                image_data=primary_input_image_data
            )
            
        # Try to get context from knowledge base if BigQuery is available
        if query_embedding_values and bq_client:
            try:
                table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
                
                # First check if the table exists and has data
                try:
                    table = bq_client.get_table(table_id)
                    if table.num_rows > 0:
                        # Use a simpler query that doesn't require vector indexes for basic functionality
                        query = f"""
                        SELECT
                            id,
                            filename,
                            user_id,
                            text_content,
                            image_url
                        FROM `{table_id}`
                        WHERE user_id = '{user["uid"]}'
                        ORDER BY upload_date DESC
                        LIMIT 3
                        """
                        query_job = bq_client.query(query)
                        rows = query_job.result()

                        for row in rows:
                            if row.text_content:
                                context_text += row.text_content + "\n\n"
                            if row.image_url:
                                context_images.append(row.image_url)
                except Exception as table_error:
                    print(f"Warning: Knowledge base table not found or empty: {table_error}")
                    # Continue without context
                    
            except Exception as e:
                # If BigQuery fails, log the error but continue without context
                print(f"Warning: Failed to retrieve context from knowledge base: {e}")
                # Continue without context - this allows the system to work even without BigQuery
            
        if request.image_data and not primary_input_text:
             # If only image is provided as primary input, also add it to context_images for direct model use
             context_images.append(request.image_data) # Assuming base64 data for immediate use by model

        if request.refinement_prompt and request.test_cases:
            # Refinement phase
            refined_test_cases_json = agent.refine_test_cases(
                existing_test_cases=json.dumps([tc.dict() for tc in request.test_cases]),
                refinement_prompt=request.refinement_prompt,
                context=context_text, # Pass text context
                images=context_images # Pass image context
            )
            refined_test_cases_data = json.loads(_clean_json_response(refined_test_cases_json))
            final_domains = [DomainGroup(domain="Refined Cases", test_cases=[TestCase.model_validate(tc) for tc in refined_test_cases_data])]
            response = GenerateResponse(product_name=product_name, domains=final_domains)

        elif request.document_text:
            segmented_text = agent.segment_requirements(document_text=request.document_text)
            requirements = json.loads(_clean_json_response(segmented_text))
        elif request.requirement:
            requirements = [request.requirement]
        else:
            raise HTTPException(status_code=400, detail="Either 'document_text' or 'requirement' must be provided.")

        if not requirements and not request.refinement_prompt:
            return GenerateResponse(product_name=product_name, domains=[])

        if requirements:
            classified_text = agent.classify_requirements(product_name=product_name, requirements=requirements)
            classified_data = json.loads(_clean_json_response(classified_text))
            
            final_domains = []
            for domain, reqs in classified_data.get("domains", {}).items():
                domain_test_cases = []
                for req in reqs:
                    # Inject context into the prompt
                    all_context = context_text + "\n\n" + (
"\n".join([f"Image: {img_url}" for img_url in context_images]) if context_images else "")

                    requirement_with_context = f"{req}\n\nContext:\n{all_context}"
                    tc_text = agent.generate_initial_test_cases(requirement=requirement_with_context, images=context_images)
                    tc_data = json.loads(_clean_json_response(tc_text))
                    for tc in tc_data:
                        tc['traceability_id'] = f"{request.requirement_id}-{tc['test_case_id']}" if request.requirement_id else tc['test_case_id']
                    domain_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
                if domain_test_cases:
                    final_domains.append(DomainGroup(domain=domain, test_cases=domain_test_cases))
            
            # Fallback for requirements that might not get classified
            classified_reqs = {req for domain_reqs in classified_data.get("domains", {}).values() for req in domain_reqs}
            unclassified_reqs = [req for req in requirements if req not in classified_reqs]
            
            if unclassified_reqs:
                unclassified_test_cases = []
                for req in unclassified_reqs:
                    # Inject context into the prompt
                    all_context = context_text + "\n\n" + (
"\n".join([f"Image: {img_url}" for img_url in context_images]) if context_images else "")
                    requirement_with_context = f"{req}\n\nContext:\n{all_context}"
                    tc_text = agent.generate_initial_test_cases(requirement=requirement_with_context, images=context_images)
                    tc_data = json.loads(_clean_json_response(tc_text))
                    unclassified_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
                if unclassified_test_cases:
                    final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))
            response = GenerateResponse(product_name=classified_data.get("product_name", product_name), domains=final_domains)
        else:
            raise HTTPException(status_code=400, detail="Invalid request: No requirements or refinement prompt provided.")

        log_audit_event(req, user, "ai_generation", details={
            "request_data": request.dict(),
            "response_data": response.dict()
        })
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/generate-manual-test-case-details", response_model=ManualTestCaseDetailsResponse, tags=["AI Generation"], summary="Generate Manual Test Case Details",
    description="Generates AI-driven details (compliance tag, test case ID, traceability ID) for a manually created test case.")
async def generate_manual_test_case_details(req: Request, request: ManualTestCaseDetailsRequest, user: Dict[str, Any] = Depends(get_current_user), agent: GenerationAgent = Depends(get_generation_agent)):
    try:
        # Combine title and steps to form a requirement for the AI agent
        requirement_text = f"Title: {request.title}\nSteps: {request.steps}"

        # Use the AI to generate initial test cases (we only need one for details)
        tc_text = agent.generate_initial_test_cases(requirement=requirement_text)
        tc_data = json.loads(_clean_json_response(tc_text))

        if not tc_data:
            raise HTTPException(status_code=500, detail="AI failed to generate test case details.")

        # Take the first generated test case to extract details
        first_tc = tc_data[0]

        # Classify the domain using the AI agent
        classified_text = agent.classify_requirements(product_name=request.product_name or "General Product", requirements=[requirement_text])
        classified_data = json.loads(_clean_json_response(classified_text))

        # Extract the domain, defaulting to "General" if classification fails or is empty
        classified_domain = "General"
        if classified_data and "domains" in classified_data:
            # Get the first domain that has requirements, or default to "General"
            for domain_name, reqs in classified_data["domains"].items():
                if reqs:
                    classified_domain = domain_name
                    break

        # Generate traceability_id
        traceability_id = f"{request.requirement_id}-{first_tc['test_case_id']}" if request.requirement_id else first_tc['test_case_id']

        return ManualTestCaseDetailsResponse(
            test_case_id=first_tc['test_case_id'],
            compliance_tag=first_tc['compliance_tag'],
            traceability_id=traceability_id,
            domain=classified_domain
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


