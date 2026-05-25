import os
import json
import pytest
from app.parser import parse_postgresql_plan, derive_postgres_metrics

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "plans")

def load_fixture(name: str) -> dict:
    path = os.path.join(FIXTURE_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_parse_seq_scan_plan():
    raw_plan = load_fixture("seq_scan.json")
    root_node = parse_postgresql_plan(raw_plan)
    
    assert root_node.node_type == "Seq Scan"
    assert root_node.relation_name == "rental"
    assert root_node.cost_total == 310.96
    
    metrics = derive_postgres_metrics(root_node)
    assert metrics["cache_hit_ratio"] == 1.0
    assert metrics["has_sort_spill"] is False
    assert len(metrics["seq_scans"]) == 1
    assert metrics["seq_scans"][0] == ("rental", 16044.0)

def test_parse_index_scan_plan():
    raw_plan = load_fixture("index_scan.json")
    root_node = parse_postgresql_plan(raw_plan)
    
    assert root_node.node_type == "Index Scan"
    assert root_node.relation_name == "rental"
    assert root_node.cost_total == 8.30
    
    metrics = derive_postgres_metrics(root_node)
    # hit = 3, read = 1. ratio = 3/4 = 0.75
    assert metrics["cache_hit_ratio"] == 0.75
    assert len(metrics["seq_scans"]) == 0

def test_parse_hash_join_spill_plan():
    raw_plan = load_fixture("hash_join_spill.json")
    root_node = parse_postgresql_plan(raw_plan)
    
    assert root_node.node_type == "Hash Join"
    
    metrics = derive_postgres_metrics(root_node)
    assert metrics["has_sort_spill"] is True  # Temp Written Blocks = 128 > 0
    assert len(metrics["seq_scans"]) == 2  # rental and customer seq scans

def test_parse_pg16_expanded_metrics():
    raw_plan = {
        "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "rental",
            "Plan Rows": 100,
            "Actual Rows": 100,
            "Local Blks Read Time": 1.25,
            "Local Blks Write Time": 0.5
        },
        "Planning": {
            "Memory": {
                "used": "15 kB",
                "allocated": "64 kB"
            }
        },
        "JIT": {
            "Timing": {
                "Deform": 15.0
            }
        },
        "Serialization": {
            "Time": 2.5
        },
        "Execution Time": 50.0
    }
    
    root_node = parse_postgresql_plan(raw_plan)
    
    assert root_node.planning_memory_used_bytes == 15360
    assert root_node.planning_memory_allocated_bytes == 65536
    assert root_node.serialization_time_ms == 2.5
    assert root_node.local_blk_read_time_ms == 1.25
    assert root_node.local_blk_write_time_ms == 0.5
    assert root_node.jit_deform_time_ms == 15.0
    assert root_node.execution_time_ms == 50.0
    
    metrics = derive_postgres_metrics(root_node)
    # JIT deform 15.0 exceeds 20% of execution time 50.0 (30%)
    assert len(metrics["findings"]) == 1
    assert "JIT compilation is spending significant time on tuple deforming" in metrics["findings"][0]
