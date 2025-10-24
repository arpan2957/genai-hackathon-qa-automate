from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Dict, Any

from models import RequirementRequest, GenerateResponse, WebhookRegistration
from database import db
import httpx
from agents.generation_agent import GenerationAgent
from utils import get_generation_agent, _clean_json_response
from config import PUBLIC_API_KEY
import json

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == PUBLIC_API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate API key")

@router.post("/public/generate", response_model=GenerateResponse, tags=["Public API"], summary="Generate Test Cases (Public)",
    description="Generates test cases from a requirement string using a public API key.")
async def public_generate_test_cases(request: RequirementRequest, api_key: str = Depends(get_api_key), agent: GenerationAgent = Depends(get_generation_agent)):
    try:
        product_name = request.product_name or "General Product"
        requirements = []

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
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                domain_test_cases.extend([tc for tc in tc_data])
            if domain_test_cases:
                final_domains.append(DomainGroup(domain=domain, test_cases=domain_test_cases))
        
        # Fallback for requirements that might not get classified
        classified_reqs = {req for domain_reqs in classified_data.get("domains", {}).values() for req in domain_reqs}
        unclassified_reqs = [req for req in requirements if req not in classified_reqs]
        
        if unclassified_reqs:
            unclassified_test_cases = []
            for req in unclassified_reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                unclassified_test_cases.extend([tc for tc in tc_data])
            if unclassified_test_cases:
                final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))

        return GenerateResponse(product_name=classified_data.get("product_name", product_name), domains=final_domains)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/public/generate", response_model=GenerateResponse, tags=["Public API"], summary="Generate Test Cases (Public)",
    description="Generates test cases from a requirement string using a public API key.")
async def public_generate_test_cases(request: RequirementRequest, api_key: str = Depends(get_api_key), agent: GenerationAgent = Depends(get_generation_agent)):
    try:
        product_name = request.product_name or "General Product"
        requirements = []

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
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                domain_test_cases.extend([tc for tc in tc_data])
            if domain_test_cases:
                final_domains.append(DomainGroup(domain=domain, test_cases=domain_test_cases))
        
        # Fallback for requirements that might not get classified
        classified_reqs = {req for domain_reqs in classified_data.get("domains", {}).values() for req in domain_reqs}
        unclassified_reqs = [req for req in requirements if req not in classified_reqs]
        
        if unclassified_reqs:
            unclassified_test_cases = []
            for req in unclassified_reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                unclassified_test_cases.extend([tc for tc in tc_data])
            if unclassified_test_cases:
                final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))

        response = GenerateResponse(product_name=classified_data.get("product_name", product_name), domains=final_domains)
        await trigger_webhooks("test_case_generated", response.dict())
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
