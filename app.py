"""
app.py — Flask REST API wrapping the Notion MCP agent.

Endpoints:
  GET  /         → health check
  GET  /health   → health check
  POST /run      → run a task through the agent
"""

import asyncio

from flask import Flask, jsonify, request
from flask_cors import CORS

import config
from notion_mcp_agent import run_task

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return jsonify({"message": "Notion MCP Agent is live. Use POST /run to submit a task."}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok", "message": "Notion MCP Agent is healthy."}), 200


@app.post("/run")
def run():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Request body must be JSON."}), 400

    task = data.get("task", "").strip()
    if not task:
        return jsonify({"status": "error", "message": "Missing or empty 'task' field."}), 400

    try:
        result = asyncio.run(run_task(task))
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    config.validate()

    if config.USE_NGROK:
        from pyngrok import ngrok
        ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(config.PORT)
        print(f"Ngrok public URL: {public_url}")

    app.run(port=config.PORT, debug=False)
