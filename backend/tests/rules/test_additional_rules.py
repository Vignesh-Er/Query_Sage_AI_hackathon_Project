import pytest
import sqlglot
from app.rules.additional import (
    A01RecursiveCteLimit,
    A02JsonWithoutExpressionIndex,
    A03IlikeLargeText,
    A04InsertWithoutReturning,
    A05LockEscalationRisk
)

def test_a01_recursive_cte_limit():
    rule = A01RecursiveCteLimit()
    
    # Positive case (missing recursion guard)
    ast_pos = sqlglot.parse_one(
        "WITH RECURSIVE cte AS (SELECT 1 UNION ALL SELECT n + 1 FROM cte) SELECT * FROM cte;"
    )
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case (has limit/level checks)
    ast_neg = sqlglot.parse_one(
        "WITH RECURSIVE cte AS (SELECT 1 UNION ALL SELECT n + 1 FROM cte WHERE n < 10) SELECT * FROM cte;"
    )
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_a02_json_indexing():
    rule = A02JsonWithoutExpressionIndex()
    
    # Positive case (extracting json path)
    ast_pos = sqlglot.parse_one("SELECT * FROM rental WHERE metadata->>'category' = 'action';")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1

def test_a04_insert_returning():
    rule = A04InsertWithoutReturning()
    
    # Positive case (no returning)
    ast_pos = sqlglot.parse_one("INSERT INTO rental (rental_date) VALUES ('2005-05-24');")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case (RETURNING clause)
    ast_neg = sqlglot.parse_one("INSERT INTO rental (rental_date) VALUES ('2005-05-24') RETURNING rental_id;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_a03_ilike():
    rule = A03IlikeLargeText()
    
    # Positive case (ILIKE used)
    ast_pos = sqlglot.parse_one("SELECT * FROM rental WHERE email ILIKE '%@google.com';")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case (LIKE used)
    ast_neg = sqlglot.parse_one("SELECT * FROM rental WHERE email LIKE '%@google.com';")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_a05_lock_escalation():
    rule = A05LockEscalationRisk()
    
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "columns": [{"name": "rental_id", "type": "int"}, {"name": "customer_id", "type": "int"}]
            }
        },
        "indexes": {
            "rental": [{"name": "idx_rental_id", "definition": "CREATE UNIQUE INDEX idx_rental_id ON rental (rental_id)"}]
        }
    }
    
    # Positive case (unindexed filter column customer_id)
    ast_pos = sqlglot.parse_one("UPDATE rental SET rental_date = '2026-05-24' WHERE customer_id = 1;")
    findings_pos = rule.analyze(ast_pos, schema)
    assert len(findings_pos) == 1
    
    # Negative case (indexed filter column rental_id)
    ast_neg = sqlglot.parse_one("UPDATE rental SET rental_date = '2026-05-24' WHERE rental_id = 1;")
    findings_neg = rule.analyze(ast_neg, schema)
    assert not findings_neg
