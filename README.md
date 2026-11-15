# Marlowe InferenceX-method results

A static site that charts Marlowe's AgentX measurements of DeepSeek-V4.1-Flash on AMD Instinct MI355X beside the
results published by [InferenceX (SemiAnalysis)](https://inferencex.semianalysis.com), with selectable axes,
P50/P90, and hardware, framework and source filters. Every Marlowe point links to its recipe: the exact server and
client commands and the scored summary of the charted run.

The Marlowe points were measured by Marlowe with InferenceX's agentx-harness client and scoring formulas; they are
not InferenceX CI runs, and SemiAnalysis has not reviewed or endorsed them. The page's footnotes list how the runs
differ from InferenceX's (simulated acceptance, shared nodes, request caps, host table at TP2, builds).

## Layout

| Path | What it holds |
|---|---|
| `data/marlowe/<point>.json` | One record per Marlowe point, with InferenceX's metric field names (`median_intvty`, `p90_ttft`, `tput_per_gpu`, …) plus series, status, build and server settings |
| `data/inferencex/<date>.json` | Snapshots of InferenceX's public API, one row per published point; a new file only when the published rows change |
| `recipes/<point>/` | `server.sh` and `client.sh` (exact commands, local paths replaced by `$MODEL_PATH`, `$TOKENIZER_PATH`, `$OUT`), `summary.json` (scorer result and run checks), `windows.json` (InferenceX's time windows), `aiperf_summary.json` (the client's aggregate export) |
| `site/` | The page: `index.html`, `app.js`, `style.css` (ECharts 5.5.0 from cdnjs) |
| `tools/` | `import_run.py` (raw run directory → record + recipe), `inferencex_snapshot.py`, `build_site.py` |

A point with `"status": "candidate"` is listed in the table but not charted. The main-series TP2 C64 point has two
candidates (prefill-decode interval 32 and 34); when one is chosen, set its status to `final` and delete the other's
record and recipe.

## Build and preview

```bash
python3 tools/build_site.py
python3 -m http.server 8000 --directory _site
```

The build refuses a point without a complete recipe, and any published file holding an absolute path, a cluster
node name or a non-loopback IP address.

## Adding a point

Copy the run's small files (`server_cmd.txt`, `cfg.txt`, `meta.txt`, `summary.json`, `windows.json`,
`client/benchmark_command.txt`, `client/run_info.txt`, `client/aiperf_artifacts/profile_export_aiperf.json`) and run:

```bash
python3 tools/import_run.py RUN_DIR --point tp4-c32 --series main --label "max-running-requests 32"
```

## Workflows

- **InferenceX snapshot** (daily 13:30 UTC, or on demand) commits `data/inferencex/<date>.json` when the published
  rows changed.
- **Pages** builds and deploys the site on changes to main, after each snapshot run, and on demand; pull requests
  build without deploying.
