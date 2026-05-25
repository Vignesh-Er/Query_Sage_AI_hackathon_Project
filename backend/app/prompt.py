import json
import hashlib
import httpx
from typing import Any, Dict, List, Tuple, Optional
from app.config import settings

SYSTEM_PROMPT = """
You are a database performance engineer analyzing SQL for a developer.
If the query has no performance or correctness issues, state that directly in the 'plain_summary' field.
All advice is advisory and will be reviewed by a human before application.
"""

OLLAMA_SYSTEM_PROMPT = SYSTEM_PROMPT + """
Respond ONLY with a valid JSON object matching the exact schema specified below.
Never include any introductory text, markdown formatting outside the JSON code block, or explanation outside the designated fields.
Never apologize, hedge, or explain your reasoning outside the designated JSON structure.

JSON Response Schema:
{
  "rewritten_query": "string (the complete optimized SQL query)",
  "changes": [
    {
      "type": "index_added" | "join_rewrite" | "predicate_rewrite" | "cte_extraction" | "function_removal",
      "original_fragment": "string",
      "replacement_fragment": "string",
      "reason": "string",
      "orm_equivalent": "string (ORM code or None)"
    }
  ],
  "index_recommendations": [
    {
      "statement": "string (CREATE INDEX CONCURRENTLY ... or CREATE INDEX ...)",
      "justification": "string",
      "estimated_selectivity": 0.05,
      "index_size_bytes": 1024000
    }
  ],
  "estimated_row_reduction_percent": 25.5,
  "confidence": "low" | "medium" | "high",
  "plain_summary": "string (maximum two sentences written for a developer who has never profiled a query)",
  "follow_up_questions": ["string", "string"]
}
"""

def clean_sql_comments_injection(sql: str) -> Tuple[str, List[str]]:
    """
    Checks SQL comments for injection commands like 'ignore', 'forget', 'override', 'disregard'.
    Strips comment text if patterns found, returning clean SQL and logs.
    """
    logs = []
    injection_words = ["ignore", "forget", "override", "disregard", "system prompt", "instruction"]
    
    # We clean simple single-line '--' comments and multi-line '/*' comments
    cleaned_sql = sql
    
    # Basic comment finding
    has_potential_injection = False
    
    # Check if words are inside comment blocks
    import re
    # Match -- comments
    dash_comments = re.findall(r"--.*", sql)
    # Match /* */ comments
    star_comments = re.findall(r"/\*.*?\*/", sql, re.DOTALL)
    
    all_comments = dash_comments + star_comments
    for comment in all_comments:
        if any(word in comment.lower() for word in injection_words):
            has_potential_injection = True
            break
            
    if has_potential_injection:
        # Strip all comments
        cleaned_sql = re.sub(r"--.*", "", sql)
        cleaned_sql = re.sub(r"/\*.*?\*/", "", cleaned_sql, flags=re.DOTALL)
        logs.append("Warning: Instruction override keywords detected inside SQL comments. Comments were stripped prior to AI submission.")
        
    return cleaned_sql, logs

def build_analysis_context(
    query: str,
    findings: List[Dict[str, Any]],
    plan_summary: Optional[Dict[str, Any]],
    workload_context: Optional[Dict[str, Any]],
    schema_excerpt: Optional[Dict[str, Any]],
    orm_framework: Optional[str]
) -> Dict[str, Any]:
    """Serializes the full analysis inputs to a structured dictionary."""
    redacted_schema = None
    if schema_excerpt:
        from app.redactor import redact_schema_excerpt
        redacted_schema, _ = redact_schema_excerpt(schema_excerpt)

    return {
        "input_query": query,
        "findings": findings,
        "execution_plan": plan_summary,
        "workload_context": workload_context,
        "schema_context": redacted_schema,
        "orm_framework": orm_framework
    }

def extract_json_raw_decode(text: str) -> Dict[str, Any]:
    text = text.strip()
    decoder = json.JSONDecoder()
    idx = 0
    while True:
        idx = text.find('{', idx)
        if idx == -1:
            break
        try:
            obj, end = decoder.raw_decode(text[idx:])
            return obj
        except json.JSONDecodeError:
            idx += 1
    raise ValueError("AI_RESPONSE_PARSE_FAILED")

async def call_ai_provider(context: Dict[str, Any]) -> Dict[str, Any]:
    """Coordinates API calls to Anthropic or Ollama based on configuration."""
    provider = settings.QUERYSAGE_AI_PROVIDER.lower()
    prompt_content = json.dumps(context, indent=2)
    
    if provider == "anthropic":
        if not settings.QUERYSAGE_ANTHROPIC_API_KEY:
            raise ValueError("Anthropic API key is not configured.")
        
        # Define the forced tool
        analysis_tool = {
            "name": "submit_query_analysis",
            "description": "Submit database query performance and correctness analysis.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "rewritten_query": {"type": "string"},
                    "changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "original_fragment": {"type": "string"},
                                "replacement_fragment": {"type": "string"},
                                "reason": {"type": "string"},
                                "orm_equivalent": {"type": "string"}
                            },
                            "required": ["type", "original_fragment", "replacement_fragment", "reason"]
                        }
                    },
                    "index_recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "statement": {"type": "string"},
                                "justification": {"type": "string"},
                                "estimated_selectivity": {"type": "number"},
                                "index_size_bytes": {"type": "integer"}
                            },
                            "required": ["statement", "justification"]
                        }
                    },
                    "estimated_row_reduction_percent": {"type": "number"},
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    },
                    "plain_summary": {"type": "string"},
                    "follow_up_questions": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "rewritten_query",
                    "changes",
                    "index_recommendations",
                    "estimated_row_reduction_percent",
                    "confidence",
                    "plain_summary",
                    "follow_up_questions"
                ]
            }
        }

        # Call Anthropic API using tools & tool_choice
        headers = {
            "x-api-key": settings.QUERYSAGE_ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": settings.QUERYSAGE_ANTHROPIC_MODEL,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": prompt_content}
            ],
            "tools": [analysis_tool],
            "tool_choice": {
                "type": "tool",
                "name": "submit_query_analysis"
            },
            "max_tokens": 4096,
            "temperature": 0.0
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.text}")
                
            res_json = response.json()
            for block in res_json.get("content", []):
                if block.get("type") == "tool_use":
                    return block["input"]
            raise ValueError("No tool_use block found in Anthropic response")
            
    elif provider == "ollama":
        # Call Local Ollama instance
        url = f"{settings.QUERYSAGE_OLLAMA_HOST}/api/generate"
        payload = {
            "model": settings.QUERYSAGE_OLLAMA_MODEL,
            "prompt": f"System Instruction:\n{OLLAMA_SYSTEM_PROMPT}\n\nContext Inputs:\n{prompt_content}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise Exception(f"Ollama local error: {response.text}")
                
            res_json = response.json()
            content = res_json.get("response", "")
            
        return extract_json_raw_decode(content)
            
    else:
        raise ValueError(f"Unsupported AI Provider: {provider}")
