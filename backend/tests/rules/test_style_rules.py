import pytest
import sqlglot
from app.rules.style import (
    S01ImplicitInsertColumns,
    S02HardcodedLiteralsInFilters,
    S03ExcessiveNesting,
    S04UnreferencedCTE,
    S05RedundantJoin,
    S06MixedJoinSyntax,
    S07ComplexUncommentedQuery
)

def test_s01_implicit_insert_columns():
    rule = S01ImplicitInsertColumns()
    
    # Positive case
    ast_pos = sqlglot.parse_one("INSERT INTO rental VALUES (1, '2005-05-24', 1, 1);")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case (columns defined)
    ast_neg = sqlglot.parse_one("INSERT INTO rental (rental_id, rental_date) VALUES (1, '2005-05-24');")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s02_hardcoded_literals():
    rule = S02HardcodedLiteralsInFilters()
    
    # Positive case (email literal)
    ast_email = sqlglot.parse_one("SELECT * FROM customer WHERE email = 'johndoe@gmail.com';")
    findings_email = rule.analyze(ast_email)
    assert len(findings_email) == 1
    
    # Positive case (date literal)
    ast_date = sqlglot.parse_one("SELECT * FROM rental WHERE rental_date = '2005-05-24';")
    findings_date = rule.analyze(ast_date)
    assert len(findings_date) == 1

    # Negative case (parameter placeholders)
    ast_neg = sqlglot.parse_one("SELECT * FROM customer WHERE email = ?;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s03_excessive_nesting():
    rule = S03ExcessiveNesting()
    
    # Positive case: four levels of subquery nesting
    ast_pos = sqlglot.parse_one("SELECT id FROM (SELECT id FROM (SELECT id FROM (SELECT id FROM orders) s3) s2) s1;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case: simple subquery
    ast_neg = sqlglot.parse_one("SELECT id FROM (SELECT id FROM orders) s1;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s04_unreferenced_cte():
    rule = S04UnreferencedCTE()
    
    # Positive case: WITH unused AS (SELECT 1) SELECT id FROM orders
    ast_pos = sqlglot.parse_one("WITH unused AS (SELECT 1) SELECT id FROM orders;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case: CTE is used
    ast_neg = sqlglot.parse_one("WITH used AS (SELECT 1) SELECT id FROM used;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s05_redundant_join():
    rule = S05RedundantJoin()
    
    # Positive case: JOIN with no columns from joined table used anywhere
    ast_pos = sqlglot.parse_one("SELECT o.id FROM orders o JOIN customer c ON o.customer_id = c.id;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case: columns from joined table are selected
    ast_neg = sqlglot.parse_one("SELECT o.id, c.name FROM orders o JOIN customer c ON o.customer_id = c.id;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s06_mixed_join_syntax():
    rule = S06MixedJoinSyntax()
    
    # Positive case: mixed comma and JOIN syntax
    ast_pos = sqlglot.parse_one("SELECT * FROM orders o, customer c JOIN staff s ON c.id = s.id;")
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case: ANSI join syntax
    ast_neg = sqlglot.parse_one("SELECT * FROM orders o JOIN customer c ON o.customer_id = c.id JOIN staff s ON c.id = s.id;")
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg

def test_s07_complex_uncommented_query():
    rule = S07ComplexUncommentedQuery()
    
    # Positive case: query over 50 tokens with no comments
    long_query = "SELECT a.id, b.name, c.email, d.address, e.phone, f.city, g.state, h.country FROM orders a " \
                 "JOIN customer b ON a.cust_id = b.id JOIN staff c ON b.staff_id = c.id " \
                 "JOIN store d ON c.store_id = d.id JOIN city e ON d.city_id = e.id " \
                 "JOIN country f ON e.country_id = f.id JOIN region g ON f.region_id = g.id " \
                 "JOIN zone h ON g.zone_id = h.id WHERE a.status = 'active' AND b.active = 1 " \
                 "AND c.active = 1 AND d.id = 5;"
    ast_pos = sqlglot.parse_one(long_query)
    findings_pos = rule.analyze(ast_pos)
    assert len(findings_pos) == 1
    
    # Negative case: query has comments
    long_query_commented = "/* test query comments */ " + long_query
    ast_neg = sqlglot.parse_one(long_query_commented)
    findings_neg = rule.analyze(ast_neg)
    assert not findings_neg
