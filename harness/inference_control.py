"""Study 2b inference-only control: each main-run instance's own data, as a table, with no tools and no experiment.
Writes results/inference_control.json."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import tasks
from env.config import load_config
from env.environment import CORRECT_VERDICT, Environment
from harness.comprehension_control import section
from harness.run_claude import last_verdict_json

ASK = """## Your answer

Which learner produced these data: "part-based", "holistic", or "factor-when-justified"? Reply with your reasoning, then end with one JSON object: {"verdict": "...", "confidence": 0.0, "justification": "..."}, where confidence is your probability that the verdict is correct.
"""


def data_table(record, cfg):
    env = Environment(record["learner"], record["seed"], cfg, "study2", k=record["scores"]["k"])
    stages, known = [], []
    for e in record["log"]:
        if e["query"] == "train" and "trained" in e["result"]:
            known = list(e["result"]["trained"])
            stages.append({"newly_trained": list(e["args"]), "known": known, "tests": {}})
        elif e["query"] == "test" and "examples_to_criterion" in e["result"]:
            if not stages:
                stages.append({"newly_trained": [], "known": [], "tests": {}})
            stages[-1]["tests"].setdefault(e["args"][0], []).append(e["result"]["examples_to_criterion"])
    lines = ["## The data", "",
             "An experimenter trained and tested the learner in the stages below, in this order. Training is cumulative. "
             "For each tested task: \"rule counts\" = how many of the tasks trained so far contain each of its three rules; "
             "\"overlap\" = its largest fraction of inputs with the same response as a trained task; then every single test "
             "result (examples to criterion; noisy, standard deviation about 15, never below 1).", ""]
    for i, st in enumerate(stages, 1):
        if not st["tests"]:
            continue
        trained = ", ".join(st["newly_trained"]) if st["newly_trained"] else "nothing"
        lines.append(f"**Stage {i}.** Newly trained: {trained}. Trained so far: {', '.join(st['known']) or 'nothing'}.")
        lines.append("")
        lines.append("| Test task | Rule counts | Overlap | Results | Mean |")
        lines.append("|---|---|---|---|---|")
        kid = [env.task_of(n) for n in st["known"]]
        for name, ys in st["tests"].items():
            labels = name.split("-")
            counts = [sum(k.split("-")[d] == labels[d] for k in st["known"]) for d in range(3)]
            overlap = tasks.similarity_to_known(env.task_of(name), kid, env.sim) if kid else 0.0
            lines.append(f"| {name} | {', '.join(f'{l}: {c}' for l, c in zip(labels, counts))} | {overlap:.3f} | "
                         f"{', '.join(map(str, ys))} | {sum(ys) / len(ys):.1f} |")
        lines.append("")
    return "\n".join(lines)


def build_prompt(record, cfg):
    text = (REPO / "harness" / "prompt_study2.md").read_text()
    head = ("# Interpret an experiment\n\nA hidden learner learns tasks. It uses one of three learning mechanisms. "
            "Your job is to judge which one produced the data below.\n\n")
    return head + section(text, "The tasks") + section(text, "The three hypotheses") + data_table(record, cfg) + "\n" + ASK


def main():
    cfg = load_config()
    ic = cfg["study2"]["inference_control"]
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "inference_control"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    out_path = REPO / "results" / "inference_control.json"
    done = {r["instance_id"]: r for r in json.load(open(out_path))["runs"]} if out_path.exists() else {}
    runs = []
    for f in sorted((REPO / "results").glob(f"{ic['source_prefix']}-*.json")):
        record = json.load(open(f))
        iid = record["instance_id"]
        if iid in done and done[iid]["verdict"]:
            runs.append(done[iid])
            continue
        prompt = build_prompt(record, cfg)
        cmd = ["claude", "-p", prompt, "--model", ic["model"], "--tools", "", "--safe-mode", "--strict-mcp-config",
               "--no-session-persistence", "--output-format", "json", "--max-turns", str(ic["max_turns"])]
        proc = subprocess.run(cmd, cwd=box, capture_output=True, text=True, timeout=900)
        try:
            res = json.loads(proc.stdout)
        except json.JSONDecodeError:
            res = {"result": proc.stdout}
        v = last_verdict_json(res.get("result") or "")
        truth = CORRECT_VERDICT[("study2", record["learner"])]
        post = record["scores"]["ideal_posterior"]
        runs.append({"instance_id": iid, "learner": record["learner"], "k": record["scores"]["k"], "verdict": v,
                     "correct": int(bool(v) and v["verdict"] == truth),
                     "in_loop_verdict": record["verdict"]["verdict"], "in_loop_correct": record["scores"]["correct"],
                     "ideal_correct": record["scores"]["ideal_correct"],
                     "inference_gap": (v["confidence"] - post[v["verdict"]]) if v and v["verdict"] in post else None,
                     "prompt": prompt, "text": res.get("result"), "cost_usd": res.get("total_cost_usd"),
                     "model_usage": list((res.get("modelUsage") or {}).keys()), "returncode": proc.returncode})
        print(iid, record["learner"], v and (v["verdict"], v["confidence"]), "in-loop", record["verdict"]["verdict"], flush=True)
        json.dump({"config": ic, "runs": runs}, open(out_path, "w"), indent=1)
    json.dump({"config": ic, "runs": runs}, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main()
