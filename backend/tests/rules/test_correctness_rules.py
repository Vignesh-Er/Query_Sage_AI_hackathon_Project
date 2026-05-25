import pytest
import sqlglot
from app.rules.correctness import (
    C01NullComparisonEquals,
    C04UnionInsteadOfUnionAll,
    C05TimezoneUnawareDate,
    C06DivisionWithoutZeroGuard,
    C07MySQLPermissiveGroupBy
)

def test_c01_null_comparison_equals():
    rule = C01NullComparisonEquals()
    
    # Positive case
    ast_pos = sqlglot.parse_one("SELECT * FROM customer WHERE email = NULL;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case (IS NULL)
    ast_neg = sqlglot.parse_one("SELECT * FROM customer WHERE email IS NULL;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_c04_union_instead_of_union_all():
    rule = C04UnionInsteadOfUnionAll()
    
    # Positive case: SELECT id FROM a UNION SELECT id FROM b
    ast_pos = sqlglot.parse_one("SELECT id FROM a UNION SELECT id FROM b;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) >= 1
    
    # Negative case: SELECT id FROM a UNION ALL SELECT id FROM b
    ast_neg = sqlglot.parse_one("SELECT id FROM a UNION ALL SELECT id FROM b;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg
    
    # Edge case: UNION DISTINCT
    ast_edge = sqlglot.parse_one("SELECT id FROM a UNION DISTINCT SELECT id FROM b;")
    findings_edge = rule.analyze(ast_edge)
    assert len(findings_edge) >= 1

def test_c05_timezone_unaware_date():
    rule = C05TimezoneUnawareDate()
    
    # Positive case: SELECT id FROM events WHERE created_at > NOW()
    ast_pos = sqlglot.parse_one("SELECT id FROM events WHERE created_at > NOW();")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) >= 1
    
    # Negative case: SELECT id FROM events WHERE created_at > timezone('UTC', NOW())
    ast_neg = sqlglot.parse_one("SELECT id FROM events WHERE created_at > timezone('UTC', NOW());")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg
    
    # Edge case: using conversion functions
    ast_edge = sqlglot.parse_one("SELECT id FROM events WHERE created_at > convert_tz(NOW(), 'GMT', 'UTC');")
    findings_edge = rule.analyze(ast_edge)
    assert not findings_edge

def test_c06_division_without_zero_guard():
    rule = C06DivisionWithoutZeroGuard()
    
    # Positive case: SELECT revenue / order_count FROM summary
    ast_pos = sqlglot.parse_one("SELECT revenue / order_count FROM summary;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) >= 1
    
    # Negative case: SELECT revenue / NULLIF(order_count, 0) FROM summary
    ast_neg = sqlglot.parse_one("SELECT revenue / NULLIF(order_count, 0) FROM summary;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg
    
    # Edge case: division by literal
    ast_edge = sqlglot.parse_one("SELECT revenue / 10 FROM summary;")
    findings_edge = rule.analyze(ast_edge)
    assert not findings_edge

def test_c07_mysql_permissive_groupby():
    rule = C07MySQLPermissiveGroupBy()
    
    # Positive case using MySQL dialect: SELECT name, email FROM users GROUP BY name
    ast_pos = sqlglot.parse_one("SELECT name, email FROM users GROUP BY name;", read="mysql")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) >= 1
    
    # Negative case: SELECT name, MAX(email) FROM users GROUP BY name
    ast_neg = sqlglot.parse_one("SELECT name, MAX(email) FROM users GROUP BY name;", read="mysql")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg
    
    # Edge case: selecting constant expressions
    ast_edge = sqlglot.parse_one("SELECT name, 'constant' FROM users GROUP BY name;", read="mysql")
    findings_edge = rule.analyze(ast_edge)
    assert not findings_edge
