import pytest
import sqlglot
from app.rules.schema_index import (
    I01CoveringIndexOpportunity,
    I02IndexPrefixMismatch,
    I03DuplicateOrRedundantIndex,
    I04TableWithoutPrimaryKey,
    I05OverlyWideIndex
)

@pytest.fixture
def mock_schema_context():
    return {
        "tables": {
            "rental": {
                "name": "rental",
                "columns": [
                    {"name": "rental_id", "type": "int", "nullable": False},
                    {"name": "rental_date", "type": "datetime", "nullable": False},
                    {"name": "customer_id", "type": "int", "nullable": False},
                    {"name": "staff_id", "type": "int", "nullable": False}
                ],
                "primary_key": ["rental_id"],
                "row_count": 500
            }
        },
        "indexes": {
            "rental": [
                {
                    "name": "idx_rental_composite",
                    "definition": "CREATE INDEX idx_rental_composite ON rental (customer_id, rental_date)"
                },
                {
                    "name": "idx_rental_redundant",
                    "definition": "CREATE INDEX idx_rental_redundant ON rental (customer_id)"
                }
            ]
        }
    }

def test_i01_covering_index_opportunity(mock_schema_context):
    rule = I01CoveringIndexOpportunity()
    
    # Positive case: filters on customer_id, selects customer_id and staff_id, no index covers staff_id
    ast_pos = sqlglot.parse_one("SELECT customer_id, staff_id FROM rental WHERE customer_id = 42;")
    findings_pos = rule.analyze(ast_pos, mock_schema_context)
    assert len(findings_pos) == 1
    
    # Negative case (covering index exists)
    ast_neg = sqlglot.parse_one("SELECT customer_id, rental_date FROM rental WHERE customer_id = 42;")
    findings_neg = rule.analyze(ast_neg, mock_schema_context)
    assert not findings_neg

def test_i02_index_prefix_mismatch(mock_schema_context):
    rule = I02IndexPrefixMismatch()
    
    # Positive case: filters on rental_date, but composite prefix is customer_id
    ast_pos = sqlglot.parse_one("SELECT * FROM rental WHERE rental_date = '2005-05-24';")
    findings_pos = rule.analyze(ast_pos, mock_schema_context)
    assert len(findings_pos) == 1
    
    # Negative case (filters on customer_id prefix)
    ast_neg = sqlglot.parse_one("SELECT * FROM rental WHERE customer_id = 42;")
    findings_neg = rule.analyze(ast_neg, mock_schema_context)
    assert not findings_neg

def test_i03_duplicate_redundant_index(mock_schema_context):
    rule = I03DuplicateOrRedundantIndex()
    
    # Checks schema duplicate indexing: single index on column a is redundant with (a, b)
    findings = rule.analyze(None, mock_schema_context)
    assert len(findings) == 1
    assert "idx_rental_redundant" in findings[0].description

def test_i04_table_without_primary_key():
    rule = I04TableWithoutPrimaryKey()
    
    schema_context_no_pk = {
        "tables": {
            "users": {
                "name": "users",
                "columns": [{"name": "id", "type": "int"}, {"name": "name", "type": "varchar"}],
                "primary_key": []
            }
        }
    }
    
    # Positive case: table with no PK
    ast_pos = sqlglot.parse_one("SELECT * FROM users WHERE id = 42;")
    findings_pos = rule.analyze(ast_pos, schema_context_no_pk)
    assert len(findings_pos) == 1
    assert "lacks a primary key" in findings_pos[0].description
    
    # Negative case: table has primary key
    schema_context_with_pk = {
        "tables": {
            "users": {
                "name": "users",
                "columns": [{"name": "id", "type": "int"}, {"name": "name", "type": "varchar"}],
                "primary_key": ["id"]
            }
        }
    }
    ast_neg = sqlglot.parse_one("SELECT * FROM users WHERE id = 42;")
    findings_neg = rule.analyze(ast_neg, schema_context_with_pk)
    assert not findings_neg

def test_i05_overly_wide_index():
    rule = I05OverlyWideIndex()
    
    schema_context_wide = {
        "indexes": {
            "users": [
                {
                    "name": "idx_five_cols",
                    "definition": "CREATE INDEX idx_five_cols ON users (col1, col2, col3, col4, col5)"
                }
            ]
        }
    }
    
    # Positive case: index with 5 columns
    findings_pos = rule.analyze(None, schema_context_wide)
    assert len(findings_pos) == 1
    assert "overly wide" in findings_pos[0].description
    
    # Negative case: index with 3 columns
    schema_context_narrow = {
        "indexes": {
            "users": [
                {
                    "name": "idx_three_cols",
                    "definition": "CREATE INDEX idx_three_cols ON users (col1, col2, col3)"
                }
            ]
        }
    }
    findings_neg = rule.analyze(None, schema_context_narrow)
    assert not findings_neg
