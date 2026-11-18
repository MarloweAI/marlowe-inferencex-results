#!/usr/bin/env python3
"""Turn one raw AgentX run directory into a charted point: data/marlowe/<point>.json and recipes/<point>/.

python3 tools/import_run.py RUN_DIR --point tp4-c1 --series release-main [--status final|candidate] [--label TEXT]

RUN_DIR is a copy of the run's small files (server_cmd.txt, cfg.txt, meta.txt, summary.json, windows.json,
client/benchmark_command.txt, client/run_info.txt, client/aiperf_artifacts/profile_export_aiperf.json, and the
per-request client/aiperf_artifacts/profile_export.jsonl, from which inferencex_metrics.py computes the metrics).
Local paths are replaced by variables ($MODEL_PATH, $TOKENIZER_PATH, $OUT), node names, job ids and the
image's storage path are dropped, and the server log is never copied. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path

from inferencex_metrics import request_metrics

ROOT = Path(__file__).resolve().parent.parent

MODEL = {"model": "dsv41flash", "model_name": "DeepSeek-V4.1-Flash", "hf_id": "deepseek-ai/DeepSeek-V4.1-Flash"}
CLIENT_ENV = {
    "HF_HUB_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "AIPERF_HTTP_TCP_USER_TIMEOUT": "900000",
    "AIPERF_REQUIRED_SERVER_METRIC_PREFIX": "sglang:",
}
REPOS = {
    "sglang": "MarloweAI/sglang",
    "sgl_amd_mono": "MarloweAI/sgl-amd-mono-upstream",
    "marlowe_mix": "MarloweAI/marlowe-mix",
}
# The SGLang commit an image was built from, and the marlowe-dev merge commit that carries the same tree.
SGLANG_MERGED_AS = {"1a16c3def99b": "08d1e520", "2ad94ff74d40": "ab55bd11"}

SNAPSHOT_PATH = re.compile(r"/[^\s'\"]*/snapshots/([0-9a-f]{40})")
VENV_BIN = re.compile(r"/[^\s'\"]*/bin/(agentx|aiperf)\b")
ARTIFACT_DIR = re.compile(r"/[^\s'\"]*/aiperf_artifacts")
IMAGE_PATH = re.compile(r"/[^\s'\"]*/([\w.-]+)\.sqsh")


def scrub(text: str) -> str:
    text = SNAPSHOT_PATH.sub("$TOKENIZER_PATH", text)
    text = VENV_BIN.sub(r"\1", text)
    text = ARTIFACT_DIR.sub("$OUT/aiperf_artifacts", text)
    return IMAGE_PATH.sub(r"\1", text)


def scrub_tree(o):
    if isinstance(o, dict):
        return {k: scrub_tree(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub_tree(v) for v in o]
    return scrub(o) if isinstance(o, str) else o


def read_kv(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v.strip().strip('"')
    return out


def parse_server_cmd(path: Path, commits: dict) -> tuple[dict, list[str], list[str], list[str], dict]:
    """(build record, unset vars, env assignments, pinning prefix, argv) from server_cmd.txt.

    The header names the image and, for older runs, carries the image's build record with its commits; for runs
    whose header has no record, the commits come from --commits.
    """
    header, cmd = path.read_text().splitlines()[:2]
    m = re.match(r"# image: (\S+)\s*(\{.*)?$", header)
    image = IMAGE_PATH.sub(r"\1", m.group(1))
    if m.group(2):
        commits = dict(re.findall(r'"(sglang|sgl_amd_mono|marlowe_mix)": "([0-9a-f]{40})"', m.group(2)))
    assert set(commits) == set(REPOS), f"{path}: no build record in the header; pass --commits"
    tokens = shlex.split(cmd)
    assert tokens[0] == "env"
    i, unset, env = 1, [], []
    while tokens[i] == "-u":
        unset.append(tokens[i + 1])
        i += 2
    while "=" in tokens[i] and not tokens[i].startswith("-"):
        env.append(tokens[i])
        i += 1
    j = tokens.index("python3", i)
    pin, argv = tokens[i:j], tokens[j:]
    return {"image": image, "commits": commits}, unset, env, pin, argv


def flag_pairs(argv: list[str]) -> list[list[str]]:
    """Group argv into [flag, value...] lines; the leading `python3 -m sglang.launch_server` is one group."""
    groups, cur = [], []
    for t in argv:
        if t.startswith("--") and cur:
            groups.append(cur)
            cur = []
        cur.append(t)
    groups.append(cur)
    return groups


def server_script(point: dict, build: dict, unset, env, pin, argv) -> str:
    groups = flag_pairs(argv)
    rev = None
    for g in groups:
        if g[0] == "--model-path":
            rev = Path(g[1]).name
            g[1] = "$MODEL_PATH"
    lines = [
        "#!/bin/bash",
        f"# {point['model_name']} AgentX server, {point['hardware'].upper()} TP{point['decode_tp']} C{point['conc']}"
        f" ({point['series']} series).",
        "# The exact command of the charted run. Only the model path is replaced by a variable.",
        f"# MODEL_PATH: a local copy of {MODEL['hf_id']} at revision {rev}.",
        f"# Image: {build['image']} (built on the InferenceX MI355X SGLang image), commits:",
    ]
    for k, sha in build["commits"].items():
        extra = f" (merged to marlowe-dev as {SGLANG_MERGED_AS[sha[:12]]})" if sha[:12] in SGLANG_MERGED_AS else ""
        lines.append(f"#   {REPOS[k]} {sha}{extra}")
    lines += [
        "# The image's own environment applies too; the variables below are set on top of it.",
        "# Several servers shared each node on disjoint GPUs, each pinned with taskset to its socket's cores.",
        "",
        "env " + " ".join(f"-u {u}" for u in unset) + " \\",
    ]
    lines += [f"  {shlex.quote(e)} \\" for e in env]
    lines.append("  " + " ".join(shlex.quote(p) for p in pin) + " \\")
    body = []
    for g in groups:
        body.append(" ".join('"$MODEL_PATH"' if t == "$MODEL_PATH" else shlex.quote(t) for t in g))
    lines += [f"  {b} \\" for b in body[:-1]] + [f"  {body[-1]}", ""]
    return "\n".join(lines)


def client_script(point: dict, bench_cmd: str, client_cpus: str | None) -> str:
    argv = shlex.split(scrub(bench_cmd))
    groups = flag_pairs(argv)
    lines = [
        "#!/bin/bash",
        f"# InferenceX agentx-harness client for {point['model_name']}, C{point['conc']}, 3600 s replay.",
        "# The exact command of the charted run. Local paths are replaced by variables:",
        f"#   TOKENIZER_PATH: the Hugging Face snapshot directory of {MODEL['hf_id']} (tokenizer files),",
        "#   OUT: the run's output directory.",
        "# The client ran on the server's node"
        + (f", pinned to {len(cpu_list(client_cpus))} cores of the server's socket." if client_cpus else "."),
        "",
    ]
    lines += [f"export {k}={shlex.quote(v)}" for k, v in CLIENT_ENV.items()]
    body = [" ".join(t if t.startswith("$") else shlex.quote(t) for t in g) for g in groups]
    body = [b.replace("$TOKENIZER_PATH", '"$TOKENIZER_PATH"').replace("$OUT/aiperf_artifacts", '"$OUT/aiperf_artifacts"')
            for b in body]
    lines += [""] + [f"{'  ' if k else ''}{b} \\" for k, b in enumerate(body[:-1])] + [f"  {body[-1]}", ""]
    return "\n".join(lines)


def cpu_list(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def server_settings(argv: list[str], env: list[str]) -> dict:
    flags = {g[0]: (g[1] if len(g) > 1 else True) for g in flag_pairs(argv)[1:]}
    envd = dict(e.split("=", 1) for e in env)
    return {
        "max_running_requests": int(flags["--max-running-requests"]) if "--max-running-requests" in flags else None,
        "chunked_prefill_size": int(flags["--chunked-prefill-size"]) if "--chunked-prefill-size" in flags else None,
        "prefill_decode_interval": int(flags["--prefill-decode-interval"]) if "--prefill-decode-interval" in flags else None,
        "schedule_policy": flags.get("--schedule-policy"),
        "mem_fraction_static": float(flags["--mem-fraction-static"]),
        "engram_host_table": envd.get("SGLANG_ENABLE_DSV41_ENGRAM_HOST_TABLE") == "1",
        "monokernel": "--enable-amd-monokernel" in flags,
        "simulated_accept_len": float(envd["SGLANG_SIMULATE_ACC_LEN"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--point", required=True)
    ap.add_argument("--series", required=True, choices=["release-main"])
    ap.add_argument("--status", default="final", choices=["final", "candidate"])
    ap.add_argument("--label", default="", help="short config label shown on hover")
    ap.add_argument("--image", default="", help="the image's release tag, shown in place of its file name")
    ap.add_argument("--commits", default="", help="sglang=SHA,sgl_amd_mono=SHA,marlowe_mix=SHA (full SHAs), for runs\n"
                    "whose server_cmd.txt header has no build record")
    a = ap.parse_args()
    d = a.run_dir

    cfg = read_kv(d / "cfg.txt")
    summary = json.loads((d / "summary.json").read_text())
    windows = json.loads((d / "windows.json").read_text())
    meta = dict(re.match(r"(\w+):? (.*)", line).groups() for line in (d / "meta.txt").read_text().splitlines())
    client_cpus = re.search(r"client_cpus (\S+)", meta["job"]).group(1)
    image_sha = re.search(r"sha256 ([0-9a-f]+)", meta["image"]).group(1)
    build, unset, env, pin, argv = parse_server_cmd(d / "server_cmd.txt", dict(kv.split("=", 1) for kv in a.commits.split(",") if kv))
    build["image"] = a.image or build["image"]
    assert summary["result"] == "PASS" and summary["faults"] == 0 and summary["errored_records"] == 0
    f = summary["full"]
    tp, conc = int(cfg["TP"]), int(cfg["C"])
    date = meta["end"][:10]

    point = {
        "id": a.point,
        "source": "marlowe",
        "measured_by": "Marlowe",
        "series": a.series,
        "status": a.status,
        "label": a.label,
        **{k: MODEL[k] for k in ("model", "model_name")},
        "hardware": "mi355x",
        "framework": "sglang",
        "framework_label": "SGLang + Marlowe monokernel",
        "precision": "fp4",
        "spec_method": "mtp",
        "disagg": False,
        "prefill_tp": tp,
        "decode_tp": tp,
        "decode_dp_attention": "--enable-dp-attention" in argv,
        "num_prefill_gpu": tp,
        "num_decode_gpu": tp,
        "offload_mode": "off",
        "benchmark_type": "agentic_traces",
        "conc": conc,
        "date": date,
        "image": f"{build['image']} (squashfs sha256 {image_sha}…)",
        "build": {REPOS[k]: v for k, v in build["commits"].items()},
        "server": server_settings(argv, env),
        "metrics": {
            **request_metrics(d / "client" / "aiperf_artifacts", tp),
            "spec_algorithm": "dspark",
            "accept_len_mean": summary["accept_len_mean"],
            "errored_requests": summary["errored_records"],
        },
        "client": "InferenceX agentx-harness 1.0.13, agentx preset, 3600 s",
        "scorer": "InferenceX request_metrics.py formulas, profiling phase",
        "recipe": f"recipes/{a.point}/",
    }
    (ROOT / "data" / "marlowe" / f"{a.point}.json").write_text(json.dumps(point, indent=1) + "\n")

    rd = ROOT / "recipes" / a.point
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "server.sh").write_text(server_script(point, build, unset, env, pin, argv))
    (rd / "client.sh").write_text(client_script(point, (d / "client/benchmark_command.txt").read_text(), client_cpus))
    dec = summary.get("decode", {})
    run_summary = {
        "result": summary["result"],
        "start": meta["start"],
        "end": meta["end"],
        "gpus": tp,
        "concurrency": conc,
        "server_ready_s": int(summary["server_ready"]),
        "server_fault_lines": summary["faults"],
        "errored_requests": summary["errored_records"],
        "accept_len_mean": summary["accept_len_mean"],
        "replay_checks": summary["replay_checks"],
        "decode": {k: dec.get(k) for k in ("intervals", "mono_share", "graph_share", "mono_batch_sizes")},
        "score_full_window": f,
        "score_keys": {
            "intv50/intv90": "interactivity P50/P90, tokens/s/user (1/TPOT)",
            "itl50_ms/itl90_ms": "TPOT P50/P90, ms",
            "ttft50/ttft90": "time to first token P50/P90, s",
            "tpg/otpg": "total (input incl. cached + output) / output tokens/s per GPU",
            "isl50/osl50": "median input/output tokens per request",
        },
    }
    (rd / "summary.json").write_text(json.dumps(run_summary, indent=1) + "\n")
    (rd / "windows.json").write_text(json.dumps(windows) + "\n")
    aip = json.loads((d / "client/aiperf_artifacts/profile_export_aiperf.json").read_text())
    (rd / "aiperf_summary.json").write_text(json.dumps(scrub_tree(aip), indent=1) + "\n")
    m = point["metrics"]
    print(f"{a.point}: {m['median_intvty']:.1f}/{m['p90_intvty']:.1f} tok/s/user, {m['tput_per_gpu']:.0f} tok/s/GPU -> "
          f"{rd.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
