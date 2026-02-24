"""
app.py — FastAPI REST API with structured logging and consistent error responses.

Changes:
  - Every request logs a unique request_id for traceability.
  - Consistent error payload: {"status": "error", "code": "...", "message": "..."}.
  - Startup and shutdown events are logged.
  - Exception handler added for unhandled 500s — never leaks raw tracebacks.
"""

import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import config
from agent_pool import AgentPool
from logger import get_logger

log = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.validate()
    log.info("app_startup", version="0.3.0", port=config.PORT)
    await AgentPool.initialise()
    yield
    await AgentPool.shutdown()
    log.info("app_shutdown")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Notion MCP Agent",
    description="Natural language REST API for your Notion workspace.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler — no raw tracebacks to clients ──────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    log.error("unhandled_exception", extra={
        "request_id": req_id,
        "path": request.url.path,
        "error": str(exc),
    })
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "internal_server_error",
            "message": "An unexpected error occurred. Check server logs.",
            "request_id": req_id,
        },
    )


# ── Request ID middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    log.info("request_received", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    })
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    log.info("request_complete", extra={
        "request_id": request_id,
        "status_code": response.status_code,
    })
    return response


# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000,
                      description="Plain English task to execute in Notion.")

class RunResponse(BaseModel):
    status: str
    result: str
    request_id: str

class ErrorResponse(BaseModel):
    status: str
    code: str
    message: str
    request_id: str

class HealthResponse(BaseModel):
    status: str
    message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Notion MCP Agent is live. POST /run to submit a task."}


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "message": "Notion MCP Agent is healthy."}


@app.post("/run", response_model=RunResponse, responses={500: {"model": ErrorResponse}})
async def run(body: RunRequest, request: Request):
    req_id = request.state.request_id
    log.info("run_request", extra={"request_id": req_id, "task_preview": body.task[:80]})

    try:
        result = await AgentPool.run_task(body.task)
        return {"status": "success", "result": result, "request_id": req_id}
    except Exception as exc:
        log.error("run_failed", extra={"request_id": req_id, "error": str(exc)})
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "agent_error",
                "message": str(exc),
                "request_id": req_id,
            },
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if config.USE_NGROK:
        from pyngrok import ngrok
        ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(config.PORT)
        log.info("ngrok_tunnel", url=str(public_url))

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)