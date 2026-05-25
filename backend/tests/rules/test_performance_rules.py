import pytest
import sqlglot
from app.rules.performance import (
    P01SelectStar,
    P02FunctionOnIndexedColumn,
    P03LeadingWildcardLike,
    P04OrConditionsIndex,
    P05UnindexedJoinColumn,
    P06CorrelatedSubquery,
    P07MissingLimit,
    P08DistinctMaskingBadJoin,
    P09NPlusOneSubquery,
    P10DeepOffsetPagination,
    P11ImplicitTypeConversion,
    P12NonSargablePredicates,
    P13RedundantOrderBy,
    P14CountInsteadOfExists,
    P15MultipleCountDistinct,
    P16HavingWithoutGroupBy,
    P17UnboundedUpdateDelete,
    P18CartesianJoin,
    P19SelfJoinReplaceableByWindow,
    P20InefficientRowNumberWrapping
)

# P01
def test_p01_select_star_positive():
    rule = P01SelectStar()
    ast = sqlglot.parse_one("SELECT * FROM rental;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P01"

def test_p01_select_star_negative():
    rule = P01SelectStar()
    ast = sqlglot.parse_one("SELECT rental_id, rental_date FROM rental;")
    findings = rule.analyze(ast)
    assert not findings

def test_p01_select_star_edge():
    rule = P01SelectStar()
    ast = sqlglot.parse_one("SELECT a.rental_id, b.customer_id FROM rental a JOIN customer b ON a.customer_id = b.customer_id;")
    findings = rule.analyze(ast)
    assert not findings

# P02
def test_p02_function_on_indexed_column_positive():
    rule = P02FunctionOnIndexedColumn()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE YEAR(rental_date) = 2005;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P02"

def test_p02_function_on_indexed_column_negative():
    rule = P02FunctionOnIndexedColumn()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE rental_date >= '2005-01-01';")
    findings = rule.analyze(ast)
    assert not findings

def test_p02_function_on_indexed_column_edge():
    rule = P02FunctionOnIndexedColumn()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE LOWER(email) = 'test@example.com';")
    findings = rule.analyze(ast)
    assert len(findings) == 1

# P03
def test_p03_leading_wildcard_like_positive():
    rule = P03LeadingWildcardLike()
    ast = sqlglot.parse_one("SELECT * FROM customer WHERE email LIKE '%@gmail.com';")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P03"

def test_p03_leading_wildcard_like_negative():
    rule = P03LeadingWildcardLike()
    ast = sqlglot.parse_one("SELECT * FROM customer WHERE email LIKE 'john%';")
    findings = rule.analyze(ast)
    assert not findings

def test_p03_leading_wildcard_like_edge():
    rule = P03LeadingWildcardLike()
    ast = sqlglot.parse_one("SELECT * FROM customer WHERE email LIKE 'john%@gmail.com';")
    findings = rule.analyze(ast)
    assert not findings

# P04
def test_p04_or_conditions_index_positive():
    rule = P04OrConditionsIndex()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE customer_id = 1 OR staff_id = 2;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P04"

def test_p04_or_conditions_index_negative():
    rule = P04OrConditionsIndex()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE customer_id = 1 AND staff_id = 2;")
    findings = rule.analyze(ast)
    assert not findings

def test_p04_or_conditions_index_edge():
    rule = P04OrConditionsIndex()
    ast = sqlglot.parse_one("SELECT * FROM rental WHERE customer_id = 1 OR customer_id = 2;")
    findings = rule.analyze(ast)
    assert len(findings) == 1

# P05
def test_p05_unindexed_join_column_positive():
    rule = P05UnindexedJoinColumn()
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "columns": [{"name": "customer_id", "type": "int"}]
            },
            "customer": {
                "name": "customer",
                "columns": [{"name": "customer_id", "type": "int"}]
            }
        },
        "indexes": {
            "rental": [],
            "customer": []
        }
    }
    ast = sqlglot.parse_one("SELECT * FROM rental JOIN customer ON rental.customer_id = customer.customer_id;")
    findings = rule.analyze(ast, schema)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P05"

def test_p05_unindexed_join_column_negative():
    rule = P05UnindexedJoinColumn()
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "columns": [{"name": "customer_id", "type": "int"}]
            },
            "customer": {
                "name": "customer",
                "columns": [{"name": "customer_id", "type": "int"}]
            }
        },
        "indexes": {
            "rental": [{"name": "idx_rental_cust", "definition": "CREATE INDEX idx_rental_cust ON rental (customer_id)"}],
            "customer": [{"name": "idx_cust_id", "definition": "CREATE INDEX idx_cust_id ON customer (customer_id)"}]
        }
    }
    ast = sqlglot.parse_one("SELECT * FROM rental JOIN customer ON rental.customer_id = customer.customer_id;")
    findings = rule.analyze(ast, schema)
    assert not findings

def test_p05_unindexed_join_column_edge():
    rule = P05UnindexedJoinColumn()
    # no schema context
    ast = sqlglot.parse_one("SELECT * FROM rental JOIN customer ON rental.customer_id = customer.customer_id;")
    findings = rule.analyze(ast, None)
    assert not findings

# P06
def test_p06_correlated_subquery_positive():
    rule = P06CorrelatedSubquery()
    ast = sqlglot.parse_one("SELECT * FROM orders WHERE status = (SELECT status FROM orders o2 WHERE o2.id = orders.id);")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P06"

def test_p06_correlated_subquery_negative():
    rule = P06CorrelatedSubquery()
    ast = sqlglot.parse_one("SELECT * FROM orders WHERE status = (SELECT status FROM orders WHERE orders.id = 123);")
    findings = rule.analyze(ast)
    assert not findings

def test_p06_correlated_subquery_edge():
    rule = P06CorrelatedSubquery()
    ast = sqlglot.parse_one("SELECT * FROM orders WHERE status IN (SELECT status FROM status_lookup);")
    findings = rule.analyze(ast)
    assert not findings

# P07
def test_p07_missing_limit_positive():
    rule = P07MissingLimit()
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "row_count": 120000
            }
        }
    }
    ast = sqlglot.parse_one("SELECT * FROM rental;")
    findings = rule.analyze(ast, schema)
    assert len(findings) == 1
    assert findings[0].rule_id == "P07"

def test_p07_missing_limit_negative():
    rule = P07MissingLimit()
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "row_count": 120000
            }
        }
    }
    ast = sqlglot.parse_one("SELECT * FROM rental LIMIT 10;")
    findings = rule.analyze(ast, schema)
    assert not findings

def test_p07_missing_limit_edge():
    rule = P07MissingLimit()
    schema = {
        "tables": {
            "rental": {
                "name": "rental",
                "row_count": 500
            }
        }
    }
    ast = sqlglot.parse_one("SELECT * FROM rental;")
    findings = rule.analyze(ast, schema)
    assert not findings

# P08
def test_p08_distinct_masking_bad_join_positive():
    rule = P08DistinctMaskingBadJoin()
    ast = sqlglot.parse_one("SELECT DISTINCT c.first_name, c.last_name FROM customer c JOIN rental r ON c.customer_id = r.customer_id;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P08"

def test_p08_distinct_masking_bad_join_negative():
    rule = P08DistinctMaskingBadJoin()
    ast = sqlglot.parse_one("SELECT c.first_name, c.last_name FROM customer c JOIN rental r ON c.customer_id = r.customer_id;")
    findings = rule.analyze(ast)
    assert not findings

def test_p08_distinct_masking_bad_join_edge():
    rule = P08DistinctMaskingBadJoin()
    ast = sqlglot.parse_one("SELECT DISTINCT first_name FROM customer;")
    findings = rule.analyze(ast)
    assert not findings

# P09
def test_p09_nplusone_subquery_positive():
    rule = P09NPlusOneSubquery()
    ast = sqlglot.parse_one("SELECT c.customer_id, (SELECT COUNT(*) FROM rental r WHERE r.customer_id = c.customer_id) AS rental_count FROM customer c;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P09"

def test_p09_nplusone_subquery_negative():
    rule = P09NPlusOneSubquery()
    ast = sqlglot.parse_one("SELECT c.customer_id, c.first_name FROM customer c JOIN rental r ON c.customer_id = r.customer_id;")
    findings = rule.analyze(ast)
    assert not findings

def test_p09_nplusone_subquery_edge():
    rule = P09NPlusOneSubquery()
    ast = sqlglot.parse_one("SELECT c.customer_id, 42 FROM customer c;")
    findings = rule.analyze(ast)
    assert not findings

# P10
def test_p10_deep_offset_pagination_positive():
    rule = P10DeepOffsetPagination()
    ast = sqlglot.parse_one("SELECT * FROM rental LIMIT 10 OFFSET 15000;")
    findings = rule.analyze(ast)
    assert len(findings) == 1
    assert findings[0].rule_id == "P10"

def test_p10_deep_offset_pagination_negative():
    rule = P10DeepOffsetPagination()
    ast = sqlglot.parse_one("SELECT * FROM rental LIMIT 10 OFFSET 50;")
    findings = rule.analyze(ast)
    assert not findings

def test_p10_deep_offset_pagination_edge():
    rule = P10DeepOffsetPagination()
    ast = sqlglot.parse_one("SELECT * FROM rental LIMIT 10 OFFSET 0;")
    findings = rule.analyze(ast)
    assert not findings

# P11
def test_p11_implicit_type_conversion_positive():
    rule = P11ImplicitTypeConversion()
    schema = {
        "tables": {
            "orders": {
                "name": "orders",
                "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}]
            }
        }
    }
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE user_id = '123';")
    findings = rule.analyze(ast, schema)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P11"

def test_p11_implicit_type_conversion_negative():
    rule = P11ImplicitTypeConversion()
    schema = {
        "tables": {
            "orders": {
                "name": "orders",
                "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}]
            }
        }
    }
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE user_id = 123;")
    findings = rule.analyze(ast, schema)
    assert not findings

def test_p11_implicit_type_conversion_edge():
    rule = P11ImplicitTypeConversion()
    schema = {
        "tables": {
            "orders": {
                "name": "orders",
                "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}]
            }
        }
    }
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE CAST(user_id AS text) = '123';")
    findings = rule.analyze(ast, schema)
    assert not findings

# P12
def test_p12_non_sargable_predicates_positive():
    rule = P12NonSargablePredicates()
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE status != 'active';")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P12"

def test_p12_non_sargable_predicates_negative():
    rule = P12NonSargablePredicates()
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE status = 'active';")
    findings = rule.analyze(ast)
    assert not findings

def test_p12_non_sargable_predicates_edge():
    rule = P12NonSargablePredicates()
    ast = sqlglot.parse_one("SELECT id FROM orders WHERE NOT status = 'active';")
    findings = rule.analyze(ast)
    assert len(findings) >= 1

# P13
def test_p13_redundant_order_by_positive():
    rule = P13RedundantOrderBy()
    ast = sqlglot.parse_one("SELECT id FROM (SELECT id FROM orders ORDER BY id) sub;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P13"

def test_p13_redundant_order_by_negative():
    rule = P13RedundantOrderBy()
    ast = sqlglot.parse_one("SELECT id FROM orders ORDER BY id;")
    findings = rule.analyze(ast)
    assert not findings

def test_p13_redundant_order_by_edge():
    rule = P13RedundantOrderBy()
    ast = sqlglot.parse_one("WITH cte AS (SELECT id FROM orders ORDER BY id) SELECT id FROM cte;")
    findings = rule.analyze(ast)
    assert not findings

# P14
def test_p14_count_instead_of_exists_positive():
    rule = P14CountInsteadOfExists()
    ast = sqlglot.parse_one("SELECT COUNT(*) FROM users WHERE active = 1;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P14"

def test_p14_count_instead_of_exists_negative():
    rule = P14CountInsteadOfExists()
    ast = sqlglot.parse_one("SELECT COUNT(*) FROM users GROUP BY country;")
    findings = rule.analyze(ast)
    assert not findings

def test_p14_count_instead_of_exists_edge():
    rule = P14CountInsteadOfExists()
    ast = sqlglot.parse_one("SELECT COUNT(*) as total FROM users;")
    findings = rule.analyze(ast)
    assert not findings

# P15
def test_p15_multiple_count_distinct_positive():
    rule = P15MultipleCountDistinct()
    ast = sqlglot.parse_one("SELECT COUNT(DISTINCT a), COUNT(DISTINCT b), COUNT(DISTINCT c) FROM t;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P15"

def test_p15_multiple_count_distinct_negative():
    rule = P15MultipleCountDistinct()
    ast = sqlglot.parse_one("SELECT COUNT(DISTINCT a), COUNT(DISTINCT b) FROM t;")
    findings = rule.analyze(ast)
    assert not findings

def test_p15_multiple_count_distinct_edge():
    rule = P15MultipleCountDistinct()
    ast = sqlglot.parse_one("SELECT COUNT(DISTINCT a) FROM t;")
    findings = rule.analyze(ast)
    assert not findings

# P16
def test_p16_having_without_group_by_positive():
    rule = P16HavingWithoutGroupBy()
    ast = sqlglot.parse_one("SELECT name FROM users HAVING active = 1;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P16"

def test_p16_having_without_group_by_negative():
    rule = P16HavingWithoutGroupBy()
    ast = sqlglot.parse_one("SELECT name, COUNT(*) FROM users GROUP BY name HAVING COUNT(*) > 5;")
    findings = rule.analyze(ast)
    assert not findings

def test_p16_having_without_group_by_edge():
    rule = P16HavingWithoutGroupBy()
    ast = sqlglot.parse_one("SELECT name FROM users HAVING 1 = 1;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1

# P17
def test_p17_unbounded_update_delete_positive():
    rule = P17UnboundedUpdateDelete()
    ast = sqlglot.parse_one("UPDATE users SET active = 0;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P17"

def test_p17_unbounded_update_delete_negative():
    rule = P17UnboundedUpdateDelete()
    ast = sqlglot.parse_one("UPDATE users SET active = 0 WHERE last_login < '2020-01-01';")
    findings = rule.analyze(ast)
    assert not findings

def test_p17_unbounded_update_delete_edge():
    rule = P17UnboundedUpdateDelete()
    ast = sqlglot.parse_one("UPDATE users SET active = 0 WHERE 1 = 1;")
    findings = rule.analyze(ast)
    assert not findings

# P18
def test_p18_cartesian_join_positive():
    rule = P18CartesianJoin()
    ast = sqlglot.parse_one("SELECT id FROM users, orders;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P18"

def test_p18_cartesian_join_negative():
    rule = P18CartesianJoin()
    ast = sqlglot.parse_one("SELECT id FROM users, orders WHERE users.id = orders.user_id;")
    findings = rule.analyze(ast)
    assert not findings

def test_p18_cartesian_join_edge():
    rule = P18CartesianJoin()
    ast = sqlglot.parse_one("SELECT id FROM users CROSS JOIN orders;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1

# P19
def test_p19_self_join_window_positive():
    rule = P19SelfJoinReplaceableByWindow()
    ast = sqlglot.parse_one("SELECT a.id, b.created_at FROM orders a JOIN orders b ON a.id = b.id - 1;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P19"

def test_p19_self_join_window_negative():
    rule = P19SelfJoinReplaceableByWindow()
    ast = sqlglot.parse_one("SELECT a.id FROM orders a JOIN orders b ON a.parent_id = b.id;")
    findings = rule.analyze(ast)
    assert not findings

def test_p19_self_join_window_edge():
    rule = P19SelfJoinReplaceableByWindow()
    ast = sqlglot.parse_one("SELECT u1.id FROM users u1 JOIN users u2 ON u1.manager_id = u2.id;")
    findings = rule.analyze(ast)
    assert not findings

# P20
def test_p20_inefficient_row_number_positive():
    rule = P20InefficientRowNumberWrapping()
    ast = sqlglot.parse_one("SELECT id FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) rn FROM orders) sub WHERE rn BETWEEN 10 AND 20;")
    findings = rule.analyze(ast)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P20"

def test_p20_inefficient_row_number_negative():
    rule = P20InefficientRowNumberWrapping()
    ast = sqlglot.parse_one("SELECT ROW_NUMBER() OVER (ORDER BY id), id FROM orders;")
    findings = rule.analyze(ast)
    assert not findings

def test_p20_inefficient_row_number_edge():
    rule = P20InefficientRowNumberWrapping()
    ast = sqlglot.parse_one("WITH numbered AS (SELECT id, ROW_NUMBER() OVER (ORDER BY id) rn FROM orders) SELECT id FROM numbered WHERE rn = 1;")
    findings = rule.analyze(ast)
    assert not findings
