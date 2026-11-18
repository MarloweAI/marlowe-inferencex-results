# Marlowe InferenceX-method results

A static copy of the InferenceX dashboard's inference chart, with Marlowe's AgentX measurements of
DeepSeek-V4.1-Flash on AMD Instinct MI355X added beside the results published by
[InferenceX (SemiAnalysis)](https://inferencex.semianalysis.com). The chart, legend, filters, tooltips and table are
InferenceX's own (`app/`, a modified copy of
[InferenceX-app](https://github.com/SemiAnalysisAI/InferenceX-app); see `app/MARLOWE_CHANGES.md`). Marlowe's points
appear as "MI355X (Marlowe SGLang, 2026-11-17 release)"; a point's details open its
recipe: the exact server and client commands and the scored summary of the charted run.

The Marlowe points were measured by Marlowe with InferenceX's agentx-harness client and scoring formulas; they are
not InferenceX CI runs, and SemiAnalysis has not reviewed or endorsed them. The notes under the chart list how the
runs differ from InferenceX's (simulated acceptance, shared nodes, request caps, host table at TP2, build).

By default the chart shows the Marlowe curve, published SGLang on MI355X and on B200, and TileRT on MI355X; every
other published series is in the legend, switched off.

Licensed under the GNU GPL v3.0 (`LICENSE`), as the InferenceX-app code it contains requires.

## Layout

| Path | What it holds |
|---|---|
| `data/marlowe/<point>.json` | One record per Marlowe point, with InferenceX's metric field names (`median_intvty`, `p90_ttft`, `tput_per_gpu`, …) plus series, status, build and server settings |
| `data/inferencex/<date>/` | InferenceX public API responses the chart reads (benchmarks per model, availability, benchmark presence, workflow info), stored unmodified; a new directory only when the published rows change |
| `recipes/<point>/` | `server.sh` and `client.sh` (exact commands, local paths replaced by `$MODEL_PATH`, `$TOKENIZER_PATH`, `$OUT`), `summary.json` (scorer result and run checks), `windows.json` (InferenceX's time windows), `aiperf_summary.json` (the client's aggregate export) |
| `app/` | The modified InferenceX-app monorepo (Next.js, bun); `app/packages/app/out/` is the exported site |
| `tools/` | `import_run.py` (raw run directory → record + recipe), `import_sailfish_run.py` (the same for a run made with sailfish), `derived_metrics.py` (E2E normalized interactivity), `inferencex_snapshot.py`, `build_static_api.py` (snapshot + Marlowe rows → static API files), `build_site.py` (checks, recipe pages, static API files) |

A point with `"status": "candidate"` is in the data and has a recipe but is not charted.

## Build and preview

```bash
python3 tools/build_site.py
cd app && bun install --frozen-lockfile && cd packages/app && bunx --bun next build
python3 -m http.server 8000 --directory app/packages/app/out
```

That builds for a domain root. The Pages workflow builds for the site's URL prefix instead
(`--site-base /marlowe-inferencex-results` and `NEXT_PUBLIC_BASE_PATH=/marlowe-inferencex-results`), taken from the
repository's Pages settings.

`build_site.py` refuses a point without a complete recipe, and any published file holding an absolute path, a
cluster node name or a non-loopback IP address.

## Adding a point

Copy the run's small files (`server_cmd.txt`, `cfg.txt`, `meta.txt`, `summary.json`, `windows.json`,
`client/benchmark_command.txt`, `client/run_info.txt`, `client/aiperf_artifacts/profile_export_aiperf.json`, and the
per-request `client/aiperf_artifacts/profile_export.jsonl`, used only to compute E2E normalized interactivity the way
InferenceX does, in `tools/derived_metrics.py`; it is not published) and run:

```bash
python3 tools/import_run.py RUN_DIR --point tp4-c32 --series release-main --image Nov-17-2026-marlowe-optimized-v0 \
  --commits sglang=SHA,sgl_amd_mono=SHA,marlowe_mix=SHA --label "max-running-requests 32"
```

## Workflows

- **InferenceX snapshot** (daily 13:30 UTC, or on demand) commits `data/inferencex/<date>/` when the published rows
  changed.
- **Pages** builds and deploys the site on changes to main, after each snapshot run, and on demand; pull requests
  build without deploying.
