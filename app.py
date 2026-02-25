"""
app.py — FastAPI REST API with SSE streaming endpoint.

Changes:
  - New POST /run/stream endpoint — streams agent messages in real
    time using Server-Sent Events (SSE) via StreamingResponse.
  - POST /run unchanged — still returns the full result at once.
"""

import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import config
from agent_pool import AgentPool
from logger import get_logger

log = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.validate()
    log.info("app_startup", extra={"version": "0.4.0", "port": config.PORT})
    await AgentPool.initialise()
    yield
    await AgentPool.shutdown()
    log.info("app_shutdown")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Notion MCP Agent",
    description="Natural language REST API for your Notion workspace.",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

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


# ── SSE helper ────────────────────────────────────────────────────────────────

async def _sse_generator(task: str, request_id: str):
    """
    Async generator that yields Server-Sent Event formatted strings.

    SSE format:
        data: <payload>\n\n

    The client receives one event per agent message as it is produced,
    rather than waiting for the full run to complete.
    A final `data: [DONE]` event signals the stream is finished.
    """
    try:
        async for message in AgentPool.stream_task(task):
            # Escape newlines inside the message so SSE framing stays intact
            safe = message.replace("\n", " ")
            yield f"data: {safe}\n\n"
    except Exception as exc:
        log.error("stream_task_failed", extra={"request_id": request_id, "error": str(exc)})
        yield f"data: [ERROR] {str(exc)}\n\n"
    finally:
        yield "data: [DONE]\n\n"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Notion MCP Agent is live. POST /run to submit a task."}


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "message": "Notion MCP Agent is healthy."}


@app.post("/run", response_model=RunResponse, responses={500: {"model": ErrorResponse}})
async def run(body: RunRequest, request: Request):
    """Submit a task and receive the full result once the agent finishes."""
    req_id = request.state.request_id
    log.info("run_request", extra={"request_id": req_id, "task_preview": body.task[:80]})

    try:
        result = await AgentPool.run_task(body.task)
        return {"status": "success", "result": result, "request_id": req_id}
    except Exception as exc:
        log.error("run_failed", extra={"request_id": req_id, "error": str(exc)})
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": "agent_error",
                "message": str(exc),
                "request_id": req_id,
            },
        )


@app.post(
    "/run/stream",
    summary="Stream agent messages via SSE",
    response_description="Server-Sent Events stream of agent messages",
)
async def run_stream(body: RunRequest, request: Request):
    """
    Submit a task and receive agent messages streamed in real time.

    Returns a text/event-stream response. Each SSE event contains one
    agent message. The stream ends with a `data: [DONE]` event.

    Example with curl:
        curl -X POST http://localhost:7001/run/stream \\
          -H "Content-Type: application/json" \\
          -d '{"task": "List all pages"}' \\
          --no-buffer
    """
    req_id = request.state.request_id
    log.info("stream_request", extra={"request_id": req_id, "task_preview": body.task[:80]})

    return StreamingResponse(
        _sse_generator(body.task, req_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # disables nginx buffering
            "X-Request-ID": req_id,
        },
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if config.USE_NGROK:
        from pyngrok import ngrok
        ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(config.PORT)
        log.info("ngrok_tunnel", extra={"url": str(public_url)})

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)