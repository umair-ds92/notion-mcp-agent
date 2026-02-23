"""
logger.py — Structured JSON logging for the entire application.

Every log line is a JSON object so it can be ingested directly by
log aggregators like Datadog, CloudWatch, or Loki without parsing.

Usage:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("task_received", task=task, request_id=req_id)
    log.error("agent_failed", error=str(exc), task=task)
"""

import logging
import sys
from pythonjsonlogger.jsonlogger import JsonFormatter

import config


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that emits structured JSON to stdout."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured — avoid duplicate handlers

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False

    return logger