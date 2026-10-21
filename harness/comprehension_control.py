"""Case-4 comprehension control: no experiment, no tools. Which verdict do fixed part-based-looking data justify,
under the main wording and the case-4 wording of the hypotheses? Writes results/comprehension_control.json."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env.config import load_config
from harness.run_claude import last_verdict_json

CORRECT = {"main": "part-based", "case4": "cannot_decide"}
PROMPT_FILES = {"main": "prompt.md", "case4": "prompt_case4.md"}
DATA = """## The data

An experimenter trained the learner on two tasks, L1-S1-M1 and L2-S2-M2. Then the experimenter tested four new tasks, 12 times each. "New rules" counts the test task's rules that are not part of any trained task. "Output overlap" is the largest fraction of inputs on which the test task gives the same response as a trained task. Lower cost means easier learning.

| Test task | New rules | Output overlap | Mean examples to criterion |
|---|---|---|---|
| L1-S1-M2 | 0 | 0.75 | 10.4 |
| L2-S1-M1 | 0 | 0.06 | 17.8 |
| L3-S3-M3 | 3 | 0.56 | 37.3 |
| L4-S4-M4 | 3 | 0.06 | 41.5 |

Test results are noisy (the standard deviation of a single test is about 15).

## Your answer

Which verdict does this evidence justify: "part-based", "holistic", or "cannot_decide"? Reply with your reasoning, then end with one JSON object: {"verdict": "...", "confidence": 0.0, "justification": "..."}, where confidence is your probability that the verdict is correct.
"""


def section(text, title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## )", text, flags=re.S | re.M)
    return f"## {title}\n{m.group(1)}"


def build_prompt(wording):
    text = (REPO / "harness" / PROMPT_FILES[wording]).read_text()
    head = ("# Interpret an experiment\n\nA hidden learner learns tasks. It uses one of two learning mechanisms. "
            "Your job is to judge which mechanism the evidence below supports.\n\n")
    return head + section(text, "The tasks") + section(text, "The two hypotheses") + DATA


def main():
    cfg = load_config()
    cc = cfg["comprehension_control"]
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "comprehension"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    runs = []
    for wording in ("main", "case4"):
        prompt = build_prompt(wording)
        for i in range(cc["n_per_wording"]):
            cmd = ["claude", "-p", prompt, "--model", cc["model"], "--tools", "", "--safe-mode",
                   "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
                   "--max-turns", str(cc["max_turns"])]
            proc = subprocess.run(cmd, cwd=box, capture_output=True, text=True, timeout=600)
            try:
                out = json.loads(proc.stdout)
            except json.JSONDecodeError:
                out = {"result": proc.stdout}
            v = last_verdict_json(out.get("result") or "")
            runs.append({"wording": wording, "i": i, "verdict": v, "correct": int(bool(v) and v["verdict"] == CORRECT[wording]),
                         "text": out.get("result"), "cost_usd": out.get("total_cost_usd"),
                         "model_usage": list((out.get("modelUsage") or {}).keys()), "returncode": proc.returncode})
            print(wording, i, v and (v["verdict"], v["confidence"]), flush=True)
    counts = {w: {} for w in ("main", "case4")}
    for r in runs:
        key = r["verdict"]["verdict"] if r["verdict"] else "none"
        counts[r["wording"]][key] = counts[r["wording"]].get(key, 0) + 1
    out = {"config": cc, "prompts": {w: build_prompt(w) for w in ("main", "case4")}, "counts": counts, "runs": runs}
    with open(REPO / "results" / "comprehension_control.json", "w") as f:
        json.dump(out, f, indent=1)
    print("counts", json.dumps(counts))


if __name__ == "__main__":
    main()
