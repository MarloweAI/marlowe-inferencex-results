#!/usr/bin/env python3
"""Prepare the app's public files: one page per recipe and the static API files the chart reads.

python3 tools/build_site.py [--public app/packages/app/public] [--site-base PREFIX]

Writes <public>/recipes/<point>/ (recipe page plus its files) and <public>/data/api/ (tools/build_static_api.py).
Then `bun run build` in app/ exports the site to app/packages/app/out/. The step fails if a Marlowe point has no
complete recipe, or if a published file carries an absolute path, a cluster node name or a non-loopback IP address.
Standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

import build_static_api

ROOT = Path(__file__).resolve().parent.parent
RECIPE_FILES = ("server.sh", "client.sh", "summary.json", "windows.json", "aiperf_summary.json")
LEAKS = (
    ("absolute path", re.compile(r"(?<![\w$.:/!])/(?!dev/null\b)[A-Za-z][\w.-]*/[\w./-]*")),
    ("node name", re.compile(r"\b[a-z]+-mi\d{3}x-\d+\b")),
    ("IP address", re.compile(r"\b(?!127\.0\.0\.1\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
)


# Legend names of the series, as the chart shows them.
SERIES_LABEL = {
    "main": "Marlowe SGLang",
    "interactivity-leaning": "Marlowe SGLang, interactivity-leaning",
    "release-main": "Marlowe SGLang, 2026-11-17",
    "release-interactivity-leaning": "Marlowe SGLang, interactivity-leaning, 2026-11-17",
}

def leaks(path: Path) -> list[str]:
    text = path.read_text()
    found = []
    for what, rx in LEAKS:
        for m in rx.finditer(text):
            if what == "absolute path" and text[max(0, m.start() - 4):m.start()].endswith(("http", "https")):
                continue
            found.append(f"{path.relative_to(ROOT)}: {what} {m.group(0)!r}")
    return found


def check(points: list[dict]) -> list[str]:
    errors = []
    for p in points:
        rd = ROOT / p["recipe"]
        errors += [f"{p['id']}: recipe lacks {f}" for f in RECIPE_FILES if not (rd / f).is_file()]
    for f in sorted((ROOT / "recipes").rglob("*")) + sorted((ROOT / "data" / "marlowe").glob("*.json")):
        if f.is_file():
            errors += leaks(f)
    return errors


def fmt(v, digits=1):
    return f"{v:,.{digits}f}" if isinstance(v, (int, float)) else "–"


def recipe_page(p: dict, files: dict[str, str]) -> str:
    m = p["metrics"]
    s = p["server"]
    title = f"{p['model_name']} · MI355X TP{p['decode_tp']} C{p['conc']}"
    rows = [
        ("Series", SERIES_LABEL[p["series"]] + (" (candidate, not charted yet)" if p["status"] != "final" else "")),
        ("Configuration", p["label"]),
        ("Interactivity P50 / P90, tok/s/user", f"{fmt(m['median_intvty'])} / {fmt(m['p90_intvty'])}"),
        ("TTFT P50 / P90, s", f"{fmt(m['median_ttft'], 3)} / {fmt(m['p90_ttft'], 3)}"),
        ("TPOT P50 / P90, ms", f"{fmt(m['median_tpot'] * 1e3, 3)} / {fmt(m['p90_tpot'] * 1e3, 3)}"),
        ("Throughput, tok/s/GPU (input incl. cached + output)", fmt(m["tput_per_gpu"], 0)),
        ("Output throughput, tok/s/GPU", fmt(m["output_tput_per_gpu"], 1)),
        ("Requests scored", f"{m['num_requests']:,} over {m['duration_seconds']} s"),
        ("Mean accept length (simulated 3.51)", fmt(m["accept_len_mean"], 3)),
        ("GPUs", f"{p['num_decode_gpu']} × MI355X, TP{p['decode_tp']}, no DP attention"),
        ("Request cap (max-running-requests)", s["max_running_requests"] or "SGLang default"),
        ("Engram host table", "on" if s["engram_host_table"] else "off"),
        ("Date", p["date"]),
        ("Image", p["image"]),
    ] + [(f"Build: {repo}", sha) for repo, sha in p["build"].items()]
    table = "\n".join(f"<tr><th scope=\"row\">{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
                      for k, v in rows)
    pre = "\n".join(
        f"<h2>{html.escape(name)}</h2>\n<p class=\"fileref\"><a href=\"{name}\">{name}</a></p>\n"
        f"<pre><code>{html.escape(files[name])}</code></pre>"
        for name in ("server.sh", "client.sh")
    )
    raw = " · ".join(f"<a href=\"{n}\">{n}</a>" for n in RECIPE_FILES[2:])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipe: {html.escape(title)}</title>
<link rel="stylesheet" href="../recipe.css">
</head>
<body>
<main class="page recipe">
<p class="crumb"><a href="../../">← Back to the chart</a></p>
<p class="brand">Marlowe</p>
<h1>{html.escape(title)}</h1>
<p class="lede">Measured by Marlowe with InferenceX's agentx-harness client (1.0.13, <code>agentx</code> preset,
3600 s) and InferenceX's scoring formulas. Not an InferenceX CI run.</p>
<div class="tablewrap"><table class="kv">{table}</table></div>
{pre}
<h2>Scores and client output</h2>
<p>{raw}: the scorer's full-window result and run checks, InferenceX's prefix and sliding windows, and the
client's own aggregate export. Local paths are replaced by variables; server logs are not published.</p>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--public", type=Path, default=ROOT / "app" / "packages" / "app" / "public")
    ap.add_argument("--site-base", default="", help="URL path prefix of the site (empty for a root site)")
    a = ap.parse_args(argv)
    points = [json.loads(f.read_text()) for f in sorted((ROOT / "data" / "marlowe").glob("*.json"))]
    errors = check(points)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    out = a.public / "recipes"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "recipe.css", out / "recipe.css")
    for p in points:
        src, dst = ROOT / p["recipe"], a.public / p["recipe"]
        shutil.copytree(src, dst)
        files = {n: (src / n).read_text() for n in RECIPE_FILES}
        (dst / "index.html").write_text(recipe_page(p, files))
    print(f"{out}: {len(points)} recipe pages")
    return build_static_api.main(["--out", str(a.public / "data" / "api"), "--site-base", a.site_base])


if __name__ == "__main__":
    sys.exit(main())
