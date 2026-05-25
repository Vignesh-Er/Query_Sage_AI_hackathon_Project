import json
from typing import Any, Dict, List, Optional, Tuple

class PlanNode:
    def __init__(
        self,
        node_type: str,
        relation_name: Optional[str] = None,
        alias: Optional[str] = None,
        rows_estimated: float = 0.0,
        rows_actual: float = 0.0,
        cost_startup: float = 0.0,
        cost_total: float = 0.0,
        shared_blocks_hit: int = 0,
        shared_blocks_read: int = 0,
        temp_blocks_written: int = 0,
        children: List["PlanNode"] = None,
        planning_memory_used_bytes: Optional[int] = None,
        planning_memory_allocated_bytes: Optional[int] = None,
        serialization_time_ms: Optional[float] = None,
        local_blk_read_time_ms: Optional[float] = None,
        local_blk_write_time_ms: Optional[float] = None,
        jit_deform_time_ms: Optional[float] = None
    ):
        self.node_type = node_type
        self.relation_name = relation_name
        self.alias = alias
        self.rows_estimated = rows_estimated
        self.rows_actual = rows_actual
        self.cost_startup = cost_startup
        self.cost_total = cost_total
        self.shared_blocks_hit = shared_blocks_hit
        self.shared_blocks_read = shared_blocks_read
        self.temp_blocks_written = temp_blocks_written
        self.children = children or []
        self.planning_memory_used_bytes = planning_memory_used_bytes
        self.planning_memory_allocated_bytes = planning_memory_allocated_bytes
        self.serialization_time_ms = serialization_time_ms
        self.local_blk_read_time_ms = local_blk_read_time_ms
        self.local_blk_write_time_ms = local_blk_write_time_ms
        self.jit_deform_time_ms = jit_deform_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "relation_name": self.relation_name,
            "alias": self.alias,
            "rows_estimated": self.rows_estimated,
            "rows_actual": self.rows_actual,
            "cost_startup": self.cost_startup,
            "cost_total": self.cost_total,
            "shared_blocks_hit": self.shared_blocks_hit,
            "shared_blocks_read": self.shared_blocks_read,
            "temp_blocks_written": self.temp_blocks_written,
            "planning_memory_used_bytes": self.planning_memory_used_bytes,
            "planning_memory_allocated_bytes": self.planning_memory_allocated_bytes,
            "serialization_time_ms": self.serialization_time_ms,
            "local_blk_read_time_ms": self.local_blk_read_time_ms,
            "local_blk_write_time_ms": self.local_blk_write_time_ms,
            "jit_deform_time_ms": self.jit_deform_time_ms,
            "children": [c.to_dict() for c in self.children]
        }

def _parse_memory_to_bytes(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        val_clean = val.strip().lower()
        digits = "".join([c for c in val_clean if c.isdigit() or c == "."])
        if not digits:
            return None
        num = float(digits)
        if "kb" in val_clean:
            return int(num * 1024)
        if "mb" in val_clean:
            return int(num * 1024 * 1024)
        return int(num)
    return None

def parse_postgresql_plan(plan_data: Any) -> PlanNode:
    if isinstance(plan_data, list):
        plan_data = plan_data[0]
        
    planning = plan_data.get("Planning", {}) if isinstance(plan_data, dict) else {}
    planning_memory = planning.get("Memory", {})
    planning_used = planning_memory.get("used")
    planning_allocated = planning_memory.get("allocated")
    
    serialization = plan_data.get("Serialization", {}) if isinstance(plan_data, dict) else {}
    serialization_time = serialization.get("Time")
    
    jit = plan_data.get("JIT", {}) if isinstance(plan_data, dict) else {}
    jit_timing = jit.get("Timing", {})
    jit_deform = jit_timing.get("Deform")
    
    execution_time = plan_data.get("Execution Time")
    
    planning_memory_used_bytes = _parse_memory_to_bytes(planning_used)
    planning_memory_allocated_bytes = _parse_memory_to_bytes(planning_allocated)
    
    serialization_time_ms = float(serialization_time) if serialization_time is not None else None
    jit_deform_time_ms = float(jit_deform) if jit_deform is not None else None
    execution_time_ms = float(execution_time) if execution_time is not None else None
    
    plan_node_dict = plan_data.get("Plan", {}) if isinstance(plan_data, dict) else {}
    root_node = _build_postgres_node(plan_node_dict)
    
    root_node.planning_memory_used_bytes = planning_memory_used_bytes
    root_node.planning_memory_allocated_bytes = planning_memory_allocated_bytes
    root_node.serialization_time_ms = serialization_time_ms
    root_node.jit_deform_time_ms = jit_deform_time_ms
    root_node.execution_time_ms = execution_time_ms
    
    return root_node

def _build_postgres_node(node_dict: dict) -> PlanNode:
    node_type = node_dict.get("Node Type", "Unknown")
    rel_name = node_dict.get("Relation Name")
    alias = node_dict.get("Alias")
    rows_estimated = float(node_dict.get("Plan Rows", 0))
    rows_actual = float(node_dict.get("Actual Rows", 0))
    cost_startup = float(node_dict.get("Startup Cost", 0))
    cost_total = float(node_dict.get("Total Cost", 0))
    
    shared_hit = int(node_dict.get("Shared Hit Blocks", 0))
    shared_read = int(node_dict.get("Shared Read Blocks", 0))
    temp_write = int(node_dict.get("Temp Written Blocks", 0))
    
    local_blk_read_time = node_dict.get("Local Blks Read Time")
    local_blk_write_time = node_dict.get("Local Blks Write Time")
    local_blk_read_time_ms = float(local_blk_read_time) if local_blk_read_time is not None else None
    local_blk_write_time_ms = float(local_blk_write_time) if local_blk_write_time is not None else None
    
    children_nodes = []
    if "Plans" in node_dict:
        for child in node_dict["Plans"]:
            children_nodes.append(_build_postgres_node(child))
            
    return PlanNode(
        node_type=node_type,
        relation_name=rel_name,
        alias=alias,
        rows_estimated=rows_estimated,
        rows_actual=rows_actual,
        cost_startup=cost_startup,
        cost_total=cost_total,
        shared_blocks_hit=shared_hit,
        shared_blocks_read=shared_read,
        temp_blocks_written=temp_write,
        children=children_nodes,
        local_blk_read_time_ms=local_blk_read_time_ms,
        local_blk_write_time_ms=local_blk_write_time_ms
    )

def parse_mysql_plan(plan_data: Any) -> PlanNode:
    # MySQL plan root is usually query_block
    if isinstance(plan_data, str):
        try:
            plan_data = json.loads(plan_data)
        except Exception:
            pass
    if isinstance(plan_data, dict) and "query_block" in plan_data:
        qblock = plan_data["query_block"]
        cost = float(qblock.get("cost_info", {}).get("query_cost", 0.0))
        
        # Traverse table/joins inside query_block
        children = []
        rel_name = None
        access_type = "Unknown"
        rows_est = 0
        
        # MySQL can have "table" or "nested_loop" (which is a list of tables)
        if "table" in qblock:
            tbl_info = qblock["table"]
            rel_name = tbl_info.get("table_name")
            access_type = tbl_info.get("access_type", "ALL")
            rows_est = float(tbl_info.get("rows_examined_per_scan", 0))
        elif "nested_loop" in qblock:
            access_type = "Nested Loop"
            for loop in qblock["nested_loop"]:
                if "table" in loop:
                    tbl_info = loop["table"]
                    children.append(PlanNode(
                        node_type=tbl_info.get("access_type", "ALL"),
                        relation_name=tbl_info.get("table_name"),
                        rows_estimated=float(tbl_info.get("rows_examined_per_scan", 0))
                    ))
        return PlanNode(
            node_type=access_type,
            relation_name=rel_name,
            cost_total=cost,
            rows_estimated=rows_est,
            children=children
        )
    return PlanNode(node_type="MySQL Explain")

def parse_sqlite_plan(plan_rows: List[Dict[str, Any]]) -> PlanNode:
    # Build a simple tree or list from SQLite EXPLAIN QUERY PLAN
    children = []
    for row in plan_rows:
        children.append(PlanNode(
            node_type="SQLite Scan",
            relation_name=row.get("detail", "")
        ))
    return PlanNode(node_type="SQLite Explain", children=children)

def derive_postgres_metrics(root_node: PlanNode) -> Dict[str, Any]:
    total_hit = 0
    total_read = 0
    temp_written = 0
    seq_scans = []
    stats_staleness = []

    # JIT warning check
    findings = []
    jit_deform = getattr(root_node, "jit_deform_time_ms", None)
    execution_time = getattr(root_node, "execution_time_ms", None)
    if jit_deform is not None and execution_time is not None and execution_time > 0:
        if jit_deform > 0.20 * execution_time:
            findings.append("JIT compilation is spending significant time on tuple deforming, which sometimes indicates that disabling JIT for this specific query pattern would be faster.")

    def traverse(node: PlanNode):
        nonlocal total_hit, total_read, temp_written
        total_hit += node.shared_blocks_hit if node.shared_blocks_hit else 0
        total_read += node.shared_blocks_read if node.shared_blocks_read else 0
        temp_written += node.temp_blocks_written if node.temp_blocks_written else 0
        
        # Check seq scan on large table (we flag it if rows_estimated > 10000)
        if "Seq Scan" in node.node_type and node.relation_name:
            seq_scans.append((node.relation_name, node.rows_estimated))
            
        # Stats staleness check
        if node.relation_name and node.rows_estimated > 0 and node.rows_actual > 0:
            ratio = node.rows_actual / node.rows_estimated
            if ratio > 5.0 or ratio < 0.2:
                stats_staleness.append({
                    "table": node.relation_name,
                    "estimated": node.rows_estimated,
                    "actual": node.rows_actual,
                    "ratio": ratio
                })
        
        for child in node.children:
            traverse(child)

    traverse(root_node)
    
    # Calculate Cache hit ratio
    hit_ratio = 1.0
    if total_hit + total_read > 0:
        hit_ratio = total_hit / (total_hit + total_read)
        
    return {
        "cache_hit_ratio": hit_ratio,
        "temp_blocks_written": temp_written,
        "has_sort_spill": temp_written > 0,
        "seq_scans": seq_scans,
        "stats_staleness": stats_staleness,
        "findings": findings
    }
