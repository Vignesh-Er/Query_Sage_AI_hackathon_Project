import os
import sys
import json
import click
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Connection, Query, Finding, Plan, Rewrite, Score
from app.connectors import get_connector
from app.rules import registry
from app.fingerprint import fingerprint
from app.pipeline import analyze_query_pipeline
from app.report import generate_markdown_report
from app.migration_parser import parse_any_migrations
from app.routers.schema import assess_migration_impact
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@click.group()
def cli():
    """QuerySage - CLI Database Intelligence Tool"""
    # Ensure database is initialized before CLI runs
    import asyncio
    asyncio.run(init_db())

@cli.command()
@click.option("--query", "-q", help="Inline SQL query string")
@click.option("--file", "-f", type=click.Path(exists=True), help="Path to SQL file")
@click.option("--db", "-d", type=int, help="Saved Connection ID")
@click.option("--format", type=click.Choice(["text", "json", "markdown"]), default="text", help="Output format")
@click.option("--severity-threshold", type=int, default=10, help="Fails script if severity exceeds threshold")
@click.option("--orm", help="ORM framework translate context (django, sqlalchemy, prisma)")
def analyze(query, file, db, format, severity_threshold, orm):
    """Analyze a single SQL query string or file"""
    sql = ""
    if query:
        sql = query
    elif file:
        with open(file, "r", encoding="utf-8") as f:
            sql = f.read()
    else:
        click.echo("Error: Must provide either --query or --file", err=True)
        sys.exit(2)

    db_session = SessionLocal()
    
    # We will invoke Layer 1 static analysis directly for simplicity or run the orchestrator
    # For CLI execution, we run static rules first:
    try:
        import sqlglot
        parsed_ast = sqlglot.parse_one(sql)
        findings = registry.run_all(parsed_ast)
    except Exception as e:
        click.echo(f"AST Parse failed: {str(e)}", err=True)
        sys.exit(2)

    max_severity = max((f.severity for f in findings), default=0)

    if format == "json":
        output = {
            "query": sql,
            "findings": [f.to_dict() for f in findings]
        }
        click.echo(json.dumps(output, indent=2))
    elif format == "markdown":
        md = generate_markdown_report(sql, [f.to_dict() for f in findings], None, None)
        click.echo(md)
    else:
        # Beautiful text printing using Rich
        console.print(Panel.fit(f"[bold ember]Analyzing SQL Query[/]\n\n{sql}", border_style="blue"))
        
        if findings:
            table = Table(title="Anti-Pattern Findings", show_header=True, header_style="bold magenta")
            table.add_column("Severity", style="bold red")
            table.add_column("Rule", style="bold yellow")
            table.add_column("Category", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Description", style="dim")
            
            for f in findings:
                table.add_row(
                    str(f.severity),
                    f.rule_id,
                    f.category,
                    f.title,
                    f.description
                )
            console.print(table)
        else:
            console.print("[bold green][OK] No static anti-patterns detected![/]")

    # Check exit threshold
    if max_severity >= severity_threshold:
        console.print(f"[bold red][FAIL] Severity threshold exceeded ({max_severity} >= {severity_threshold})[/]")
        sys.exit(1)
    
    sys.exit(0)

@cli.command()
@click.option("--alter", help="ALTER TABLE statement to test")
@click.option("--migrations", type=click.Path(exists=True), help="Path to migrations folder")
@click.option("--db", "-d", type=int, required=True, help="Saved Connection ID")
@click.option("--severity-threshold", type=int, default=7, help="Fails if static severity exceeds threshold")
def check_schema(alter, migrations, db, severity_threshold):
    """Check unapplied alterations or ALTER commands against query log history"""
    db_session = SessionLocal()
    conn = db_session.query(Connection).filter(Connection.id == db).first()
    if not conn:
        click.echo(f"Error: Connection ID {db} not found.", err=True)
        sys.exit(2)

    alter_operations = []
    if alter:
        parsed_op = parse_alter_statement(alter)
        if parsed_op:
            alter_operations.append(parsed_op)
        else:
            click.echo("Error: Invalid ALTER statement structure.", err=True)
            sys.exit(2)
    elif migrations:
        alter_operations = parse_any_migrations(migrations)
        
    # Run static rule checks against migration SQL files if --migrations is passed
    if migrations:
        import sqlglot
        sql_files = []
        if os.path.isdir(migrations):
            for root, _, files in os.walk(migrations):
                for f in files:
                    if f.endswith(".sql"):
                        sql_files.append(os.path.join(root, f))
        elif os.path.isfile(migrations) and migrations.endswith(".sql"):
            sql_files.append(migrations)

        max_severity = 0
        rule_violations = []

        for sql_file in sql_files:
            with open(sql_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Split queries by semicolon
            statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]
            for stmt in statements:
                try:
                    if stmt.lower().startswith(("begin", "commit", "rollback", "start transaction")):
                        continue
                    dialect = "postgres" if conn.engine == "postgresql" else conn.engine
                    parsed_ast = sqlglot.parse_one(stmt, read=dialect)
                    findings = registry.run_all(parsed_ast)
                    for fnd in findings:
                        if fnd.severity > max_severity:
                            max_severity = fnd.severity
                        if fnd.severity >= severity_threshold:
                            rule_violations.append((sql_file, stmt, fnd))
                except Exception:
                    pass

        if rule_violations:
            console.print("[bold red][FAIL] STATIC RULE VIOLATIONS DETECTED IN MIGRATION FILES:[/]")
            for sql_file, stmt, fnd in rule_violations:
                console.print(f"- [yellow]{os.path.basename(sql_file)}[/] [dim]({fnd.rule_id} - Sev {fnd.severity})[/]: {fnd.title} - {fnd.description}")
                console.print(f"  [dim]SQL: {stmt[:100]}...[/]")
            sys.exit(1)

    if not alter_operations:
        click.echo("No alter operations to check.")
        sys.exit(0)

    queries = db_session.query(Query).filter(Query.connection_id == db).all()
    results = assess_migration_impact(queries, alter_operations, conn.engine)

    if results["broken"]:
        console.print("[bold red][FAIL] BROKEN QUERIES DETECTED:[/]")
        for item in results["broken"]:
            console.print(f"- [yellow]{item.fingerprint}[/]: {item.impact_reason}")
        sys.exit(1)
        
    if results["potentially_affected"]:
        console.print("[bold yellow][WARNING] POTENTIALLY AFFECTED QUERIES DETECTED:[/]")
        for item in results["potentially_affected"]:
            console.print(f"- [yellow]{item.fingerprint}[/]: {item.impact_reason}")
        sys.exit(2)

    console.print("[bold green][OK] Schema changes are safe. No queries broken or affected.[/]")
    sys.exit(0)

@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), required=True, help="Path to SQL log file (.csv, slow query log or json)")
def bulk(file):
    """Analyze a SQL log file in bulk and rank query patterns by impact"""
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    from app.routers.bulk import parse_stat_statements_csv, parse_mysql_slow_log, analyze_single_query_static
    import math
    import json

    raw_queries = []
    if file.endswith(".csv"):
        raw_queries = parse_stat_statements_csv(content)
    elif "query_time" in content.lower():
        raw_queries = parse_mysql_slow_log(content)
    else:
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        raw_queries.append({
                            "query": item.get("query"),
                            "calls": int(item.get("calls", 1)),
                            "mean_time_ms": float(item.get("mean_exec_time", item.get("mean_time_ms", 0.0)))
                        })
                    elif isinstance(item, str):
                        raw_queries.append({"query": item, "calls": 1, "mean_time_ms": 0.0})
        except Exception:
            statements = content.split(";")
            for stmt in statements:
                cleaned = " ".join(stmt.split()).strip()
                if len(cleaned) > 20:
                    raw_queries.append({"query": cleaned, "calls": 1, "mean_time_ms": 0.0})

    if not raw_queries:
        click.echo("Error: No valid queries parsed.", err=True)
        sys.exit(2)

    unique_queries = {}
    for item in raw_queries:
        q = item["query"]
        if q not in unique_queries:
            unique_queries[q] = item
        else:
            unique_queries[q]["calls"] += item["calls"]

    query_items = list(unique_queries.values())
    ranked_patterns = []

    for item in query_items:
        res = analyze_single_query_static(item["query"])
        if res["error"]:
            continue
        
        calls = item["calls"]
        mean_time = item["mean_time_ms"]
        severity_coeff = max(res["severity_sum"], 1.0)
        impact_score = severity_coeff * math.log10(calls + 1)
        
        ranked_patterns.append({
            "query_pattern": res["query"],
            "infrastructure_impact_score": round(impact_score, 2),
            "calls_per_day": float(calls),
            "mean_time_ms": round(mean_time, 2),
            "findings_count": res["findings_count"],
            "fingerprint": res["fingerprint"]
        })

    ranked_patterns.sort(key=lambda x: x["infrastructure_impact_score"], reverse=True)

    table = Table(title="Bulk Analysis Results", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim")
    table.add_column("Score", style="bold red")
    table.add_column("Calls/Day", style="cyan")
    table.add_column("Findings", style="yellow")
    table.add_column("Query Pattern", style="white")

    for rank, item in enumerate(ranked_patterns, 1):
        table.add_row(
            str(rank),
            str(item["infrastructure_impact_score"]),
            str(item["calls_per_day"]),
            str(item["findings_count"]),
            item["query_pattern"][:100] + ("..." if len(item["query_pattern"]) > 100 else "")
        )
    console.print(table)

@cli.command()
@click.option("--query-id", "-q", type=int, required=True, help="Saved Query ID to export")
@click.option("--output", "-o", type=click.Path(), help="Output file path (default: stdout)")
def export(query_id, output):
    """Export a database analysis report for a specific query ID"""
    db_session = SessionLocal()
    query_row = db_session.query(Query).filter(Query.id == query_id).first()
    if not query_row:
        click.echo(f"Error: Query ID {query_id} not found.", err=True)
        sys.exit(2)

    findings = [f.to_dict() for f in query_row.findings]
    
    plan_summary = None
    if query_row.plans:
        plan = query_row.plans[0]
        try:
            plan_json = json.loads(plan.plan_json)
        except Exception:
            plan_json = plan.plan_json
        plan_summary = {
            "total_cost": plan.total_cost,
            "rows_estimated": plan.rows_estimated,
            "rows_actual": plan.rows_actual,
            "execution_time_ms": plan.execution_time_ms,
            "cache_hit_ratio": plan.cache_hit_ratio,
            "has_seq_scan": plan.has_seq_scan,
            "has_sort_spill": plan.has_sort_spill,
            "plan_json": plan_json
        }

    rewrite_proposal = None
    if query_row.rewrites:
        rewrite = query_row.rewrites[0]
        try:
            changes = json.loads(rewrite.changes_json)
        except Exception:
            changes = rewrite.changes_json
        try:
            recs = json.loads(rewrite.index_recommendations_json)
        except Exception:
            recs = rewrite.index_recommendations_json
        rewrite_proposal = {
            "rewritten_query": rewrite.rewritten_sql,
            "changes": changes,
            "index_recommendations": recs,
            "estimated_row_reduction_percent": rewrite.estimated_row_reduction_percent,
            "confidence": rewrite.confidence
        }

    md_report = generate_markdown_report(
        query_row.raw_sql,
        findings,
        plan_summary,
        rewrite_proposal
    )

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(md_report)
        console.print(f"[bold green][OK] Report successfully exported to {output}[/]")
    else:
        click.echo(md_report)

@cli.command()
def score():
    """Prints the current DBA Scorecard"""
    db_session = SessionLocal()
    latest_score = db_session.query(Score).order_by(Score.submitted_at.desc()).first()
    if not latest_score:
        console.print("No scores logged. Run analyze stream to generate rolling scorecard updates.")
        return
        
    console.print(Panel(
        f"[bold cyan]DBA SCORECARD[/]\n\n"
        f"Rolling average: [bold green]{latest_score.rolling_average}[/]\n"
        f"Streak: [bold yellow]{latest_score.streak_count} queries[/]\n"
        f"Subscores:\n"
        f"- Performance: {latest_score.performance_subscore}\n"
        f"- Correctness: {latest_score.correctness_subscore}\n"
        f"- Style: {latest_score.style_subscore}",
        title="Scorecard",
        expand=False
    ))

if __name__ == "__main__":
    cli()
