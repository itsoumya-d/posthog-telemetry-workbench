from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AiGenerationEvent:
    trace_id: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    total_cost_usd: float
    is_error: bool = False


def summarize_ai_traces(events: list[AiGenerationEvent]) -> dict:
    if not events:
        return {"trace_count": 0, "total_cost_usd": 0.0, "p95_latency_ms": 0.0, "error_rate": 0.0}

    latencies = sorted(e.latency_ms for e in events)
    p95_idx = min(len(latencies) - 1, math.ceil(0.95 * (len(latencies) - 1)))
    total_cost = round(sum(e.total_cost_usd for e in events), 6)
    errors = sum(1 for e in events if e.is_error)
    return {
        "trace_count": len({e.trace_id for e in events}),
        "generation_count": len(events),
        "total_cost_usd": total_cost,
        "p95_latency_ms": round(latencies[p95_idx], 2),
        "error_rate": round(errors / len(events), 4),
    }
