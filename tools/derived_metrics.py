#!/usr/bin/env python3
"""E2E normalized interactivity of one run, computed as InferenceX computes it.

python3 tools/derived_metrics.py RUN_DIR [RUN_DIR ...]

Reads RUN_DIR/client/aiperf_artifacts/profile_export.jsonl (the client's per-request export) and prints one JSON
object per run: {"run": RUN_DIR, "p75_e2e_norm_intvty": ..., "p90_e2e_norm_intvty": ..., "n": ...}.

The method follows InferenceX-app's packages/db/src/queries/derived-agentic-metrics.ts: for each request in the
profiling phase with positive request latency, TTFT, input length and output length, take end-to-end latency in
seconds divided by output tokens; take the p75 and p90 of those ratios (linear interpolation between closest
ranks); report their inverses in tokens per second per user. Standard library only.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PROFILE = Path("client") / "aiperf_artifacts" / "profile_export.jsonl"


def _num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    if isinstance(v, dict) and isinstance(v.get("value"), (int, float)) and math.isfinite(v["value"]):
        return v["value"]
    return None


def quantile(sorted_asc: list[float], q: float) -> float:
    if len(sorted_asc) == 1:
        return sorted_asc[0]
    pos = (len(sorted_asc) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return sorted_asc[lo]
    return sorted_asc[lo] + (sorted_asc[hi] - sorted_asc[lo]) * (pos - lo)


def e2e_norm_intvty(lines) -> dict:
    ratios = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        phase = (rec.get("metadata") or {}).get("benchmark_phase")
        if phase and phase != "profiling":
            continue
        m = rec.get("metrics") or {}
        rl, tt = _num(m.get("request_latency")), _num(m.get("time_to_first_token"))
        isl, osl = _num(m.get("input_sequence_length")), _num(m.get("output_sequence_length"))
        if None in (rl, tt, isl, osl) or min(rl, tt, isl, osl) <= 0:
            continue
        ratios.append(rl / 1000 / osl)
    ratios = sorted(r for r in ratios if math.isfinite(r))
    if not ratios:
        return {"p75_e2e_norm_intvty": None, "p90_e2e_norm_intvty": None, "n": 0}
    inv = lambda v: 1 / v if v > 0 else None  # noqa: E731
    return {"p75_e2e_norm_intvty": inv(quantile(ratios, 0.75)),
            "p90_e2e_norm_intvty": inv(quantile(ratios, 0.90)), "n": len(ratios)}


def main(argv: list[str]) -> int:
    for run in argv:
        with open(Path(run) / PROFILE) as f:
            print(json.dumps({"run": run, **e2e_norm_intvty(f)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
