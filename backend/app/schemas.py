from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# Connection Schemas
class ConnectionCreate(BaseModel):
    name: str
    engine: str  # 'postgresql', 'mysql', 'sqlite'
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class ConnectionResponse(BaseModel):
    id: int
    name: str
    engine: str
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    username: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ConnectionTestResponse(BaseModel):
    connected: bool
    error: Optional[str] = None

# Settings Schemas
class SettingsResponse(BaseModel):
    key: str
    value: str
    updated_at: datetime

    class Config:
        from_attributes = True

class SettingsPatch(BaseModel):
    value: str

# Analysis Schemas
class AnalyzeRequest(BaseModel):
    query: str
    connection_id: Optional[int] = None
    include_execution_plan: bool = True
    verify_equivalence: bool = False
    orm_framework: Optional[str] = None  # 'django', 'sqlalchemy', 'prisma', etc.

class FindingResponse(BaseModel):
    rule_id: str
    severity: int
    category: str
    title: str
    description: str
    location_start: Optional[int] = None
    location_end: Optional[int] = None
    auto_fixable: bool = False

    class Config:
        from_attributes = True

class PlanSummaryResponse(BaseModel):
    total_cost: float
    rows_estimated: float
    rows_actual: float
    execution_time_ms: float
    cache_hit_ratio: float
    has_seq_scan: bool
    has_sort_spill: bool
    plan_json: Any
    warnings: List[str] = []

    class Config:
        from_attributes = True

class RegressionEventResponse(BaseModel):
    query_id: int
    previous_plan_id: int
    current_plan_id: int
    cost_delta_percent: float
    regression_type: str
    detected_at: datetime

    class Config:
        from_attributes = True

class WorkloadContextResponse(BaseModel):
    query: str
    calls: int
    total_exec_time: float
    mean_exec_time: float
    rows: int
    calls_per_day: float
    infrastructure_impact_score: float

class RewriteChange(BaseModel):
    type: str  # 'index_added', 'join_rewrite', 'predicate_rewrite', etc.
    original_fragment: str
    replacement_fragment: str
    reason: str
    orm_equivalent: Optional[str] = None

class IndexRecommendation(BaseModel):
    statement: str
    justification: str
    estimated_selectivity: float
    index_size_bytes: int

class RewriteProposalResponse(BaseModel):
    rewritten_query: str
    changes: List[RewriteChange]
    index_recommendations: List[IndexRecommendation]
    estimated_row_reduction_percent: float
    confidence: str  # 'low', 'medium', 'high'
    plain_summary: str
    follow_up_questions: List[str]

class EquivalenceResultResponse(BaseModel):
    row_count_match: bool
    original_row_count: int
    optimized_row_count: int
    original_hash: str
    optimized_hash: str
    result_match: bool
    status: str  # 'VERIFIED', 'ALTERED', 'ORDER_DIFFERS'
    sample_rows_diff: Optional[Any] = None

# Score Schemas
class ScoreResponse(BaseModel):
    query_score: float
    rolling_average: float
    performance_subscore: float
    correctness_subscore: float
    style_subscore: float
    streak_count: int
    cognitive_complexity: Optional[dict] = None

class ScoreTrendResponse(BaseModel):
    date: str
    score: float

class ScorecardResponse(BaseModel):
    rolling_average: float
    streak: int
    per_category_breakdown: Dict[str, float]
    pattern_to_break: Optional[str] = None
    trend_data: List[ScoreTrendResponse]

# Bulk Analysis Schemas
class BulkAnalyzeRequest(BaseModel):
    log_content: str
    connection_id: Optional[int] = None

class BulkPatternRow(BaseModel):
    rank: int
    query_pattern: str
    infrastructure_impact_score: float
    calls_per_day: float
    mean_time_ms: float
    findings_count: int
    fingerprint: str

class BulkAnalyzeResponse(BaseModel):
    analyzed_queries_count: int
    ranked_patterns: List[BulkPatternRow]

# Schema evolution
class SchemaImpactRequest(BaseModel):
    alter_statement: Optional[str] = None
    migrations_dir: Optional[str] = None
    connection_id: int

class SchemaImpactRow(BaseModel):
    query_id: int
    fingerprint: str
    raw_sql: str
    impact_reason: str

class SchemaImpactResponse(BaseModel):
    broken: List[SchemaImpactRow]
    potentially_affected: List[SchemaImpactRow]
    unaffected: List[SchemaImpactRow]

# Natural Language
class NaturalLanguageRequest(BaseModel):
    natural_language: str
    table_scope: List[str] = []
    connection_id: Optional[int] = None

class NaturalLanguageResponse(BaseModel):
    generated_sql: str
    assumptions_made: str
    findings: List[FindingResponse]

# Audit Log
class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    query_id: Optional[int]
    ai_model: Optional[str]
    prompt_hash: Optional[str]
    schema_subset_hash: Optional[str]
    output_hash: Optional[str]
    confidence: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# What-If Simulation Schemas
class WhatIfRequest(BaseModel):
    query: str
    index_statement: str
    connection_id: int

class WhatIfResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    index_name: Optional[str] = None
    table_name: Optional[str] = None
    columns: Optional[str] = None
    hinted_query: Optional[str] = None
    original_cost: Optional[float] = None
    original_rows: Optional[float] = None
    hinted_cost: Optional[float] = None
    hinted_rows: Optional[float] = None
    cost_reduction_percent: Optional[float] = None
    original_plan_json: Optional[Any] = None
    hinted_plan_json: Optional[Any] = None

class LintRequest(BaseModel):
    query: str
    connection_id: Optional[int] = None

