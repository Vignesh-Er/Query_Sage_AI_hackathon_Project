import pytest
from app.scoring import calculate_cognitive_complexity

def test_simple_query_complexity():
    """
    Test one: a simple SELECT with no joins, cases, or windows returns all zeroes.
    """
    sql = "SELECT id FROM users WHERE active = 1"
    metrics = calculate_cognitive_complexity(sql)
    assert metrics["join_count"] == 0
    assert metrics["subquery_depth"] == 0
    assert metrics["case_count"] == 0
    assert metrics["window_function_count"] == 0
    assert metrics["cognitive_complexity_score"] == 0

def test_deep_join_subquery_complexity():
    """
    Test two: a query with 2 joins and 2 subquery nesting levels.
    Absolute score: 2 * 3 + 2 * 5 = 16.
    """
    sql = (
        "SELECT a.id FROM orders a "
        "JOIN order_items b ON a.id = b.order_id "
        "JOIN products c ON b.product_id = c.id "
        "WHERE a.customer_id IN ("
        "  SELECT id FROM customers WHERE country IN ("
        "    SELECT country FROM regions WHERE active = 1"
        "  )"
        ")"
    )
    metrics = calculate_cognitive_complexity(sql)
    assert metrics["join_count"] == 2
    assert metrics["subquery_depth"] == 2
    assert metrics["cognitive_complexity_score"] == 16

def test_case_and_window_complexity():
    """
    Test three: 1 case expression, 1 window function.
    Absolute score: 1 * 2 + 1 * 4 = 6.
    """
    sql = (
        "SELECT id, "
        "CASE "
        "  WHEN status = 1 THEN 'active' "
        "  WHEN status = 2 THEN 'pending' "
        "  ELSE 'unknown' "
        "END as label, "
        "ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at) as rn "
        "FROM orders"
    )
    metrics = calculate_cognitive_complexity(sql)
    assert metrics["join_count"] == 0
    assert metrics["subquery_depth"] == 0
    assert metrics["case_count"] == 1
    assert metrics["window_function_count"] == 1
    assert metrics["cognitive_complexity_score"] == 6
