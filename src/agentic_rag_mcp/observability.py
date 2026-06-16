"""Structured logging + Prometheus metrics."""
import logging
import sys

import structlog
from prometheus_client import Histogram, start_http_server

from agentic_rag_mcp.config import settings

# Metrics — exposed on settings.prometheus_port
retrieval_latency = Histogram(
    "retrieval_latency_seconds",
    "End-to-end hybrid retrieval latency",
    buckets=[0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
)
retrieval_hits = Histogram(
    "retrieval_hits_returned",
    "Number of chunks returned by hybrid_search",
    buckets=[1, 3, 5, 10, 20, 50],
)
agent_steps = Histogram(
    "agent_steps_total",
    "Number of retrieval steps taken in an agentic query",
    buckets=[1, 2, 3, 4, 5, 10],
)
agent_latency = Histogram(
    "agent_query_latency_seconds",
    "End-to-end agentic query latency",
    buckets=[0.5, 1, 2, 3, 5, 10, 30],
)
agent_token_cost = Histogram(
    "agent_query_cost_usd",
    "Estimated USD cost per agentic query",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )
    try:
        start_http_server(settings.prometheus_port)
    except OSError:
        pass  # port already taken (e.g. running tests in parallel)
