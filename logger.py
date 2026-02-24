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

class _ContextFormatter(JsonFormatter):
    """Includes all extra={} fields in the JSON output."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ContextFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False
    return logger