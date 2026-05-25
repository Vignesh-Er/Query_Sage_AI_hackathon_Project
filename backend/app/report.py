import json
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from app.config import settings

async def generate_pdf_report(query_id: int, host: str = "localhost") -> bytes:
    """
    Spawns an async Playwright headless browser instance to capture
    the React report template page at query_id, exporting it to A4 PDF bytes.
    """
    # Navigates to the frontend print-optimized page
    # Docker containers will resolve via service naming, local will be port 3000 (Vite)
    frontend_host = "querysage-frontend" if os.environ.get("AM_I_IN_A_DOCKER_CONTAINER") else host
    report_url = f"http://{frontend_host}:3000/report/{query_id}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(
                report_url, 
                wait_until="networkidle", 
                timeout=settings.QUERYSAGE_PLAYWRIGHT_TIMEOUT
            )
            # Render PDF with margins
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"}
            )
            return pdf_bytes
        finally:
            await browser.close()

def generate_markdown_report(
    raw_sql: str,
    findings: List[Dict[str, Any]],
    plan_summary: Optional[Dict[str, Any]],
    rewrite_proposal: Optional[Dict[str, Any]]
) -> str:
    """
    Constructs a clean, self-contained Markdown document summarizing
    the analysis results.
    """
    md = []
    md.append("# QuerySage Database Analysis Report")
    md.append(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    md.append("\n---")
    
    # original SQL
    md.append("\n## Submitted Query")
    md.append("```sql")
    md.append(raw_sql.strip())
    md.append("```")
    
    # Findings Table
    md.append("\n## Detective static analysis findings")
    if findings:
        md.append("| Severity | Rule | Category | Title | Description |")
        md.append("| --- | --- | --- | --- | --- |")
        for f in findings:
            md.append(
                f"| {f.get('severity')} | {f.get('rule_id')} | {f.get('category')} | {f.get('title')} | {f.get('description')} |"
            )
    else:
        md.append("No static anti-patterns detected.")

    # Execution Plan Summary
    if plan_summary:
        md.append("\n## Prosecutor Live Execution plan analysis")
        md.append(f"- **Total Optimizer Cost**: {plan_summary.get('total_cost')}")
        md.append(f"- **Estimated Rows**: {plan_summary.get('rows_estimated')}")
        md.append(f"- **Actual Rows**: {plan_summary.get('rows_actual')}")
        md.append(f"- **Execution Time (ms)**: {plan_summary.get('execution_time_ms')}")
        md.append(f"- **Shared Page Hit Ratio**: {plan_summary.get('cache_hit_ratio') * 100:.1f}%")
        md.append(f"- **Has Sequential Scans**: {'Yes' if plan_summary.get('has_seq_scan') else 'No'}")
        md.append(f"- **Has Sort Disk Spills**: {'Yes' if plan_summary.get('has_sort_spill') else 'No'}")

    # Optimization Rewrite
    if rewrite_proposal:
        md.append("\n## Counsel Optimized Query Rewrite")
        md.append("```sql")
        md.append(rewrite_proposal.get("rewritten_query", "").strip())
        md.append("```")
        
        md.append("\n### Detailed Changes")
        changes = rewrite_proposal.get("changes", [])
        if changes:
            for chg in changes:
                md.append(f"- **[{chg.get('type')}]**: {chg.get('reason')}")
                if chg.get("orm_equivalent"):
                    md.append(f"  - *ORM Equivalent*: `{chg.get('orm_equivalent')}`")
        else:
            md.append("No query rewrites proposed.")

        # Index Recommendations
        md.append("\n### Index Recommendations")
        recs = rewrite_proposal.get("index_recommendations", [])
        if recs:
            for rec in recs:
                md.append("```sql")
                md.append(rec.get("statement"))
                md.append("```")
                md.append(f"- **Justification**: {rec.get('justification')}")
                md.append(f"- **Estimated Size**: {rec.get('index_size_bytes', 0) / 1024 / 1024:.2f} MB")
                md.append(f"- **Estimated Selectivity**: {rec.get('estimated_selectivity') * 100:.1f}%")
        else:
            md.append("No index recommendations proposed.")

        md.append(f"\n**Estimated row reduction cost delta**: {rewrite_proposal.get('estimated_row_reduction_percent')}%")
        md.append(f"**Optimization Confidence**: {rewrite_proposal.get('confidence').upper()}")
        
    return "\n".join(md)

import os
from datetime import datetime
