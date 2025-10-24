import time
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import json
import base64
import io
from PIL import Image

from models import *
from security import get_current_user
from agents.generation_agent import GenerationAgent
from utils import get_generation_agent
from utils import _clean_json_response
from config import GENAI_MODEL, PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE
from database import db, bq_client
from vertexai.language_models import TextEmbeddingModel
import google.generativeai as genai

from audit import log_audit_event

router = APIRouter()

@router.post("/api/generate", response_model=GenerateResponse, tags=["AI Generation"], summary="Generate Test Cases",
    description="Generates test cases from either a single requirement string or a full document's text.")
async def generate_test_cases(request: RequirementRequest, user: Dict[str, Any] = Depends(get_current_user), agent: GenerationAgent = Depends(get_generation_agent)):
    try:
        if request.image_data:
            # Multimodal request
            model = genai.GenerativeModel(GENAI_MODEL)
            image_data = request.image_data.split(",", 1)[1]
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            response = model.generate_content([
                request.requirement,
                image
            ])
            
            tc_data = json.loads(_clean_json_response(response.text))
            final_domains = [DomainGroup(domain="General", test_cases=[TestCase.model_validate(tc) for tc in tc_data])]
            return GenerateResponse(product_name=request.product_name or "General Product", domains=final_domains)

        product_name = request.product_name or "General Product"
        requirements = []
        context = ""

        if request.requirement:
            # Generate embedding for the requirement
            model = TextEmbeddingModel.from_pretrained("text-embedding-005")
            requirement_embedding = model.get_embeddings([request.requirement])[0].values

            # Query BigQuery to find similar documents
            table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
            query = f"""
                SELECT id, filename, upload_date, user_id, embedding
                FROM `{table_id}`
                WHERE user_id = '{user["uid"]}'
                ORDER BY
                (SELECT SUM(v1 * v2)
                FROM UNNEST(embedding) AS v1 WITH OFFSET i
                JOIN UNNEST({requirement_embedding}) AS v2 WITH OFFSET j
                ON i = j) DESC
                LIMIT 3
            """
            query_job = bq_client.query(query)
            rows = query_job.result()

            # Get the text of the most similar documents from Firestore
            for row in rows:
                doc_ref = db.collection('users').document(user['uid']).collection('knowledge_base').document(row.id).get()
                if doc_ref.exists:
                    context += doc_ref.to_dict().get("text", "")

        if request.document_text:
            segmented_text = agent.segment_requirements(document_text=request.document_text)
            requirements = json.loads(_clean_json_response(segmented_text))
        elif request.requirement:
            requirements = [request.requirement]
        else:
            raise HTTPException(status_code=400, detail="Either 'document_text' or 'requirement' must be provided.")

        if not requirements:
            return GenerateResponse(product_name=product_name, domains=[])

        classified_text = agent.classify_requirements(product_name=product_name, requirements=requirements)
        classified_data = json.loads(_clean_json_response(classified_text))
        
        final_domains = []
        for domain, reqs in classified_data.get("domains", {}).items():
            domain_test_cases = []
            for req in reqs:
                # Inject context into the prompt
                requirement_with_context = f"{req}\n\nContext:\n{context}"
                tc_text = agent.generate_initial_test_cases(requirement=requirement_with_context)
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
                requirement_with_context = f"{req}\n\nContext:\n{context}"
                tc_text = agent.generate_initial_test_cases(requirement=requirement_with_context)
                tc_data = json.loads(_clean_json_response(tc_text))
                unclassified_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
            if unclassified_test_cases:
                final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))

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
