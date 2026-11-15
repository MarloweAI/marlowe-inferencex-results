#!/usr/bin/env python3
"""Write the static API files the site reads: the latest InferenceX snapshot plus the Marlowe points as rows.

python3 tools/build_static_api.py --out app/packages/app/public/data/api [--site-base /]

The app's API client (app/packages/app/src/lib/api/static-api.ts) maps each API request to a file here. Each
Marlowe point becomes a benchmark row with InferenceX's row shape: hardware mi355x, framework `marlowe` (main
series) or `marlowe-intvty` (interactivity-leaning), the measured metrics, and run_url pointing at its recipe page.
Metrics we did not measure (power, cache hit rates, full-response percentiles) are left out. Candidate points are
not written. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK = {"main": "marlowe", "interactivity-leaning": "marlowe-intvty"}
# Marlowe row ids sit far above InferenceX's so they never collide.
ID_BASE = 90_000_000
SNAPSHOT_DATE_TS = "app/packages/app/src/components/marlowe/snapshot-date.ts"


def latest_snapshot() -> Path:
    days = sorted(p for p in (ROOT / "data" / "inferencex").iterdir() if p.is_dir())
    if not days:
        sys.exit("no InferenceX snapshot under data/inferencex/")
    return days[-1]


def restrict_availability(av: dict, codes: set[str]) -> dict:
    """Keep the snapshot's models only, each available on its latest run date only.

    The snapshot holds the latest result per configuration, so the run-date picker offers that date alone.
    """
    lines = [ln for ln in av["lines"] if av["models"][ln[0]] in codes]
    last: dict[int, int] = {}
    for ln in lines:
        end, d = 0, None
        runs = ln[9]
        for k in range(0, len(runs), 2):
            start = end + runs[k]
            end = start + runs[k + 1]
            d = end - 1
        last[ln[0]] = max(last.get(ln[0], -1), d)
    out = dict(av)
    out["lines"] = [ln[:9] + [[last[ln[0]], 1]] for ln in lines]
    return out


def marlowe_row(i: int, p: dict, site_base: str) -> dict:
    m = p["metrics"]
    tp = p["decode_tp"]
    # The app draws the latest curve run per series, so a series' points share one run id.
    run_id = str(ID_BASE + 100_000 + list(FRAMEWORK).index(p["series"]))
    run_started = f"{p['date']} 00:00:00+00"
    metrics = {
        "median_intvty": m["median_intvty"],
        "p90_intvty": m["p90_intvty"],
        "mean_intvty": None,
        "median_ttft": m["median_ttft"],
        "p90_ttft": m["p90_ttft"],
        "median_tpot": m["median_tpot"],
        "p90_tpot": m["p90_tpot"],
        "median_itl": m["median_tpot"],
        "p90_itl": m["p90_tpot"],
        "tput_per_gpu": m["tput_per_gpu"],
        "input_tput_per_gpu": m["input_tput_per_gpu"],
        "output_tput_per_gpu": m["output_tput_per_gpu"],
        "total_tput_tps": m["tput_per_gpu"] * tp,
        "input_tput_tps": m["input_tput_per_gpu"] * tp,
        "output_tput_tps": m["output_tput_per_gpu"] * tp,
        "duration_seconds": m["duration_seconds"],
        "total_requests_completed": m["num_requests"],
        "spec_algorithm": m["spec_algorithm"],
        "spec_draft_model": "native",
        "offload_mode": "off",
        "kv_offloading": "none",
        "pp": 1,
        "dp": 1,
        "dcp_size": 1,
        "pcp_size": 1,
        "power_valid": 0,
    }
    return {
        "id": str(ID_BASE + i),
        "hardware": p["hardware"],
        "framework": FRAMEWORK[p["series"]],
        "model": p["model"],
        "precision": p["precision"],
        "spec_method": p["spec_method"],
        "disagg": False,
        "is_multinode": False,
        "prefill_tp": tp,
        "prefill_ep": 1,
        "prefill_dp_attention": False,
        "prefill_num_workers": 0,
        "decode_tp": tp,
        "decode_ep": 1,
        "decode_dp_attention": False,
        "decode_num_workers": 0,
        "num_prefill_gpu": tp,
        "num_decode_gpu": tp,
        "benchmark_type": "agentic_traces",
        "offload_mode": "off",
        "isl": None,
        "osl": None,
        "conc": p["conc"],
        "image": p["image"].split(" ")[0],
        "recipe_fingerprint": None,
        "workers": None,
        "power_invalid_reasons": None,
        "power_audit": None,
        "metrics": metrics,
        "date": p["date"],
        "workflow_run_id": run_id,
        "run_started_at": run_started,
        "run_url": f"{site_base.rstrip('/')}/{p['recipe']}",
        "curve_date": p["date"],
        "curve_workflow_run_id": run_id,
        "curve_run_started_at": run_started,
        "marlowe": {"point": p["id"], "series": p["series"], "label": p["label"]},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--site-base", default="", help="URL path prefix of the site (empty for a root site)")
    a = ap.parse_args(argv)
    snap = latest_snapshot()
    points = [json.loads(f.read_text()) for f in sorted((ROOT / "data" / "marlowe").glob("*.json"))]
    points = [p for p in points if p["status"] == "final"]

    if a.out.exists():
        shutil.rmtree(a.out)
    shutil.copytree(snap, a.out)
    av = a.out / "availability-compact.json"
    av.write_text(json.dumps(restrict_availability(json.loads(av.read_text()), {p["model"] for p in points}),
                             separators=(",", ":")))
    by_model: dict[str, list[dict]] = {}
    for i, p in enumerate(points):
        by_model.setdefault(p["model_name"], []).append(marlowe_row(i, p, a.site_base))
    for model, rows in by_model.items():
        f = a.out / "benchmarks" / f"{model}.json"
        published = json.loads(f.read_text()) if f.exists() else []
        f.write_text(json.dumps(published + rows, separators=(",", ":")))
    (ROOT / SNAPSHOT_DATE_TS).write_text(
        "// Written by tools/build_static_api.py: the date of the InferenceX snapshot the site was built from.\n"
        f"export const MARLOWE_SNAPSHOT_DATE = '{snap.name}';\n")
    print(f"{a.out}: snapshot {snap.name}, {len(points)} Marlowe rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
