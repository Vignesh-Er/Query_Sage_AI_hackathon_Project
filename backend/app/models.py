from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    engine = Column(String(50), nullable=False)  # 'postgresql', 'mysql', 'sqlite'
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    database = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    queries = relationship("Query", back_populates="connection", cascade="all, delete-orphan")
    schema_snapshots = relationship("SchemaSnapshot", back_populates="connection", cascade="all, delete-orphan")

class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String(64), index=True, nullable=False)  # SHA-256 hash
    raw_sql = Column(Text, nullable=False)
    normalized_sql = Column(Text, nullable=False)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(Text, default="[]")  # JSON array as string
    source = Column(String(50), nullable=False)  # 'manual', 'bulk', 'natural_language', 'cli'

    connection = relationship("Connection", back_populates="queries")
    findings = relationship("Finding", back_populates="query", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="query", cascade="all, delete-orphan")
    rewrites = relationship("Rewrite", back_populates="query", cascade="all, delete-orphan")
    equivalence_checks = relationship("EquivalenceCheck", back_populates="query", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="query", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="query", cascade="all, delete-orphan")
    regression_events = relationship("RegressionEvent", back_populates="query", foreign_keys="RegressionEvent.query_id", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    rule_id = Column(String(50), nullable=False)
    severity = Column(Integer, nullable=False)  # 1-10
    category = Column(String(50), nullable=False)  # 'PERFORMANCE', 'CORRECTNESS', 'STYLE', 'INDEX', 'LOCKING'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location_start = Column(Integer, nullable=True)
    location_end = Column(Integer, nullable=True)
    auto_fixable = Column(Boolean, default=False)

    query = relationship("Query", back_populates="findings")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    plan_json = Column(Text, nullable=False)  # Normalized plan tree JSON string
    total_cost = Column(Float, nullable=False)
    rows_estimated = Column(Float, nullable=False)
    rows_actual = Column(Float, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    cache_hit_ratio = Column(Float, nullable=False)
    has_seq_scan = Column(Boolean, default=False)
    has_sort_spill = Column(Boolean, default=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", back_populates="plans")

class Rewrite(Base):
    __tablename__ = "rewrites"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    rewritten_sql = Column(Text, nullable=False)
    changes_json = Column(Text, nullable=False)  # array of change detail objects
    index_recommendations_json = Column(Text, nullable=False)  # array of index recommendation objects
    estimated_row_reduction_percent = Column(Float, nullable=False)
    confidence = Column(String(50), nullable=False)  # 'low', 'medium', 'high'
    semantic_equivalence_verified = Column(Boolean, default=False)
    ai_model = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", back_populates="rewrites")
    equivalence_checks = relationship("EquivalenceCheck", back_populates="rewrite", cascade="all, delete-orphan")

class EquivalenceCheck(Base):
    __tablename__ = "equivalence_checks"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    rewrite_id = Column(Integer, ForeignKey("rewrites.id"), nullable=False)
    original_row_count = Column(Integer, nullable=False)
    optimized_row_count = Column(Integer, nullable=False)
    original_hash = Column(String(64), nullable=False)
    optimized_hash = Column(String(64), nullable=False)
    result_match = Column(Boolean, default=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", back_populates="equivalence_checks")
    rewrite = relationship("Rewrite", back_populates="equivalence_checks")

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    query_score = Column(Float, nullable=False)
    rolling_average = Column(Float, nullable=False)
    performance_subscore = Column(Float, nullable=False)
    correctness_subscore = Column(Float, nullable=False)
    style_subscore = Column(Float, nullable=False)
    streak_count = Column(Integer, nullable=False)

    query = relationship("Query", back_populates="scores")

class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=False)
    snapshot_json = Column(Text, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow)

    connection = relationship("Connection", back_populates="schema_snapshots")

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)
    ai_model = Column(String(100), nullable=True)
    prompt_hash = Column(String(64), nullable=True)
    schema_subset_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    confidence = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", back_populates="audit_logs")

class RegressionEvent(Base):
    __tablename__ = "regression_events"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    previous_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    current_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    cost_delta_percent = Column(Float, nullable=False)
    regression_type = Column(String(100), nullable=False)  # 'cost_increase', 'seq_scan_appeared', 'index_dropped'
    detected_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("Query", foreign_keys=[query_id], back_populates="regression_events")
    previous_plan = relationship("Plan", foreign_keys=[previous_plan_id])
    current_plan = relationship("Plan", foreign_keys=[current_plan_id])

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
