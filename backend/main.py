"""
main.py — TaxMantri FastAPI application entry point.

Start with: uvicorn main:app --reload --port 8000
(run from d:/TaxMantri/backend/)
"""
import logging
import os
import subprocess
import sys
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings

# ---------------------------------------------------------------------------
# Logging — configured before anything else
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Run Alembic migrations (auto-applied — no manual step needed)
      2. Initialize Redis connection pool  ← added by Plan 04
    Shutdown:
      1. Close Redis pool
    """
    # --- 1. Database: run Alembic migrations ---
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
    )
    if result.returncode != 0:
        logger.error("Alembic migration failed:\n%s", result.stderr)
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")
    msg = result.stdout.strip() or "No pending migrations"
    logger.info("Alembic: %s", msg)

    # --- 2. Redis: initialize connection pool (Plan 04 injects here) ---
    from backend.cache import create_redis_pool
    app.state.redis = await create_redis_pool()

    # --- 3. RAG retriever — loaded once (slow: BGE-M3 + FAISS + BM25 reconstruct) ---
    import asyncio
    from backend.agents.matcher_agent.retriever import TaxRetriever
    from mistralai import Mistral

    try:
        app.state.retriever = TaxRetriever()
        logger.info("TaxRetriever loaded successfully")
    except FileNotFoundError as exc:
        logger.warning(
            "RAG indexes missing — POST /api/query will return 503 until Phase 4 indexes are built: %s", exc
        )
        app.state.retriever = None

    # --- 4. Mistral client — singleton for HTTP connection pool reuse ---
    app.state.mistral = Mistral(api_key=settings.mistral_api_key)
    logger.info("Mistral client initialized")

    # --- 5. asyncio.Semaphore — MUST be created inside async context (not module level) ---
    app.state.rag_semaphore = asyncio.Semaphore(2)
    logger.info("RAG semaphore initialized (concurrency=2)")

    # --- 6. LangGraph agent pipeline — register resources and compile graph ---
    from backend.graph.graph import set_resources, build_graph
    set_resources(
        retriever=app.state.retriever,
        mistral_client=app.state.mistral,
        rag_semaphore=app.state.rag_semaphore,
    )
    app.state.tax_graph = build_graph()
    logger.info("TaxMantri LangGraph pipeline compiled and ready")

    logger.info("TaxMantri v%s starting up", settings.app_version)
    yield

    # --- Shutdown ---
    await app.state.redis.aclose()
    logger.info("Redis connection pool closed")
    logger.info("TaxMantri shutting down")



# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TaxMantri API",
    version=settings.app_version,
    description=(
        "GenAI-powered ITR-1 tax co-pilot for Indian salaried individuals. "
        "Compares Old vs New regime, identifies missed deductions, and guides ITR-1 filing."
    ),
    lifespan=lifespan,
    # Disable default /docs redirect on 422 — we handle validation errors ourselves
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS middleware — restricted to frontend origins from settings
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Error response helper
# ---------------------------------------------------------------------------
def _make_error_response(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    status_code: int = 500,
) -> JSONResponse:
    """Build a standard {error: {code, message, details}} response."""
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }
    return JSONResponse(status_code=status_code, content=body)


# ---------------------------------------------------------------------------
# Global exception handlers — registered BEFORE routers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Converts Pydantic / FastAPI 422 validation errors to standard format.
    Returns ALL field violations in one response.
    """
    details = []
    for error in exc.errors():
        # Build dot-notation field path, excluding the top-level 'body' loc
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append({"field": field or None, "issue": error["msg"]})
    return _make_error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
        status_code=422,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Converts FastAPI HTTPException to standard error format with semantic code.
    """
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "FILE_TOO_LARGE",
        415: "INVALID_MIME_TYPE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    return _make_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
    )


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """
    Catches explicit ValueError raises from business logic (validator.py, store.py).
    Surfaces as 422 VALIDATION_ERROR so the caller understands it's a data issue.
    """
    return _make_error_response(
        code="VALIDATION_ERROR",
        message=str(exc),
        status_code=422,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch-all for unexpected errors.
    DEBUG=true  → includes exception type & message in details (dev only).
    DEBUG=false → generic message; full traceback logged server-side only.
    """
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=True,
    )
    if settings.debug:
        details = [{"issue": f"{type(exc).__name__}: {exc}"}]
        message = "An unexpected error occurred (debug details included)"
    else:
        details = []
        message = "An unexpected error occurred"
    return _make_error_response(
        code="INTERNAL_ERROR",
        message=message,
        details=details,
        status_code=500,
    )


# ---------------------------------------------------------------------------
# Health endpoint (no auth required)
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["System"])
async def health_check() -> dict:
    """
    Returns service health status.
    Used by load balancers, deployment pipelines, and judges exploring the API.
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



# ---------------------------------------------------------------------------
# Agent routers (existing — backward-compatible)
# ---------------------------------------------------------------------------
from backend.agents.input_agent.routes import router as input_agent_router
from backend.agents.evaluator_agent.routes import router as evaluator_agent_router
from backend.agents.matcher_agent.routes import router as matcher_agent_router

app.include_router(input_agent_router)
app.include_router(evaluator_agent_router)
app.include_router(matcher_agent_router)


# ---------------------------------------------------------------------------
# POST /api/run — unified LangGraph agent pipeline endpoint
# ---------------------------------------------------------------------------
from fastapi import Body


@app.post("/api/run", tags=["agent_pipeline"])
async def run_pipeline(
    request: Request,
    payload: dict = Body(...),
) -> JSONResponse:
    """
    Run the full three-agent LangGraph pipeline:
      InputAgent → MatcherAgent → EvaluatorAgent

    Request body:
      - All UserFinancialProfile fields (manual input), OR
      - {input_method: "ocr", ocr_session_id: "...", ...override fields}

    Returns:
      200: Full TaxResult with citations and law-grounded rationale
      422: Validation errors from InputAgent
      503: RAG index not available
    """
    graph = request.app.state.tax_graph
    if graph is None:
        return _make_error_response(
            code="SERVICE_UNAVAILABLE",
            message="Agent pipeline not initialized. Please restart the server.",
            status_code=503,
        )

    input_method = payload.get("input_method", "manual")

    # Build initial state
    initial_state = {
        "raw_input": payload,
        "input_method": input_method,
        "file_path": payload.pop("file_path", None),
        "ocr_session_id": payload.get("ocr_session_id"),
        "input_errors": [],
        "errors": [],
        "should_stop": False,
        "current_agent": "input",
    }

    try:
        result_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error("Graph invocation failed: %s", exc, exc_info=True)
        return _make_error_response(
            code="PIPELINE_ERROR",
            message=f"Agent pipeline failed: {exc}",
            status_code=500,
        )

    # Handle InputAgent validation failure
    if result_state.get("should_stop"):
        errors = result_state.get("input_errors", ["Unknown validation error"])
        details = [{"field": None, "issue": e} for e in errors]
        return _make_error_response(
            code="VALIDATION_ERROR",
            message="Profile validation failed",
            details=details,
            status_code=422,
        )

    # Build success response
    tax_result = result_state.get("tax_result")
    if tax_result is None:
        return _make_error_response(
            code="PIPELINE_ERROR",
            message="Tax calculation did not produce a result",
            status_code=500,
        )

    return JSONResponse(
        status_code=200,
        content={
            "profile_id": result_state.get("profile_dict", {}).get("profile_id"),
            "tax_result": tax_result,
            "citations": result_state.get("citations", []),
            "law_context_summary": result_state.get("law_context", "")[:500],
            "sections_retrieved": len(result_state.get("retrieved_chunks", [])),
            "matcher_confidence": result_state.get("matcher_confidence", "low"),
            "pipeline_trace": {
                "input_confidence": result_state.get("input_confidence", 0.0),
                "queries_generated": len(result_state.get("tax_queries", [])),
                "chunks_retrieved": len(result_state.get("retrieved_chunks", [])),
                "citations_count": len(result_state.get("citations", [])),
            },
        },
    )
