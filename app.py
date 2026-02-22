"""
app.py — FastAPI REST API wrapping the Notion MCP agent.

Endpoints:
  GET  /         → root info
  GET  /health   → liveness check
  POST /run      → run a task through the agent (async-native)
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from agent_pool import AgentPool

# ── Lifespan: warm up the agent pool on startup ───────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.validate()
    await AgentPool.initialise()          # loads MCP tools ONCE at boot
    yield
    await AgentPool.shutdown()


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Notion MCP Agent",
    description="Natural language REST API for your Notion workspace.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000,
                      description="Plain English task to execute in Notion.")

class RunResponse(BaseModel):
    status: str
    result: str

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


@app.post("/run", response_model=RunResponse)
async def run(body: RunRequest):
    """Submit a natural language task for the agent to execute in Notion."""
    try:
        result = await AgentPool.run_task(body.task)
        return {"status": "success", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if config.USE_NGROK:
        from pyngrok import ngrok
        ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(config.PORT)
        print(f"Ngrok public URL: {public_url}")

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)