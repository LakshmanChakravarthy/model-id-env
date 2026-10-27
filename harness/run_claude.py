"""Run Claude (headless Claude Code) as the experimenter on hidden-learner instances.

Usage:
  python harness/run_claude.py probe         # check 3a: permission probe with a fixed command list
  python harness/run_claude.py check3        # check 3b: "any method" leakage run, 1 instance
  python harness/run_claude.py pilot         # main-condition pilot instances
  python harness/run_claude.py pilot_case4   # case-4 pilot instances
  python harness/run_claude.py main          # main run, main condition (resumable)
  python harness/run_claude.py main_case4    # main run, case-4 condition (resumable)
  python harness/run_claude.py pilot_study2  # study 2 pilot (one instance per learner)
  python harness/run_claude.py main_study2   # study 2 main run, 10 per learner (resumable)
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
from harness import baselines, baselines_study2

RESULTS = REPO / "results"
ALLOWED = re.compile(r"^python3 query\.py(\s|$)")
PROBE_COMMANDS = [
    "python3 query.py budget",
    f"cat {REPO}/README.md",
    f"cat ../../..{REPO}/CLAUDE.md",
    f"ls {REPO}",
    "ls",
    "ls ..",
    "cat query.py",
    "head -3 query.py",
    "ps aux",
    "env",
    "pwd",
    f"grep -rl part_based {REPO}/env",
    f"python3 query.py budget && cat {REPO}/configs/default.json",
    "python3 query.py budget; ps aux",
    "python3 query.py budget && ls",
    "python3 -c \"print(1)\"",
    f"git -C {REPO} log -1",
    "echo hello",
]
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


def query_only(cmd):
    """True if the command is one query.py call, or a chain of query.py calls with no other commands."""
    if cmd.startswith("python3 query.py submit "):
        return True
    if re.search(r"[`$<>|]", cmd.replace("||", ";").replace("&&", ";")) or "&" in cmd.replace("&&", ""):
        return False
    return all(ALLOWED.match(part.strip()) for part in re.split(r"&&|\|\||;", cmd) if part.strip())


def last_verdict_json(text):
    """The last JSON object in text with "verdict" and "confidence" keys, or None."""
    decoder, found = json.JSONDecoder(), None
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "verdict" in obj and "confidence" in obj:
                found = obj
    return found


def claude_command(prompt, cr, model=None):
    denied = [f"Bash({c})" for c in cr["denied_commands"]] + [f"Bash({c} *)" for c in cr["denied_commands"]]
    return ["claude", "-p", prompt, "--model", model or cr["model"],
            "--tools", "Bash", "--allowedTools", "Bash(python3 query.py *)",
            "--disallowedTools", *denied,
            "--permission-mode", "dontAsk", "--safe-mode", "--strict-mcp-config",
            "--no-session-persistence", "--output-format", "stream-json", "--verbose",
            "--max-turns", str(cr["max_turns"])]


def audit(events):
    """Every tool call, whether it was a query.py command, whether it errored, and forbidden strings in results."""
    calls, results = {}, {}
    for e in events:
        msg = e.get("message") if isinstance(e, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
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
                     "allowed_form": bool(c["tool"] == "Bash" and query_only(cmd)),
                     "is_error": r["is_error"],
                     "forbidden_strings": [f for f in FORBIDDEN_IN_RESULTS if f in r["text"]]})
    leaks = [r for r in rows if (not r["allowed_form"] and r["is_error"] is False) or r["forbidden_strings"]]
    return {"n_tool_calls": len(rows), "n_other_attempts": sum(not r["allowed_form"] for r in rows),
            "leaks": leaks, "pass": not leaks, "calls": rows}


def run_instance(instance_id, learner, seed, cfg, prompt_template, kind, condition="main", model=None, k=None):
    cr = cfg["claude_runs"]
    env = Environment(learner, seed, cfg, condition, k=k)
    srv, port = server.start(env)
    prompt = prompt_template.replace("{budget}", str(env.budget))
    box = make_sandbox(cr["sandbox_root"], instance_id, port, prompt)
    t0 = time.time()
    try:
        proc = subprocess.run(claude_command(prompt, cr, model), cwd=box, capture_output=True, text=True,
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
                   "model_usage": final.get("modelUsage"), "command": claude_command("<prompt>", cr, model)}

    if code != 0 or not any(e.get("type") == "assistant" for e in events if isinstance(e, dict)):
        # A failed launch (for example an unsupported model) is not a result: keep it out of results/.
        failed = RESULTS.parent / "results_failed"
        failed.mkdir(exist_ok=True)
        (RESULTS / "transcripts" / f"{instance_id}.jsonl").rename(failed / f"{instance_id}.jsonl")
        with open(failed / f"{instance_id}.json", "w") as f:
            json.dump({"instance_id": instance_id, "claude": claude_meta}, f, indent=1, default=str)
        raise RuntimeError(f"{instance_id}: launch failed (returncode {code}): {claude_meta['final_text']}")

    verdict_source = "submit" if env.verdict is not None else None
    if env.verdict is None:
        fallback = last_verdict_json(claude_meta["final_text"] or "")
        if fallback is not None:
            try:
                env.submit(fallback)
                verdict_source = "final_message"
            except (ValueError, RuntimeError):
                pass
    claude_meta["verdict_source"] = verdict_source

    scores = scoring.score(env)
    base = {}
    if condition == "study2":
        for name, f in baselines_study2.BASELINES.items():
            benv = Environment(learner, seed, cfg, condition, k=env.k)
            f(benv, seed + 1)
            base[name] = scoring.score(benv)
    else:
        analyses = ["multiple", "aware"] if condition == "case4" else ["multiple"]
        for name, f in [("random", baselines.random_experimenter), ("dopt", baselines.dopt_experimenter)]:
            for a in analyses:
                benv = Environment(learner, seed, cfg, condition)
                f(benv, seed + 1, a)
                base[name if a == "multiple" else f"{name}_{a}"] = scoring.score(benv)
    record = scoring.instance_record(env, scores, {"instance_id": instance_id, "kind": kind, "prompt": prompt,
                                                    "claude": claude_meta, "audit": audit(events),
                                                    "baselines_same_instance": base})
    with open(RESULTS / f"{instance_id}.json", "w") as f:
        json.dump(record, f, indent=1, default=str)
    return record


def summary_line(r):
    v = r["verdict"] or {}
    key = "design_score" if r["condition"] == "study2" else "dissociation"
    base = "  ".join(f"{k} {b['correct']}/{b[key]:.2f}" for k, b in r["baselines_same_instance"].items())
    return (f"{r['instance_id']}: {r['condition']} learner {r['learner']} (correct: {r['correct_verdict']})  "
            f"verdict {v.get('verdict')} ({v.get('confidence')})  scores {r['scores']}  baselines {base}  "
            f"audit pass {r['audit']['pass']} "
            f"(other attempts {r['audit']['n_other_attempts']})  turns {r['claude']['num_turns']}  "
            f"{r['claude']['elapsed_s']:.0f}s")


def probe(cfg):
    """Check 3a: run a fixed list of commands with the experimenter's flags; non-query commands must be denied."""
    cr = cfg["claude_runs"]
    env = Environment("holistic", 0, cfg)
    srv, port = server.start(env)
    prompt = ("Permissions test. Run each command below with the Bash tool, one tool call per command, exactly as "
              "written. Many will be denied: that is expected. After a denial, continue with the next command. "
              "Do not stop, do not ask questions, do not try alternatives. Commands:\n" + "\n".join(PROBE_COMMANDS))
    box = make_sandbox(cr["sandbox_root"], "probe", port, prompt)
    try:
        proc = subprocess.run(claude_command(prompt, cr, cr["probe_model"]), cwd=box, capture_output=True,
                              text=True, timeout=cr["timeout_s"])
    finally:
        srv.shutdown()
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    a = audit(events)
    ran = {c["command"]: c["is_error"] is False for c in a["calls"]}
    rows = [{"command": c, "attempted": c in ran, "ran": ran.get(c, False), "should_run": query_only(c)}
            for c in PROBE_COMMANDS]
    ok = all(r["attempted"] and r["ran"] == r["should_run"] for r in rows)
    # The raw transcript is not saved: denied output is empty, but it may hold host details if a command ran.
    out = {"pass": ok, "model": cr["probe_model"], "rows": rows,
           "unexpected_calls": [c["command"] for c in a["calls"] if c["command"] not in PROBE_COMMANDS]}
    with open(RESULTS / "checks" / "check3_probe.json", "w") as f:
        json.dump(out, f, indent=1)
    for r in rows:
        print(f"  {'ran   ' if r['ran'] else 'denied'} (should {'run' if r['should_run'] else 'be denied'}"
              f"{'' if r['attempted'] else ', NOT ATTEMPTED'})  {r['command']}")
    print("probe pass", ok)


def main(mode):
    cfg = load_config()
    cr = cfg["claude_runs"]
    if mode == "probe":
        probe(cfg)
    elif mode == "check3":
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
    elif mode in ("main", "main_case4"):
        condition = "case4" if mode == "main_case4" else "main"
        template = (REPO / "harness" / ("prompt_case4.md" if condition == "case4" else "prompt.md")).read_text()
        p = cr[mode]
        n = p["n_instances"]
        pool = (p["learners"] * n)[:n]
        learners = np.random.default_rng(p["seed"]).permutation(pool)
        prefix = "case4" if condition == "case4" else "main"
        for i, learner in enumerate(learners):
            instance_id = f"{prefix}-{i:03d}"
            if (RESULTS / f"{instance_id}.json").exists():
                print(f"{instance_id}: exists, skipped", flush=True)
                continue
            try:
                r = run_instance(instance_id, str(learner), p["seed"] + i, cfg, template, mode, condition=condition)
                print(summary_line(r), flush=True)
            except RuntimeError as e:
                print(f"{instance_id}: {e}", flush=True)
    elif mode in ("pilot_study2", "main_study2"):
        template = (REPO / "harness" / "prompt_study2.md").read_text()
        s2 = cfg["study2"]
        if mode == "pilot_study2":
            p = s2["pilot"]
            plan = [(l, None) for l in np.random.default_rng(p["seed"]).permutation(p["learners"])]
            prefix = "s2pilot"
        else:
            p = s2["main"]
            n = p["n_instances"]
            per = n // 3
            ks = s2["k_values"]
            plan = ([("part_based", None)] * per + [("holistic", None)] * per +
                    [("factor_when_justified", ks[j % len(ks)]) for j in range(per)])
            order = np.random.default_rng(p["seed"]).permutation(len(plan))
            plan = [plan[j] for j in order]
            prefix = "s2main"
        for i, (learner, k) in enumerate(plan):
            instance_id = f"{prefix}-{i:03d}"
            if (RESULTS / f"{instance_id}.json").exists():
                print(f"{instance_id}: exists, skipped", flush=True)
                continue
            try:
                r = run_instance(instance_id, str(learner), p["seed"] + i, cfg, template, mode,
                                 condition="study2", k=k)
                print(summary_line(r), flush=True)
            except RuntimeError as e:
                print(f"{instance_id}: {e}", flush=True)
    elif mode == "pilot_case4":
        template = (REPO / "harness" / "prompt_case4.md").read_text()
        p = cr["case4_pilot"]
        for i, learner in enumerate(np.random.default_rng(p["seed"]).permutation(p["learners"])):
            r = run_instance(f"pilot-case4-{i:03d}", str(learner), p["seed"] + i, cfg, template, "pilot_case4",
                             condition="case4")
            print(summary_line(r), flush=True)
    else:
        raise ValueError(mode)


if __name__ == "__main__":
    main(sys.argv[1])
