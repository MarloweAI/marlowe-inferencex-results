#!/usr/bin/env python3
"""Snapshot the InferenceX public API responses the chart reads, into data/inferencex/<UTC date>/.

python3 tools/inferencex_snapshot.py [--out data/inferencex]

InferenceX's public API needs no credential. For each model in MODELS it saves benchmarks/<model>.json (the latest
result per configuration, as the dashboard fetches it), plus availability-compact.json, benchmark-presence.json and
workflow-info/<date>.json for the model's latest run date. Responses are stored unmodified. A day's directory is
never replaced, and a new one is written only when the benchmark rows changed since the latest snapshot, so the
snapshot date is the day the published results last changed. If any request fails, nothing is written and the exit
status is 1, so the site keeps the last snapshot. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://inferencex.semianalysis.com/api/v1"
# InferenceX model code -> API model name
MODELS = {"dsv41flash": "DeepSeek-V4.1-Flash"}
TIMEOUT_SECONDS = 120


class Unavailable(Exception):
    """InferenceX did not give a usable answer; the message says why."""


def get_json(path: str):
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "inference-results-snapshot/1.0",
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise Unavailable(f"{url}: {e}") from e
    if isinstance(data, dict) and "error" in data:
        raise Unavailable(f"{url}: {data['error']}")
    return data


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")) + "\n")


def fetch_all(dest: Path) -> dict[str, list]:
    """Write every response under dest; return the benchmark rows per API model name."""
    rows = {}
    for code, name in MODELS.items():
        data = get_json("/benchmarks?" + urllib.parse.urlencode({"model": name}))
        if not isinstance(data, list) or not data:
            raise Unavailable(f"benchmarks for {name}: no rows")
        rows[name] = data
        write(dest / "benchmarks" / f"{name}.json", data)
        latest = max(r["date"] for r in data if r.get("model") == code)
        write(dest / "workflow-info" / f"{latest}.json",
              get_json("/workflow-info?" + urllib.parse.urlencode({"date": latest})))
    write(dest / "availability-compact.json", get_json("/availability/compact"))
    write(dest / "benchmark-presence.json", get_json("/benchmark-presence"))
    return rows


def latest_rows(out: Path) -> dict[str, list] | None:
    days = sorted(p for p in out.glob("????-??-??") if p.is_dir())
    if not days:
        return None
    return {name: json.loads((days[-1] / "benchmarks" / f"{name}.json").read_text())
            for name in MODELS.values() if (days[-1] / "benchmarks" / f"{name}.json").exists()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "inferencex")
    a = ap.parse_args(argv)
    day = a.out / f"{datetime.now(UTC):%Y-%m-%d}"
    if day.exists():
        print(f"{day} exists; a day's snapshot is never replaced")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        try:
            rows = fetch_all(Path(tmp))
        except Unavailable as e:
            print(f"no snapshot: {e}", file=sys.stderr)
            return 1
        if latest_rows(a.out) == rows:
            print("published rows unchanged since the latest snapshot; nothing written")
            return 0
        shutil.copytree(tmp, day)
    print(f"{day}: " + ", ".join(f"{name} {len(r)} rows" for name, r in rows.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
