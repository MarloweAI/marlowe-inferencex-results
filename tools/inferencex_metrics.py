#!/usr/bin/env python3
"""A run's published-row metrics, computed the way InferenceX computes them for its AgentX rows.

python3 tools/inferencex_metrics.py RUN_ARTIFACT_DIR GPUS

RUN_ARTIFACT_DIR holds the client's profile_export.jsonl (and profile_export_aiperf.json for the theoretical cache hit
rate). Prints the metrics as one JSON object with InferenceX's row field names.

The formulas follow InferenceX's inferencex-e2e/infx/results/agentic/request_metrics.py and common.py
(github.com/SemiAnalysisAI/InferenceX): profiling-phase records without an error; latency percentiles with linear
interpolation between closest ranks; interactivity as 1 / the ITL percentile; E2E normalized interactivity as
1 / the percentile of request latency / output tokens; throughput over the span from the first request start to the
last request end; per-GPU throughput divided by the GPU count; floats rounded to 5 decimals. The p50 statistic is
stored as `median_*`, as InferenceX's rows store it. Standard library only.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from bisect import bisect_left
from pathlib import Path

STATS = ("mean", "p50", "p75", "p90", "p95")


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    return s[f] if f + 1 >= len(s) else s[f] + (k - f) * (s[f + 1] - s[f])


def stats(prefix: str, values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    out = {f"mean_{prefix}": statistics.mean(values)}
    out |= {f"p{p}_{prefix}": percentile(values, p) for p in (50, 75, 90, 95)}
    out[f"std_{prefix}"] = statistics.pstdev(values) if len(values) > 1 else 0.0
    return out


def inverse_stats(latency: dict[str, float], per_request: list[float], src: str, dst: str) -> dict[str, float]:
    """Interactivity from a latency's statistics: 1 / the latency percentile, so P90 is the slow tail."""
    out = {f"{k}_{dst}": 1 / latency[f"{k}_{src}"] for k in STATS if latency.get(f"{k}_{src}", 0) > 0}
    rates = [1 / v for v in per_request if v > 0]
    if rates:
        out[f"std_{dst}"] = statistics.pstdev(rates) if len(rates) > 1 else 0.0
    return out


def value(record: dict, key: str) -> float | None:
    v = record.get("metrics", {}).get(key)
    v = v.get("value") if isinstance(v, dict) else v
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) else None


def seconds(records: list[dict], key: str) -> list[float]:
    return [v / 1000 for r in records if (v := value(r, key)) is not None and v > 0]


def profiled_records(jsonl: Path) -> list[dict]:
    records = []
    with open(jsonl) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            phase = r.get("metadata", {}).get("benchmark_phase")
            if r.get("error") or (phase is not None and phase != "profiling"):
                continue
            records.append(r)
    return records


def qps(records: list[dict]) -> dict[str, float]:
    ends = sorted(int(r["metadata"]["request_end_ns"]) / 1e9 for r in records if r["metadata"].get("request_end_ns"))
    if len(ends) < 2 or ends[-1] <= ends[0]:
        return {}
    counts, t = [], ends[0]
    while t + 1.0 <= ends[-1]:
        counts.append(float(bisect_left(ends, t + 1.0) - bisect_left(ends, t)))
        t += 1.0
    return stats("qps", counts) if counts else {"mean_qps": len(ends) / (ends[-1] - ends[0])}


def request_metrics(artifact_dir: Path, gpus: int) -> dict[str, float]:
    records = profiled_records(artifact_dir / "profile_export.jsonl")
    itls = seconds(records, "inter_token_latency")
    full_itls = seconds(records, "full_response_inter_token_latency")
    e2el_per_osl = [lat / 1000 / osl for r in records
                    if (lat := value(r, "request_latency")) and (osl := value(r, "output_sequence_length"))
                    and lat > 0 and osl > 0]
    m: dict[str, float] = {}
    m |= qps(records)
    m |= stats("ttft", seconds(records, "time_to_first_token"))
    m |= stats("e2el", seconds(records, "request_latency"))
    m |= (itl := stats("itl", itls))
    m |= stats("tpot", itls)
    m |= inverse_stats(itl, itls, "itl", "intvty")
    m |= inverse_stats(stats("e2el_per_osl", e2el_per_osl), e2el_per_osl, "e2el_per_osl", "e2e_norm_intvty")
    m |= (full := stats("full_response_itl", full_itls))
    m |= inverse_stats(full, full_itls, "full_response_itl", "full_response_intvty")

    isl = [int(v) for r in records if (v := value(r, "input_sequence_length")) is not None]
    osl = [int(v) for r in records if (v := value(r, "output_sequence_length")) is not None]
    m |= stats("input_tokens", isl)
    m |= stats("output_tokens_actual", osl)

    starts = [int(r["metadata"]["request_start_ns"]) for r in records if r["metadata"].get("request_start_ns")]
    ends = [int(r["metadata"]["request_end_ns"]) for r in records if r["metadata"].get("request_end_ns")]
    duration = (max(ends) - min(starts)) / 1e9
    m |= {
        "input_tput_tps": sum(isl) / duration,
        "output_tput_tps": sum(osl) / duration,
        "total_tput_tps": (sum(isl) + sum(osl)) / duration,
        "duration_seconds": duration,
        "total_requests_completed": len(records),
        "total_prompt_tokens": sum(isl),
        "total_generation_tokens": sum(osl),
    }
    m |= {"tput_per_gpu": m["total_tput_tps"] / gpus, "input_tput_per_gpu": m["input_tput_tps"] / gpus,
          "output_tput_per_gpu": m["output_tput_tps"] / gpus}

    aggregate = artifact_dir / "profile_export_aiperf.json"
    hit = json.loads(aggregate.read_text()).get("theoretical_prefix_cache_hit") if aggregate.exists() else None
    if isinstance(hit, dict) and hit.get("count"):
        m["theoretical_cache_hit_rate"] = hit["sum"] / hit["count"]

    return {k.replace("p50_", "median_", 1) if k.startswith("p50_") else k: round(v, 5) for k, v in m.items()}


if __name__ == "__main__":
    print(json.dumps(request_metrics(Path(sys.argv[1]), int(sys.argv[2])), indent=1))
