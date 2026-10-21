"""Run Claude (headless Claude Code) as the experimenter on hidden-learner instances.

Usage:
  python harness/run_claude.py check3      # leakage check, 1 instance
  python harness/run_claude.py pilot       # pilot instances
For each instance: sandbox outside the repo with only prompt.md and query.py; environment server in
this process; results/<instance_id>.json and results/transcripts/<instance_id>.jsonl.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import scoring, server
from env.config import load_config
from env.environment import Environment
from harness import baselines

RESULTS = REPO / "results"
ALLOWED = re.compile(r"^python3 query\.py(\s|$)")
FORBIDDEN_IN_RESULTS = ["part_based", "model-id-env", "mean_cost", "label_of", "def ", "learners.py"]


def make_sandbox(root, instance_id, port, prompt):
    box = Path(root) / instance_id
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    client = (REPO / "harness" / "query.py").read_text().replace("PORT = None  # set by the harness", f"PORT = {port}")
    (box / "query.py").write_text(client)
    (box / "prompt.md").write_text(prompt)
    return box


def claude_command(prompt, cr):
    return ["claude", "-p", prompt, "--model", cr["model"],
            "--tools", "Bash", "--allowedTools", "Bash(python3 query.py *)",
            "--permission-mode", "dontAsk", "--safe-mode", "--strict-mcp-config",
            "--no-session-persistence", "--output-format", "stream-json", "--verbose",
            "--max-turns", str(cr["max_turns"])]


def audit(events):
    """Every tool call, whether it was a query.py command, whether it errored, and forbidden strings in results."""
    calls, results = {}, {}
    for e in events:
        for block in (e.get("message") or {}).get("content", []) if isinstance((e.get("message") or {}).get("content"), list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = {"tool": block["name"], "input": block.get("input", {})}
            elif block.get("type") == "tool_result":
                content = block.get("content")
                text = content if isinstance(content, str) else json.dumps(content)
                results[block["tool_use_id"]] = {"is_error": bool(block.get("is_error")), "text": text}
    rows = []
    for cid, c in calls.items():
        cmd = c["input"].get("command", "") if c["tool"] == "Bash" else ""
        r = results.get(cid, {"is_error": None, "text": ""})
        rows.append({"tool": c["tool"], "command": cmd or json.dumps(c["input"])[:300],
                     "allowed_form": bool(c["tool"] == "Bash" and ALLOWED.match(cmd)
                                          and not re.search(r"[;&|`$<>]", cmd.split("submit", 1)[0])),
                     "is_error": r["is_error"],
                     "forbidden_strings": [f for f in FORBIDDEN_IN_RESULTS if f in r["text"]]})
    leaks = [r for r in rows if (not r["allowed_form"] and r["is_error"] is False) or r["forbidden_strings"]]
    return {"n_tool_calls": len(rows), "n_other_attempts": sum(not r["allowed_form"] for r in rows),
            "leaks": leaks, "pass": not leaks, "calls": rows}


def run_instance(instance_id, learner, seed, cfg, prompt_template, kind):
    cr = cfg["claude_runs"]
    env = Environment(learner, seed, cfg)
    srv, port = server.start(env)
    prompt = prompt_template.replace("{budget}", str(env.budget))
    box = make_sandbox(cr["sandbox_root"], instance_id, port, prompt)
    t0 = time.time()
    try:
        proc = subprocess.run(claude_command(prompt, cr), cwd=box, capture_output=True, text=True,
                              timeout=cr["timeout_s"])
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        stdout, stderr, code = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout", None
    finally:
        srv.shutdown()
    elapsed = time.time() - t0

    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    (RESULTS / "transcripts").mkdir(parents=True, exist_ok=True)
    (RESULTS / "transcripts" / f"{instance_id}.jsonl").write_text(stdout)
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    claude_meta = {"returncode": code, "stderr_tail": stderr[-2000:], "elapsed_s": elapsed,
                   "num_turns": final.get("num_turns"), "total_cost_usd": final.get("total_cost_usd"),
                   "subtype": final.get("subtype"), "final_text": final.get("result"),
                   "model_usage": final.get("modelUsage"), "command": claude_command("<prompt>", cr)}

    scores = scoring.score(env)
    base = {}
    for name, f in [("random", baselines.random_experimenter), ("oracle", baselines.oracle_experimenter)]:
        benv = Environment(learner, seed, cfg)
        f(benv, seed + 1)
        base[name] = scoring.score(benv)
    record = scoring.instance_record(env, scores, {"instance_id": instance_id, "kind": kind, "prompt": prompt,
                                                    "claude": claude_meta, "audit": audit(events),
                                                    "baselines_same_instance": base})
    with open(RESULTS / f"{instance_id}.json", "w") as f:
        json.dump(record, f, indent=1, default=str)
    return record


def summary_line(r):
    v = r["verdict"] or {}
    return (f"{r['instance_id']}: learner {r['learner']}  verdict {v.get('verdict')} ({v.get('confidence')})  "
            f"scores {r['scores']}  random {r['baselines_same_instance']['random']}  "
            f"oracle {r['baselines_same_instance']['oracle']}  audit pass {r['audit']['pass']} "
            f"(other attempts {r['audit']['n_other_attempts']})  turns {r['claude']['num_turns']}  "
            f"{r['claude']['elapsed_s']:.0f}s")


def main(mode):
    cfg = load_config()
    cr = cfg["claude_runs"]
    if mode == "check3":
        template = (REPO / "harness" / "prompt_check3.md").read_text()
        r = run_instance("check3-000", "holistic" if cr["check3"]["seed"] % 2 else "part_based",
                         cr["check3"]["seed"], cfg, template, "check3")
        print(summary_line(r))
        for c in r["audit"]["calls"]:
            print("  ", "OK " if c["allowed_form"] else "-- ", "error" if c["is_error"] else "ran  ", c["command"][:150])
    elif mode == "pilot":
        template = (REPO / "harness" / "prompt.md").read_text()
        p = cr["pilot"]
        n = p["n_instances"]
        learners = np.random.default_rng(p["seed"]).permutation((["part_based", "holistic"] * n)[:n])
        for i, learner in enumerate(learners):
            r = run_instance(f"pilot-{i:03d}", str(learner), p["seed"] + i, cfg, template, "pilot")
            print(summary_line(r), flush=True)
    else:
        raise ValueError(mode)


if __name__ == "__main__":
    main(sys.argv[1])
