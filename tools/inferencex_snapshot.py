#!/usr/bin/env python3
"""Snapshot InferenceX's published AgentX results for the charted models into data/inferencex/<UTC date>.json.

python3 tools/inferencex_snapshot.py [--out data/inferencex]

InferenceX's public API needs no credential. Each model in MODELS is fetched and its agentic-trace rows kept with
the fields the page charts. A day's file is never replaced, and a new file is written only when the rows differ
from the latest snapshot, so the snapshot date is the day the published data last changed. If a model cannot be
fetched, nothing is written and the exit status is 1, so the page keeps the last snapshot. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://inferencex.semianalysis.com/api/v1"
BENCHMARKS = BASE + "/benchmarks?model={model}"
SITE = "https://inferencex.semianalysis.com"
# InferenceX model code -> API model name
MODELS = {"dsv41flash": "DeepSeek-V4.1-Flash"}
VERSION = 1
TIMEOUT_SECONDS = 60

ROW_FIELDS = (
    "id", "hardware", "framework", "model", "precision", "spec_method", "disagg", "is_multinode",
    "prefill_tp", "prefill_ep", "prefill_dp_attention", "prefill_num_workers",
    "decode_tp", "decode_ep", "decode_dp_attention", "decode_num_workers",
    "num_prefill_gpu", "num_decode_gpu", "benchmark_type", "offload_mode", "conc", "image", "date", "run_url",
)
METRIC_FIELDS = (
    "median_intvty", "p90_intvty", "median_ttft", "p90_ttft", "median_tpot", "p90_tpot",
    "median_e2el", "p90_e2el", "tput_per_gpu", "input_tput_per_gpu", "output_tput_per_gpu",
    "spec_algorithm", "duration_seconds",
)


class Unavailable(Exception):
    """InferenceX did not give a usable answer; the message says why."""


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "inference-results-snapshot/1.0",
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise Unavailable(f"{url}: {e}") from e
    if isinstance(data, dict) and "error" in data:
        raise Unavailable(f"{url}: {data['error']}")
    if not isinstance(data, list):
        raise Unavailable(f"{url}: expected a list of rows")
    return data


def keep(x: dict) -> dict:
    row = {k: x.get(k) for k in ROW_FIELDS}
    row["metrics"] = {k: x["metrics"].get(k) for k in METRIC_FIELDS}
    return row


def build_record(fetch, fetched_at: str) -> dict:
    models = {}
    for code, api_model in MODELS.items():
        rows = [keep(x) for x in fetch(api_model)
                if x.get("model") == code and x.get("benchmark_type") == "agentic_traces"]
        rows.sort(key=lambda r: (r["hardware"], r["framework"], r["num_decode_gpu"], r["conc"], r["id"]))
        models[code] = {"api_model": api_model, "rows": rows}
    return {"version": VERSION, "fetched_at": fetched_at, "source": BASE, "site": SITE, "models": models}


def dump(record: dict) -> str:
    """JSON with one row per line, so a day's diff shows which published points changed."""
    head = {k: v for k, v in record.items() if k != "models"}
    parts = [json.dumps(head)[:-1] + ', "models": {']
    for i, (code, m) in enumerate(record["models"].items()):
        rows = ",\n".join("   " + json.dumps(r, separators=(",", ":")) for r in m["rows"])
        sep = "," if i < len(record["models"]) - 1 else ""
        parts.append(f' {json.dumps(code)}: {{"api_model": {json.dumps(m["api_model"])}, "rows": [\n{rows}\n ]}}{sep}')
    return "\n".join(parts) + "\n}}\n"


def latest(out: Path) -> dict | None:
    files = sorted(out.glob("????-??-??.json"))
    return json.loads(files[-1].read_text()) if files else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "inferencex")
    a = ap.parse_args(argv)
    now = datetime.now(UTC)
    path = a.out / f"{now:%Y-%m-%d}.json"
    if path.exists():
        print(f"{path} exists; a day's snapshot is never replaced")
        return 0
    try:
        record = build_record(
            lambda name: get_json(BENCHMARKS.format(model=urllib.parse.quote(name))),
            fetched_at=now.isoformat(timespec="seconds"),
        )
    except Unavailable as e:
        print(f"no snapshot: {e}", file=sys.stderr)
        return 1
    prev = latest(a.out)
    if prev and prev["models"] == record["models"]:
        print(f"published rows unchanged since {prev['fetched_at'][:10]}; nothing written")
        return 0
    a.out.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(record))
    rows = sum(len(m["rows"]) for m in record["models"].values())
    print(f"{path}: {len(record['models'])} models, {rows} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
