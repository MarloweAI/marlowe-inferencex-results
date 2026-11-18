#!/usr/bin/env python3
"""Turn one sailfish AgentX run directory into a point: data/marlowe/<point>.json and recipes/<point>/.

python3 tools/import_sailfish_run.py RUN_DIR --scores SCORES.jsonl --point ID --series SERIES --image NAME
    [--status final|candidate] [--label TEXT] [--commits sglang=SHA,sgl_amd_mono=SHA,marlowe_mix=SHA]

RUN_DIR holds a sailfish run's small files: meta.txt, server_cmd.txt (the job's env and server command, then the
expanded engine and router commands for DP-attention servers), client/benchmark_command.txt,
client/aiperf_artifacts/profile_export_aiperf.json and client/aiperf_artifacts/inferencex_summary.json.
SCORES.jsonl has one line per client job: InferenceX's windows.py full-window score ("ours"), with the E2E
normalized interactivity computed by derived_metrics.py. Registry hosts, node addresses, local paths and job ids
are dropped; the server log is never copied. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path

from import_run import MODEL, REPOS, flag_pairs, scrub, scrub_tree, server_settings

ROOT = Path(__file__).resolve().parent.parent
SERIES = ["release-main"]
PORT = "30000"
URL = re.compile(r"http://[\d.]+:\d+")
REGISTRY = re.compile(r"[\w.-]+\.azurecr\.io/")
JOB_OUT = re.compile(r"/[^\s'\"]*/jobs/\d+/replay_1")
WEIGHTS = re.compile(r"/[^\s'\"]*/weights/[^\s'\"]*")


def scrub_sailfish(text: str) -> str:
    text = JOB_OUT.sub("$OUT/aiperf_artifacts", URL.sub(f"http://127.0.0.1:{PORT}", text))
    return REGISTRY.sub("", WEIGHTS.sub("$TOKENIZER_PATH", text))


def parse_meta(path: Path) -> dict:
    meta = {}
    for line in path.read_text().splitlines():
        m = re.match(r"(client job|server job|server image|weights|started) (\S+)(?: finished (\S+))?", line)
        if m:
            meta[m.group(1)] = m.group(2)
            if m.group(3):
                meta["finished"] = m.group(3)
    return meta


def parse_server(path: Path) -> tuple[list[str], list[str], list[str], list[str] | None]:
    """(unset vars, env assignments, engine argv, router argv or None) from server_cmd.txt."""
    lines = [ln for ln in path.read_text().splitlines() if ln and not ln.startswith("#")]
    job = shlex.split(re.sub(r'\s*>\s*"\$RUN_DIR/server\.log".*$', "", lines[0].removeprefix("$SETSID ")))
    assert job[0] == "env"
    i, unset, env = 1, [], []
    while job[i] == "-u":
        unset.append(job[i + 1])
        i += 2
    while "=" in job[i] and not job[i].startswith("-"):
        env.append(job[i])
        i += 1
    expanded = dict(re.match(r"(engine|router): (.*)", ln).groups() for ln in lines[1:])
    if not expanded:
        return unset, env, job[i:], None
    return unset, env, shlex.split(expanded["engine"]), shlex.split(expanded["router"])


def public_argv(argv: list[str]) -> list[str]:
    out = []
    for k, t in enumerate(argv):
        prev = argv[k - 1] if k else ""
        if k == 0 and t.endswith("python3"):
            t = "python3"
        elif prev == "--model-path":
            t = "$MODEL_PATH"
        elif prev == "--port" and t == "$SAI_PORT":
            t = PORT
        out.append(t)
    return out


def command_lines(argv: list[str]) -> list[str]:
    body = [" ".join('"$MODEL_PATH"' if t == "$MODEL_PATH" else shlex.quote(t) for t in g) for g in flag_pairs(argv)]
    return [f"  {b} \\" for b in body[:-1]] + [f"  {body[-1]}"]


def server_script(point: dict, unset, env, engine, router) -> str:
    lines = [
        "#!/bin/bash",
        f"# {point['model_name']} AgentX server, {point['hardware'].upper()} TP{point['decode_tp']} C{point['conc']}.",
        "# The exact command of the measured run. Only the model path and the listening port are replaced.",
        f"# MODEL_PATH: a local copy of {MODEL['hf_id']} (weight bundle sha256 {point['weights'][:12]}…).",
        f"# Image: {point['image']}" + (", commits:" if point["build"] else "."),
    ]
    lines += [f"#   {repo} {sha}" for repo, sha in point["build"].items()]
    lines += ["# The image's own environment applies too; the variables below are set on top of it.",
              "# One server per node, started fresh for this concurrency."]
    prefix = ["env " + " ".join(f"-u {u}" for u in unset) + " \\"] + [f"  {shlex.quote(e)} \\" for e in env]
    if router is None:
        lines += [""] + prefix + command_lines(public_argv(engine)) + [""]
    else:
        lines += [
            "# DP attention: one SGLang engine with --data-parallel-size 2 behind sglang_router (--dp-aware).",
            "",
            "# Engine:",
        ] + prefix + [ln if ln.endswith("\\") else ln + " &" for ln in command_lines(public_argv(engine))]
        r = public_argv(router)
        r[r.index("--port") + 1] = PORT
        router_lines = command_lines(r)
        lines += ["", "# Router, which the client connects to:", router_lines[0].lstrip()] + router_lines[1:] + [""]
    return "\n".join(lines)


def client_script(point: dict, bench_cmd: str) -> str:
    cmd = bench_cmd.split(" 2>&1")[0]
    cmd = URL.sub(f"http://127.0.0.1:{PORT}", scrub(cmd)).replace('"$SAI_MODEL_PATH"', "$TOKENIZER_PATH")
    cmd = cmd.replace('"$RUN_DIR"/replay_1', "$OUT/aiperf_artifacts")
    tokens = shlex.split(cmd)
    assert tokens[0] == "env"
    k = 1
    env = []
    while "=" in tokens[k]:
        env.append(tokens[k])
        k += 1
    body = [" ".join(t if t.startswith("$") else shlex.quote(t) for t in g) for g in flag_pairs(tokens[k:])]
    body = [b.replace("$TOKENIZER_PATH", '"$TOKENIZER_PATH"').replace("$OUT/aiperf_artifacts", '"$OUT/aiperf_artifacts"')
            for b in body]
    lines = [
        "#!/bin/bash",
        f"# InferenceX agentx-harness client for {point['model_name']}, C{point['conc']}, 3600 s replay.",
        "# The exact command of the measured run. Local paths are replaced by variables:",
        f"#   TOKENIZER_PATH: a local copy of {MODEL['hf_id']} (tokenizer files),",
        "#   OUT: the run's output directory.",
        "",
    ] + [f"export {e.split('=', 1)[0]}={shlex.quote(e.split('=', 1)[1])}" for e in env]
    lines += [""] + [f"{'  ' if i else ''}{b} \\" for i, b in enumerate(body[:-1])] + [f"  {body[-1]}", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--point", required=True)
    ap.add_argument("--series", required=True, choices=SERIES)
    ap.add_argument("--image", required=True, help="public name of the server image")
    ap.add_argument("--status", default="final", choices=["final", "candidate"])
    ap.add_argument("--label", default="", help="short config label shown on hover")
    ap.add_argument("--commits", default="", help="sglang=SHA,sgl_amd_mono=SHA,marlowe_mix=SHA (full SHAs)")
    a = ap.parse_args()
    d = a.run_dir

    meta = parse_meta(d / "meta.txt")
    score = next(json.loads(ln) for ln in a.scores.read_text().splitlines()
                 if json.loads(ln)["label"].endswith(f":{meta['client job']}"))
    f = score["ours"]
    unset, env, engine, router = parse_server(d / "server_cmd.txt")
    flags = {g[0]: (g[1] if len(g) > 1 else True) for g in flag_pairs(engine)[1:]}
    tp = int(flags["--tp"])
    conc = int(re.search(r"--concurrency (\d+)", (d / "client/benchmark_command.txt").read_text()).group(1))
    ixs = json.loads((d / "client/aiperf_artifacts/inferencex_summary.json").read_text())
    acct = ixs["request_accounting"]
    commits = dict(kv.split("=", 1) for kv in a.commits.split(",") if kv)
    assert set(commits) <= set(REPOS), commits
    digest = meta["server image"].split("@sha256:")[1]

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
        "framework_label": "SGLang" + (" + Marlowe MoE runner" if "marlowe_mix" in engine else ""),
        "precision": "fp4",
        "spec_method": "mtp",
        "disagg": False,
        "prefill_tp": tp,
        "decode_tp": tp,
        "decode_dp_attention": "--enable-dp-attention" in engine,
        "num_prefill_gpu": tp,
        "num_decode_gpu": tp,
        "offload_mode": "off",
        "benchmark_type": "agentic_traces",
        "conc": conc,
        "date": meta["finished"][:10],
        "image": f"{a.image} (sha256 {digest[:16]}…)",
        "weights": meta["weights"].split("@sha256:")[1],
        "build": {REPOS[k]: v for k, v in commits.items()},
        "server": server_settings(engine, env),
        "metrics": {
            "median_intvty": f["intv50"],
            "p90_intvty": f["intv90"],
            "median_ttft": f["ttft50"],
            "p90_ttft": f["ttft90"],
            "median_tpot": 1 / f["intv50"],
            "p90_tpot": 1 / f["intv90"],
            "tput_per_gpu": f["tpg"],
            "input_tput_per_gpu": f["tpg"] - f["otpg"],
            "output_tput_per_gpu": f["otpg"],
            "spec_algorithm": "dspark",
            "accept_len_mean": float(dict(e.split("=", 1) for e in env)["SGLANG_SIMULATE_ACC_LEN"]),
            "num_requests": f["n"],
            "errored_requests": acct["records_error_dropped"],
            "duration_seconds": 3600,
            "p75_e2e_norm_intvty": f["e2en75"],
            "p90_e2e_norm_intvty": f["e2en90"],
        },
        "client": "InferenceX agentx-harness 1.0.12, agentx preset, 3600 s",
        "scorer": "InferenceX agentx-audit-data windows.py, full window",
        "recipe": f"recipes/{a.point}/",
    }
    (ROOT / "data" / "marlowe" / f"{a.point}.json").write_text(json.dumps(point, indent=1) + "\n")

    rd = ROOT / "recipes" / a.point
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "server.sh").write_text(server_script(point, unset, env, engine, router))
    (rd / "client.sh").write_text(client_script(point, (d / "client/benchmark_command.txt").read_text()))
    run_summary = {
        "start": meta["started"],
        "end": meta["finished"],
        "gpus": tp,
        "concurrency": conc,
        "requests_profiled": acct["records_profiled"],
        "requests_errored": acct["records_error_dropped"],
        "error_categories": acct.get("error_categories", {}),
        "score_full_window": f,
        "score_keys": {
            "intv50/intv90": "interactivity P50/P90, tokens/s/user (1/TPOT)",
            "ttft50/ttft90": "time to first token P50/P90, s",
            "tpg/otpg": "total (input incl. cached + output) / output tokens/s per GPU",
            "e2en75/e2en90": "E2E normalized interactivity P75/P90, tokens/s/user",
        },
    }
    (rd / "summary.json").write_text(json.dumps(run_summary, indent=1) + "\n")
    (rd / "windows.json").write_text(json.dumps({"full": f}) + "\n")
    aip = json.loads((d / "client/aiperf_artifacts/profile_export_aiperf.json").read_text())
    aip = json.loads(scrub_sailfish(json.dumps(scrub_tree(aip))))
    (rd / "aiperf_summary.json").write_text(json.dumps(aip, indent=1) + "\n")
    print(f"{a.point}: {f['intv50']:.1f}/{f['intv90']:.1f} tok/s/user, {f['otpg']:.1f} out tok/s/GPU, "
          f"{acct['records_error_dropped']} errored -> {rd.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
