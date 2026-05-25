import pytest
from app.fingerprint import fingerprint

def test_sql_fingerprint_normalization():
    # Identical queries with different numeric literals should have same fingerprint
    sql_1 = "SELECT * FROM rental WHERE customer_id = 42;"
    sql_2 = "SELECT * FROM rental WHERE customer_id = 1500;"
    
    fp_1 = fingerprint(sql_1, "postgres")
    fp_2 = fingerprint(sql_2, "postgres")
    
    assert fp_1 == fp_2

def test_sql_fingerprint_string_literals():
    # String literal substitution checks
    sql_a = "SELECT * FROM customer WHERE email = 'johndoe@gmail.com';"
    sql_b = "SELECT * FROM customer WHERE email = 'admin@website.org';"
    
    assert fingerprint(sql_a, "postgres") == fingerprint(sql_b, "postgres")

def test_sql_fingerprint_parameterized():
    # Comparing literal statement with parameterized statement
    sql_lit = "SELECT * FROM rental WHERE customer_id = 42 AND staff_id = 2;"
    sql_param = "SELECT * FROM rental WHERE customer_id = ? AND staff_id = ?;"
    
    assert fingerprint(sql_lit, "postgres") == fingerprint(sql_param, "postgres")

def test_sql_fingerprint_invalid_query_fallback():
    # Handled fallback checks for query syntax failures
    invalid_sql = "SELECT SELECT FROM WHERE;"
    fp = fingerprint(invalid_sql)
    assert len(fp) == 64  # SHA-256 string length
