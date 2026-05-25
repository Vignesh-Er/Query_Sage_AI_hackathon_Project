import os
from fastapi import FastAPI
from app.database import init_db
from app.middleware import setup_cors, global_exception_handler
from app.routers import (
    connections, 
    analyze, 
    history, 
    bulk, 
    schema, 
    score, 
    natural_language, 
    report, 
    audit, 
    settings,
    lsp,
    metrics
)

# Initialize FastAPI App listening exclusively on localhost (bound at running stage)
app = FastAPI(
    title="QuerySage API",
    description="Deterministic First, AI Second Database Profiling and Optimization Engine",
    version="1.0.0"
)

# Setup CORS Policies
setup_cors(app)

# Global Exceptions Handler
app.add_exception_handler(Exception, global_exception_handler)

# Register Sub-Routers
app.include_router(connections.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(bulk.router)
app.include_router(schema.router)
app.include_router(score.router)
app.include_router(natural_language.router)
app.include_router(report.router)
app.include_router(audit.router)
app.include_router(settings.router)
app.include_router(lsp.router)
app.include_router(metrics.router)

@app.on_event("startup")
async def startup_event():
    # Initialize DB schemas and registers SQLite triggers
    await init_db()

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "querysage-api"}
