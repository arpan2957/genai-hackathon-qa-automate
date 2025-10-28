import time
from fastapi import APIRouter, Depends, HTTPException
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
from database import db, bq_client
from vertexai.language_models import TextEmbeddingModel
import google.generativeai as genai

from audit import log_audit_event

router = APIRouter()

async def _get_multimodal_embedding(text: Optional[str] = None, image_data: Optional[str] = None) -> List[float]:
    """Generates a multi-modal embedding for the given text and/or image data."""
    try:
        aiplatform.init(project=PROJECT_ID, location="us-central1")
        model = aiplatform.MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        
        image = None
        if image_data:
            # Assuming image_data is base64 encoded string
            image_bytes = base64.b64decode(image_data.split(",", 1)[1])
            image = aiplatform.Image(image_bytes=image_bytes)

        if not text and not image:
            return []

        embeddings = model.get_embeddings(
            contextual_text=text,
            image=image,
        )
        
        # We get both text and image embeddings, for a query we prefer the image one if available
        if image:
            return embeddings.image_embedding
        return embeddings.text_embedding

    except Exception as e:
        print(f"Error generating multi-modal embedding: {e}")
        # Fallback to a zero-vector or handle appropriately
        return [0.0] * 1408 # Dimension for multimodalembedding@001


@router.post("/api/generate", response_model=GenerateResponse, tags=["AI Generation"], summary="Generate Test Cases",
    description="Generates test cases from either a single requirement string or a full document's text.")
async def generate_test_cases(request: RequirementRequest, user: Dict[str, Any] = Depends(get_current_user), agent: GenerationAgent = Depends(get_generation_agent)):
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
                model_name=GENAI_VISION_MODEL, # Use vision model for multi-modal embedding
                text=primary_input_text,
                image_data=primary_input_image_data
            )
            
        if query_embedding_values:
            table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
            # IMPORTANT: For VECTOR_SEARCH to work, you must create BigQuery vector indexes.
            # Example DDL:
            # CREATE VECTOR INDEX my_text_embedding_index ON `{table_id}`(embedding) OPTIONS(distance_type='DOT_PRODUCT', index_type='IVF');
            # CREATE VECTOR INDEX my_image_embedding_index ON `{table_id}`(image_embedding) OPTIONS(distance_type='DOT_PRODUCT', index_type='IVF');

            query = f"""
            WITH text_results AS (
              SELECT id, distance FROM VECTOR_SEARCH(
                TABLE `{table_id}`,
                'embedding',
                (SELECT {query_embedding_values} AS embedding),
                top_k => 3,
                distance_type => 'DOT_PRODUCT'
              )
              WHERE user_id = '{user["uid"]}'
            ),
            image_results AS (
              SELECT id, distance FROM VECTOR_SEARCH(
                TABLE `{table_id}`,
                'image_embedding',
                (SELECT {query_embedding_values} AS embedding),
                top_k => 3,
                distance_type => 'DOT_PRODUCT'
              )
              WHERE user_id = '{user["uid"]}'
            ),
            combined_results AS (
                SELECT id, distance FROM text_results
                UNION ALL
                SELECT id, distance FROM image_results
            ),
            final_ranking AS (
                SELECT id, SUM(distance) as total_distance
                FROM combined_results
                GROUP BY id
                ORDER BY total_distance DESC
                LIMIT 3
            )
            SELECT
                t.id,
                t.filename,
                t.user_id,
                t.text_content,
                t.image_url
            FROM `{table_id}` AS t
            JOIN final_ranking AS fr ON t.id = fr.id
            ORDER BY fr.total_distance DESC
            """
            query_job = bq_client.query(query)
            rows = query_job.result()

            for row in rows:
                if row.text_content:
                    context_text += row.text_content + "\n\n"
                if row.image_url:
                    context_images.append(row.image_url)
            
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

        log_audit_event({
            "timestamp": time.time(),
            "user_id": user['uid'],
            "email": user['email'],
            "event_type": "ai_generation",
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
async def generate_manual_test_case_details(request: ManualTestCaseDetailsRequest, user: Dict[str, Any] = Depends(get_current_user), agent: GenerationAgent = Depends(get_generation_agent)):
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


