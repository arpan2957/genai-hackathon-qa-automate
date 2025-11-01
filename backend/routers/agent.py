from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from agents.generation_agent import GenerationAgent
from utils import get_generation_agent, _clean_json_response
from models import GenerateResponse, RequirementRequest, DomainGroup, TestCase
import json
from security import get_current_user, verify_agent_api_key
from database import db
import google.generativeai as genai
import os
from config import api_key

# 1. Define Tool Functions with JSON-compatible signatures
async def generate_test_cases_tool(requirement: str, product_name: Optional[str] = "General Product") -> GenerateResponse:
    """
    Generates test cases from a single requirement string.
    """
    try:
        # Instantiate the agent inside the function
        agent = GenerationAgent()
        requirements = [requirement]
        
        # Detect compliance frameworks from the requirement
        detected_frameworks = agent.detect_compliance_frameworks(requirement)
        
        classified_text = agent.classify_requirements(product_name=product_name, requirements=requirements)
        classified_data = json.loads(_clean_json_response(classified_text))

        final_domains = []
        for domain, reqs in classified_data.get("domains", {}).items():
            domain_test_cases = []
            for req in reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req, detected_frameworks=detected_frameworks)
                tc_data = json.loads(_clean_json_response(tc_text))
                domain_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
            if domain_test_cases:
                final_domains.append(DomainGroup(domain=domain, test_cases=domain_test_cases))

        classified_reqs = {req for domain_reqs in classified_data.get("domains", {}).values() for req in domain_reqs}
        unclassified_reqs = [req for req in requirements if req not in classified_reqs]

        if unclassified_reqs:
            unclassified_test_cases = []
            for req in unclassified_reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req, detected_frameworks=detected_frameworks)
                tc_data = json.loads(_clean_json_response(tc_text))
                unclassified_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
            if unclassified_test_cases:
                final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))

        return GenerateResponse(product_name=classified_data.get("product_name", product_name), domains=final_domains)

    except Exception as e:
        raise e

async def search_test_cases_tool(user_id: str, query: str) -> List[TestCase]:
    """
    Searches for test cases in Firestore for a given user based on a query string.
    """
    try:
        test_cases_ref = db.collection(f"users/{user_id}/finalized_test_cases")
        matching_test_cases = []
        docs = test_cases_ref.limit(100).stream()
        search_query_lower = query.lower()

        for doc in docs:
            test_case_data = doc.to_dict()
            if test_case_data:
                if (search_query_lower in test_case_data.get("title", "").lower() or
                    search_query_lower in test_case_data.get("description", "").lower() or
                    search_query_lower in test_case_data.get("compliance_tag", "").lower() or
                    search_query_lower in test_case_data.get("test_case_id", "").lower()):
                    matching_test_cases.append(TestCase.model_validate(test_case_data))

        return matching_test_cases

    except Exception as e:
        raise e

# 2. Configure the generative AI model and register the tools
genai.configure(api_key=api_key)
internal_agent_model = genai.GenerativeModel(
    'gemini-2.5-flash',
    tools=[generate_test_cases_tool, search_test_cases_tool]
)

# 3. Define Router and Endpoints
router = APIRouter()

class AgentQueryRequest(BaseModel):
    query: str
    session_id: str = None

class AgentQueryResponse(BaseModel):
    response: str

@router.post(
    "/api/agent/query",
    tags=["Conversational Agent"],
    response_model=AgentQueryResponse,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AgentQueryResponse"}
                }
            },
        }
    },
)
async def agent_query(
    request_data: AgentQueryRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    agent_api_key_verified: bool = Depends(verify_agent_api_key)
):
    """
    Endpoint for Google Agent Builder to send natural language queries.
    This acts as the central point for the internal tool-calling agent.
    """
    try:
        chat_session = internal_agent_model.start_chat()
        response = chat_session.send_message(request_data.query)

        if response.candidates and response.candidates[0].content.parts and response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            function_name = function_call.name
            function_args = {key: value for key, value in function_call.args.items()}

            if function_name == "generate_test_cases_tool":
                tool_result = await generate_test_cases_tool(**function_args)
                result_dict = tool_result.model_dump()
            elif function_name == "search_test_cases_tool":
                function_args['user_id'] = user['uid']
                tool_result = await search_test_cases_tool(**function_args)
                result_dict = [tc.model_dump() for tc in tool_result]
            else:
                raise HTTPException(status_code=400, detail=f"Unknown tool: {function_name}")

            final_response = chat_session.send_message(
                [genai.types.FunctionResponse(name=function_name, response=result_dict)]
            )
            return AgentQueryResponse(response=final_response.text)
        else:
            return AgentQueryResponse(response=response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")
