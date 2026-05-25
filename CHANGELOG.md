# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-24

### Added
- **Interactive Plan Tree Visualizer**: Built with React Flow (`@xyflow/react`) to replace tabular EXPLAIN outputs with color-coded flowchart nodes, featuring collapsible hierarchy and temp-file sort spill alerts.
- **ORM Fingerprinting & Recommendations**: Created an AST-based signature module that detects Django, SQLAlchemy, Prisma, Sequelize, and Hibernate frameworks and issues code-level remediation.
- **ECharts Performance Metrics Dashboard**: Integrated Canvas-based `echarts` and `echarts-for-react` plotting query execution totals, count trends, and score shifts over time.
- **Monaco LSP WebSocket Proxy**: Spawns a Go-based `sqls` language server to handle autocompletion, hovers, and syntax diagnostic assistance inside Monaco Editor, with a graceful dismissible fallback banner if the binary is missing.
- **AST-Based Cognitive Complexity Scoring**: A structural complexity scorer traversing the AST to evaluate join depth, window functions, logical subquery levels, and CASE statement nesting.
- **OpenTelemetry Instrumentation**: Distributed tracing compliant with OTel DB Semantic Conventions (`db.system`, `db.collection.name`, etc.) exporting pipeline optimization stages as span events.
- **Pre-commit Git Hook**: A pre-configured `.pre-commit-hooks.yaml` to audit SQL migration files locally before code commits.
- **Pagila Mock Datasets & Custom PostgreSQL Image**: Integrated standard database performance fixtures, Docker Postgres images with pre-loaded `pg_hint_plan` configurations, and tests.

### Changed
- **Forced Tool Calling**: Shifted Claude API query analyzer parsing from fragile regex matchers to robust Anthropic forced tool calls (`submit_query_analysis`), ensuring 100% schema validation.
- **Asynchronous SQLite Engine**: Migrated the history database from synchronous SQLAlchemy sessions to non-blocking `sqlite+aiosqlite` and `NullPool` connections, eliminating Event Loop lag.
- **Offloaded Blocking Subprocesses**: Wrapped database connector executions and shell invocations inside `asyncio.to_thread` pools to keep the FastAPI server responsive.
- **Expanded pg16/17 Planner Metrics**: Updated standard explain plan JSON extraction to include text serialization times, JIT deforming compilation logs, and planning memory usage.

### Security
- **DNS Rebinding Prevention**: Registered Starlette `TrustedHostMiddleware` whitelist constraints (`localhost`, `127.0.0.1`, `[::1]`) blocking unauthorized third-party cross-origin requests.
