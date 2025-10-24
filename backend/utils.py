from agents.generation_agent import GenerationAgent
from config import GENAI_MODEL

def _clean_json_response(response_text: str) -> str:
    if '```json' in response_text:
        response_text = response_text.split('```json', 1)[1].rsplit('```', 1)[0]
    return response_text.strip()

def get_generation_agent():
    return GenerationAgent(model_name=GENAI_MODEL)