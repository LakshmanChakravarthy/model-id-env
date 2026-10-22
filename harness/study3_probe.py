"""Study 3a headroom probe: Claude learns tasks from examples (no tools) and predicts new tasks.
Writes results/study3_probe.json."""
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import tasks
from env.config import load_config

KINDS = ["X", "Y", "Z"]
CONDITIONS = [("labelled", 0, ["a", "c"]), ("labelled", 4, ["a", "b", "c"]), ("unlabelled", 4, ["a", "b", "c"])]


def make_instance(rng, pc, R, S):
    parts = [tasks.task_parts(t) for t in range(64)]
    for _ in range(pc["n_search"]):
        K = [int(u) for u in rng.choice(64, size=pc["n_known"], replace=False)]
        vals = [{parts[k][d] for k in K} for d in range(3)]
        counts = {(d, parts[k][d]): 0 for k in K for d in range(3)}
        for k in K:
            for d in range(3):
                counts[(d, parts[k][d])] += 1
        if min(counts.values()) < pc["min_part_repeats"]:
            continue
        rest = [t for t in range(64) if t not in K]
        known_all = [t for t in rest if all(parts[t][d] in vals[d] for d in range(3))]
        a = [t for t in known_all if S[t, K].max() <= pc["low_overlap_max"]]
        c = [t for t in known_all if S[t, K].max() >= pc["high_overlap_min"]]
        b = [t for t in rest if sum(parts[t][d] not in vals[d] for d in range(3)) == 1]
        if a and b and c:
            return K, {"a": int(rng.choice(a)), "b": int(rng.choice(b)), "c": int(rng.choice(c))}
    raise RuntimeError("no instance found")


def build(seed, pc):
    rng = np.random.default_rng(seed)
    R = tasks.response_matrix()
    S = tasks.similarity_matrix(R)
    K, tests = make_instance(rng, pc, R, S)
    label_perm = [rng.permutation(4) + 1 for _ in range(3)]
    known_names = [chr(ord("A") + i) for i in range(len(K))]
    known_ex = {k: [int(x) for x in rng.choice(256, size=pc["n_known_examples"], replace=False)] for k in K}
    test_ex = {}
    for typ, t in tests.items():
        idx = rng.permutation(256)
        test_ex[typ] = {"shots": [int(x) for x in idx[:pc["n_shots"]]],
                        "items": [int(x) for x in idx[pc["n_shots"]:pc["n_shots"] + pc["n_test_items"]]]}
    return {"seed": seed, "K": K, "tests": tests, "label_perm": [p.tolist() for p in label_perm],
            "known_names": known_names, "known_examples": known_ex, "test_examples": test_ex}


def label(t, inst):
    return "-".join(f"{KINDS[d]}{inst['label_perm'][d][v]}" for d, v in enumerate(tasks.task_parts(t)))


def fmt(x):
    b = format(x, "08b")
    return f"{b[:4]} {b[4:]}"


def prompt(inst, condition, shots, typ, R):
    lines = ["# Learn tasks from examples", "",
             "Each task maps an input to one of four buttons: 0, 1, 2, or 3. An input is a pair of stimuli; each "
             "stimulus has 4 binary features, written as 4 bits. The line `1011 0110 -> 2` means: stimulus 1 is 1011, "
             "stimulus 2 is 0110, and the correct button is 2. Within a task, the mapping is fixed and deterministic.", ""]
    if condition == "labelled":
        lines += ["Each task is built from three components, one of each kind: an X component, a Y component, and a Z "
                  "component. Each kind has several possible versions (X1, X2, and so on). A task's label lists its "
                  "components, for example X2-Y1-Z3. Tasks that share part of a label share that component.", ""]
    lines += ["## Known tasks", ""]
    for name, k in zip(inst["known_names"], inst["K"]):
        title = label(k, inst) if condition == "labelled" else name
        lines.append(f"### Task {title}")
        lines += [f"{fmt(x)} -> {R[k, x]}" for x in inst["known_examples"][k]]
        lines.append("")
    t = inst["tests"][typ]
    ex = inst["test_examples"][typ]
    title = f"Task {label(t, inst)}" if condition == "labelled" else "a new task"
    lines += ["## The new task", ""]
    if shots == 0:
        lines.append(f"You have no examples of {title}.")
    else:
        lines.append(f"Here are {shots} examples of {title}:")
        lines += [f"{fmt(x)} -> {R[t, x]}" for x in ex["shots"][:shots]]
    lines += ["", f"Predict the button for each of these {len(ex['items'])} inputs of the new task:"]
    lines += [f"{i + 1}. {fmt(x)}" for i, x in enumerate(ex["items"])]
    lines += ["", f"Answer with your reasoning if you wish, then end with a JSON list of {len(ex['items'])} integers "
              "(the buttons, in the order of the inputs)."]
    return "\n".join(lines)


def similarity_answers(inst, condition, shots, typ, R):
    """Per item, the response of the known task most consistent with what was shown (majority over ties)."""
    t = inst["tests"][typ]
    ex = inst["test_examples"][typ]
    if shots == 0:
        tp = tasks.task_parts(t)
        score = {k: sum(a == b for a, b in zip(tasks.task_parts(k), tp)) for k in inst["K"]}
    else:
        score = {k: sum(R[k, x] == R[t, x] for x in ex["shots"][:shots]) for k in inst["K"]}
    top = [k for k, v in score.items() if v == max(score.values())]
    out = []
    for x in ex["items"]:
        votes = {}
        for k in top:
            votes[int(R[k, x])] = votes.get(int(R[k, x]), 0) + 1
        best = [r for r, n in votes.items() if n == max(votes.values())]
        out.append(best[0] if len(best) == 1 else None)
    return out, top


def parse(text, n):
    for m in reversed(list(re.finditer(r"\[[\s\d,]+\]", text or ""))):
        try:
            v = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if len(v) == n and all(isinstance(a, int) for a in v):
            return v
    return None


def call(args):
    p, model, max_turns, box = args
    cmd = ["claude", "-p", p, "--model", model, "--tools", "", "--safe-mode", "--strict-mcp-config",
           "--no-session-persistence", "--output-format", "json", "--max-turns", str(max_turns)]
    proc = subprocess.run(cmd, cwd=box, capture_output=True, text=True, timeout=1200)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"result": proc.stdout, "error": proc.stderr[-500:]}


def main():
    cfg = load_config()
    s3 = cfg["study3"]
    pc = s3["probe"]
    R = tasks.response_matrix()
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "study3"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    jobs = []
    for i in range(pc["n_instances"]):
        inst = build(pc["seed"] + i, pc)
        for condition, shots, types in CONDITIONS:
            for typ in types:
                jobs.append((inst, condition, shots, typ))
    prompts = [prompt(inst, c, sh, typ, R) for inst, c, sh, typ in jobs]
    with ThreadPoolExecutor(4) as ex:
        outs = list(ex.map(call, [(p, s3["model"], s3["max_turns"], box) for p in prompts]))
    rows = []
    for (inst, c, sh, typ), p, o in zip(jobs, prompts, outs):
        t = inst["tests"][typ]
        items = inst["test_examples"][typ]["items"]
        truth = [int(R[t, x]) for x in items]
        sim, top = similarity_answers(inst, c, sh, typ, R)
        ans = parse(o.get("result"), len(items))
        rows.append({"seed": inst["seed"], "condition": c, "shots": sh, "type": typ, "task": t,
                     "known": inst["K"], "max_overlap": float(tasks.similarity_matrix(R)[t, inst["K"]].max()),
                     "truth": truth, "answer": ans, "similarity_answer": sim, "similarity_top": top,
                     "accuracy": None if ans is None else float(np.mean([a == b for a, b in zip(ans, truth)])),
                     "prompt": p, "text": o.get("result"), "cost_usd": o.get("total_cost_usd"),
                     "model_usage": list((o.get("modelUsage") or {}).keys())})
    json.dump({"config": s3, "rows": rows}, open(REPO / "results" / "study3_probe.json", "w"), indent=1)
    summarize(rows)


def summarize(rows):
    print("cost", round(sum(r["cost_usd"] or 0 for r in rows), 2), "unparsed", sum(r["answer"] is None for r in rows))
    for condition, shots, types in CONDITIONS:
        for typ in types:
            rr = [r for r in rows if r["condition"] == condition and r["shots"] == shots and r["type"] == typ and r["answer"]]
            acc = np.mean([r["accuracy"] for r in rr]) if rr else float("nan")
            disc = [(a, s, t) for r in rr for a, s, t in zip(r["answer"], r["similarity_answer"], r["truth"])
                    if s is not None and s != t]
            share_sim = np.mean([a == s for a, s, t in disc]) if disc else float("nan")
            share_true = np.mean([a == t for a, s, t in disc]) if disc else float("nan")
            print(f"{condition:10s} {shots} shots ({typ}): accuracy {acc:.2f} (n={len(rr)}); discriminating items "
                  f"{len(disc)}: = similarity {share_sim:.2f}, = correct {share_true:.2f}")


if __name__ == "__main__":
    main()
