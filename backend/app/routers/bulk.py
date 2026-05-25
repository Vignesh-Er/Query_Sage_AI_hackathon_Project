import json
import csv
import math
import io
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from multiprocessing import Pool
import sqlglot
from app.database import get_db
from app.rules import registry
from app.fingerprint import fingerprint
from app.schemas import BulkAnalyzeResponse, BulkPatternRow

router = APIRouter(prefix="/api/bulk", tags=["Bulk Analysis"])

# Picklable top-level function for multiprocessing.Pool
def analyze_single_query_static(query_sql: str) -> Dict[str, Any]:
    try:
        # Standardize formatting
        parsed_ast = sqlglot.parse_one(query_sql, read="postgres")
        findings = registry.run_all(parsed_ast)
        
        # Calculate scores
        severity_sum = sum(f.severity for f in findings)
        findings_count = len(findings)
        
        # Compute fingerprint
        fp = fingerprint(query_sql, "postgres")
        
        return {
            "query": query_sql,
            "findings_count": findings_count,
            "severity_sum": severity_sum,
            "fingerprint": fp,
            "error": None
        }
    except Exception as e:
        return {
            "query": query_sql,
            "findings_count": 0,
            "severity_sum": 0,
            "fingerprint": "error",
            "error": str(e)
        }

def parse_mysql_slow_log(content: str) -> List[Dict[str, Any]]:
    # Simple parse mysql slow logs finding Query_time, etc.
    queries = []
    # Match mysql blocks: # User@Host: ... \n # Query_time: ... \n SQL_STATEMENT;
    # Regex split by statement ends
    raw_statements = content.split(";")
    for stmt in raw_statements:
        cleaned = stmt.strip()
        if not cleaned:
            continue
        # Extract query text and strip slow query log metadata lines
        lines = cleaned.split("\n")
        sql_lines = [l for l in lines if not l.strip().startswith("#") and not l.strip().startswith("use ")]
        sql_text = " ".join(sql_lines).strip()
        if sql_text and len(sql_text) > 15:
            # Parse calls and query execution times from metadata lines
            calls = 1
            exec_time = 1.0
            
            # Search query times
            for line in lines:
                if "query_time:" in line.lower():
                    # extract query_time
                    match = re.search(r"query_time:\s*([0-9.]+)", line, re.IGNORECASE)
                    if match:
                        exec_time = float(match.group(1))
                        
            queries.append({
                "query": sql_text,
                "calls": calls,
                "mean_time_ms": exec_time * 1000.0
            })
    return queries

def parse_stat_statements_csv(content: str) -> List[Dict[str, Any]]:
    queries = []
    f = io.StringIO(content)
    reader = csv.DictReader(f)
    for row in reader:
        # Standard columns: query, calls, total_exec_time, mean_exec_time, rows
        query_sql = row.get("query")
        if query_sql:
            calls = int(row.get("calls", 1))
            mean_time = float(row.get("mean_exec_time", 0.0) or row.get("mean_time", 0.0) or 0.0)
            queries.append({
                "query": query_sql,
                "calls": calls,
                "mean_time_ms": mean_time
            })
    return queries

@router.post("/analyze", response_model=BulkAnalyzeResponse)
async def bulk_analyze_log(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8")
    
    # Step 1: Detect log type and parse SQL strings
    raw_queries = []
    if file.filename.endswith(".csv"):
        try:
            raw_queries = parse_stat_statements_csv(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse pg_stat_statements CSV: {str(e)}")
    elif "query_time" in content.lower():
        raw_queries = parse_mysql_slow_log(content)
    else:
        # Simple fallback: split by semicolon or JSON list
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        raw_queries.append({
                            "query": item.get("query"),
                            "calls": int(item.get("calls", 1)),
                            "mean_time_ms": float(item.get("mean_exec_time", item.get("mean_time_ms", 0.0)))
                        })
                    elif isinstance(item, str):
                        raw_queries.append({"query": item, "calls": 1, "mean_time_ms": 0.0})
        except Exception:
            # Fallback semicolon split
            statements = content.split(";")
            for stmt in statements:
                cleaned = " ".join(stmt.split()).strip()
                if len(cleaned) > 20:
                    raw_queries.append({"query": cleaned, "calls": 1, "mean_time_ms": 0.0})

    if not raw_queries:
        raise HTTPException(status_code=400, detail="No valid queries could be parsed from the uploaded file.")

    # Deduplicate raw queries by query text to avoid redundant analysis
    unique_queries = {}
    for item in raw_queries:
        q = item["query"]
        if q not in unique_queries:
            unique_queries[q] = item
        else:
            # accumulate calls
            unique_queries[q]["calls"] += item["calls"]

    query_items = list(unique_queries.values())
    sql_texts = [item["query"] for item in query_items]

    # Step 2: Parallel execution using multiprocessing.Pool
    # Limit pool size to safe worker count (e.g. 4)
    # Using multiprocessing spawn context to be safe on Windows/Unix
    import multiprocessing
    ctx = multiprocessing.get_context("spawn")
    
    analysis_results = []
    try:
        with ctx.Pool(processes=4) as pool:
            # Run parallel AST rule scans
            analysis_results = pool.map(analyze_single_query_static, sql_texts)
    except Exception as e:
        # Fallback to single thread execution if pool creation crashes (sandbox restrictions, etc.)
        for sql in sql_texts:
            analysis_results.append(analyze_single_query_static(sql))

    # Step 3: Compute Infrastructure Impact Score and Rank
    ranked_patterns = []
    for i, res in enumerate(analysis_results):
        item = query_items[i]
        if res["error"]:
            continue
            
        calls = item["calls"]
        mean_time = item["mean_time_ms"]
        severity_coeff = max(res["severity_sum"], 1.0)
        
        # Infrastructure Impact Score = severity_coeff * log10(calls + 1)
        impact_score = severity_coeff * math.log10(calls + 1)
        
        ranked_patterns.append({
            "query_pattern": res["query"],
            "infrastructure_impact_score": round(impact_score, 2),
            "calls_per_day": float(calls),
            "mean_time_ms": round(mean_time, 2),
            "findings_count": res["findings_count"],
            "fingerprint": res["fingerprint"]
        })

    # Sort descending by Infrastructure Impact Score
    ranked_patterns.sort(key=lambda x: x["infrastructure_impact_score"], reverse=True)
    
    # Assign ranks
    for rank, item in enumerate(ranked_patterns, 1):
        item["rank"] = rank
        
    return BulkAnalyzeResponse(
        analyzed_queries_count=len(ranked_patterns),
        ranked_patterns=[BulkPatternRow(**item) for item in ranked_patterns]
    )
