import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas import NaturalLanguageRequest, NaturalLanguageResponse, FindingResponse
from app.config import settings
from app.rules import registry
import sqlglot

router = APIRouter(prefix="/api/natural-language", tags=["Natural Language"])

NL_PROMPT = """
You are a database engineer. Translate the natural language prompt into a high-performance SQL query.
Focus on Postgres syntax compatibility.
Respond ONLY with a JSON block matching this schema:
{
  "generated_sql": "string (the SQL statement)",
  "assumptions_made": "string (brief list of database assumptions made)"
}

Table Scope context:
The database has these tables available: {table_scope_str}
"""

@router.post("/generate", response_model=NaturalLanguageResponse)
async def generate_sql_from_nl(
    data: NaturalLanguageRequest,
    db: AsyncSession = Depends(get_db)
):
    provider = settings.QUERYSAGE_AI_PROVIDER.lower()
    table_scope_str = ", ".join(data.table_scope) if data.table_scope else "All Tables"
    prompt = f"Natural language instruction: {data.natural_language}\n\nTable Scope: {table_scope_str}"
    
    generated_sql = ""
    assumptions = ""
    
    try:
        if provider == "anthropic":
            if not settings.QUERYSAGE_ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API key is not configured.")
            
            headers = {
                "x-api-key": settings.QUERYSAGE_ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": settings.QUERYSAGE_ANTHROPIC_MODEL,
                "system": NL_PROMPT.format(table_scope_str=table_scope_str),
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.0
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Anthropic API error: {response.text}")
                res = response.json()
                content = res["content"][0]["text"]
        else: # Ollama
            url = f"{settings.QUERYSAGE_OLLAMA_HOST}/api/generate"
            payload = {
                "model": settings.QUERYSAGE_OLLAMA_MODEL,
                "prompt": f"System:\n{NL_PROMPT.format(table_scope_str=table_scope_str)}\n\nUser: {prompt}",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0}
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Ollama local error: {response.text}")
                res = response.json()
                content = res.get("response", "")

        # Parse JSON
        content_clean = content.strip()
        if content_clean.startswith("```json"):
            content_clean = content_clean[7:]
        if content_clean.endswith("```"):
            content_clean = content_clean[:-3]
        content_clean = content_clean.strip()
        
        parsed = json.loads(content_clean)
        generated_sql = parsed.get("generated_sql", "")
        assumptions = parsed.get("assumptions_made", "")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL from AI: {str(e)}")

    # Auto-trigger static rule checks on the output SQL
    static_findings = []
    if generated_sql:
        try:
            parsed_ast = sqlglot.parse_one(generated_sql, read="postgres")
            findings_objs = registry.run_all(parsed_ast)
            static_findings = [FindingResponse.model_validate(f.to_dict()) for f in findings_objs]
        except Exception:
            pass
            
    return NaturalLanguageResponse(
        generated_sql=generated_sql,
        assumptions_made=assumptions,
        findings=static_findings
    )
