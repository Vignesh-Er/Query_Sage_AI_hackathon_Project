from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Score, Query, Finding

def calculate_query_score(findings: List[Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
    """
    Computes score for a single query. Starting score is 100.
    Subtracts (severity * severity / 10) per finding.
    Returns the total query score and category subscores.
    """
    score_val = 100.0
    category_penalties = {
        "PERFORMANCE": 0.0,
        "CORRECTNESS": 0.0,
        "STYLE": 0.0,
        "INDEX": 0.0,
        "LOCKING": 0.0
    }

    for finding in findings:
        severity = finding.get("severity", 1)
        category = finding.get("category", "PERFORMANCE")
        
        penalty = (severity * severity) / 10.0
        score_val -= penalty
        
        if category in category_penalties:
            category_penalties[category] += penalty
            
    score_val = max(0.0, score_val)
    
    # Calculate subscores per category (100 - category penalty)
    subscores = {}
    for cat, penalty in category_penalties.items():
        subscores[cat] = max(0.0, 100.0 - penalty)
        
    return score_val, subscores

async def get_or_create_next_score(
    db: AsyncSession,
    query_id: int,
    findings: List[Dict[str, Any]]
) -> Score:
    """
    Calculates query score, updates streaks, computes rolling averages (last 20),
    and saves a new Score entry to the database.
    """
    query_score, subscores = calculate_query_score(findings)
    
    # Fetch last 19 scores to compute rolling average (including current makes 20)
    result = await db.execute(select(Score).order_by(Score.submitted_at.desc()).limit(19))
    past_scores = result.scalars().all()
    past_scores.reverse()  # chronological order
    
    # Prepend past query scores
    scores_list = [s.query_score for s in past_scores] + [query_score]
    
    # Calculate weighted rolling average
    # Most recent (current) has weight 2.0. Previous decreases by 0.1 down to 0.1 (or less if fewer than 20)
    weights = [2.0 - (i * 0.1) for i in range(len(scores_list))]
    weights.reverse()  # aligning weight 2.0 to the most recent (last element)
    
    weighted_sum = sum(s * w for s, w in zip(scores_list, weights))
    weight_pool = sum(weights)
    
    rolling_avg = weighted_sum / weight_pool if weight_pool > 0 else 60.0
    
    # Check streak
    # Streak increments for consecutive queries with no severity 8+ findings
    has_critical_finding = any(f.get("severity", 0) >= 8 for f in findings)
    
    last_score = past_scores[-1] if past_scores else None
    if has_critical_finding:
        streak_count = 0
    else:
        streak_count = (last_score.streak_count + 1) if last_score else 1

    # Extract averages for categories
    perf_list = [s.performance_subscore for s in past_scores] + [subscores["PERFORMANCE"]]
    perf_avg = sum(s * w for s, w in zip(perf_list, weights)) / weight_pool if weight_pool > 0 else 100.0
    
    corr_list = [s.correctness_subscore for s in past_scores] + [subscores["CORRECTNESS"]]
    corr_avg = sum(s * w for s, w in zip(corr_list, weights)) / weight_pool if weight_pool > 0 else 100.0
    
    style_list = [s.style_subscore for s in past_scores] + [subscores["STYLE"]]
    style_avg = sum(s * w for s, w in zip(style_list, weights)) / weight_pool if weight_pool > 0 else 100.0

    score_entry = Score(
        query_id=query_id,
        query_score=round(query_score, 2),
        rolling_average=round(rolling_avg, 2),
        performance_subscore=round(perf_avg, 2),
        correctness_subscore=round(corr_avg, 2),
        style_subscore=round(style_avg, 2),
        streak_count=streak_count,
        submitted_at=datetime.utcnow()
    )
    db.add(score_entry)
    await db.commit()
    await db.refresh(score_entry)
    return score_entry

async def get_pattern_to_break(db: AsyncSession) -> Optional[str]:
    """
    Identifies the rule_id that appears in > 30% of the last 20 queries.
    Returns the rule_id or the most frequent rule.
    """
    result = await db.execute(
        select(Query).options(selectinload(Query.findings)).order_by(Query.submitted_at.desc()).limit(20)
    )
    last_queries = result.scalars().all()
    if not last_queries:
        return None
        
    rule_counts = {}
    total_queries = len(last_queries)
    
    for q in last_queries:
        seen_rules = {f.rule_id for f in q.findings}
        for r_id in seen_rules:
            rule_counts[r_id] = rule_counts.get(r_id, 0) + 1
            
    if not rule_counts:
        return None
        
    # Find most frequent rule
    sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)
    top_rule, count = sorted_rules[0]
    
    # Check if > 30% of queries
    if count / total_queries >= 0.3:
        return top_rule
        
    return top_rule

import sqlglot
import sqlglot.expressions as exp

def calculate_cognitive_complexity(sql: str) -> dict:
    """
    Parses SQL and returns structural cognitive complexity metrics:
    - join_count (Join nodes)
    - subquery_depth (Recursive max Subquery depth)
    - case_count (Case nodes)
    - window_function_count (Window nodes)
    - cognitive_complexity_score (Absolute weighted score)
    """
    try:
        parsed = sqlglot.parse_one(sql, error_level=sqlglot.ErrorLevel.RAISE)
    except Exception:
        return {
            "join_count": 0,
            "subquery_depth": 0,
            "case_count": 0,
            "window_function_count": 0,
            "cognitive_complexity_score": 0
        }

    join_count = sum(1 for node in parsed.walk() if isinstance(node, exp.Join))
    case_count = sum(1 for node in parsed.walk() if isinstance(node, exp.Case))
    window_function_count = sum(1 for node in parsed.walk() if isinstance(node, exp.Window))

    def get_subquery_depth(node, depth: int) -> int:
        if isinstance(node, exp.Subquery):
            new_depth = depth + 1
        else:
            new_depth = depth

        max_child_depth = new_depth
        children = []
        for val in node.args.values():
            if isinstance(val, exp.Expression):
                children.append(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, exp.Expression):
                        children.append(item)

        for child in children:
            child_depth = get_subquery_depth(child, new_depth)
            if child_depth > max_child_depth:
                max_child_depth = child_depth

        return max_child_depth

    subquery_depth = get_subquery_depth(parsed, 0)
    cognitive_complexity_score = (
        join_count * 3 +
        subquery_depth * 5 +
        case_count * 2 +
        window_function_count * 4
    )

    return {
        "join_count": join_count,
        "subquery_depth": subquery_depth,
        "case_count": case_count,
        "window_function_count": window_function_count,
        "cognitive_complexity_score": cognitive_complexity_score
    }

