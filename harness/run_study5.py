"""Run Study 5. Usage: python harness/run_study5.py pilot | main
Simulated experiments are stored in results/study5/<mode>/instances.json; each call is saved as
results/study5/<mode>/raw/<instance>__L<level>__<instruction>.json as soon as it returns."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import cpro
from env.config import load_config
from harness import study5 as s5
from harness.study4 import call

OUT = REPO / "results" / "study5"


def make_instances(mode, p):
    path = OUT / mode / "instances.json"
    if path.exists():
        return json.load(open(path))
    seed = p["pilot_seed"] if mode == "pilot" else p["seed"]
    rng = np.random.default_rng(seed)
    plan = list(cpro.ACCOUNTS) if mode == "pilot" else [a for a in cpro.ACCOUNTS for _ in range(p["n_per_account"])]
    insts = []
    for i, acc in enumerate(plan):
        design = cpro.make_design(rng)
        summary, group = cpro.simulate(rng, acc, design, p["n_participants"])
        ideal = {L: cpro.posterior(summary, design, L, np.random.default_rng([seed, i, L]), k=p["ideal_k"])
                 for L in (1, 2, 3, 4)}
        insts.append({"id": f"{acc}-{i:02d}", "account": acc, "design": design, "summary": summary,
                      "group_params": group, "ideal": ideal})
    path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(json.loads(json.dumps(insts, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))),
              open(path, "w"))
    return json.load(open(path))


def run(mode, cfg):
    p = cfg["study5"]
    insts = make_instances(mode, p)
    raw = OUT / mode / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    variants = [(4, False)] if mode == "pilot" else [(L, a) for L in (1, 2, 3, 4) for a in (False, True)]
    jobs = [(inst, L, a) for inst in insts for L, a in variants
            if not (raw / f"{inst['id']}__L{L}__{'alternatives' if a else 'base'}.json").exists()]
    box = Path(cfg["claude_runs"]["sandbox_root"]) / f"study5_{mode}"
    box.mkdir(parents=True, exist_ok=True)

    def one(job):
        inst, L, alt = job
        text = s5.report(inst["summary"], inst["design"], L, p["n_participants"])
        prompt = s5.prompt(text, alt)
        resp = call(prompt, p["model"], p["max_turns"], box)
        if resp.get("returncode") not in (None, 0) and not resp.get("result"):
            return f"{inst['id']} L{L} {alt}: launch failed"
        ans = s5.parse(resp.get("result"))
        ideal = inst["ideal"][str(L)] if str(L) in inst["ideal"] else inst["ideal"][L]
        rec = {"id": inst["id"], "account": inst["account"], "level": L,
               "instruction": "alternatives" if alt else "base", "answer": ans, "ideal": ideal,
               "score": s5.score(ans, inst["account"], ideal), "text": resp.get("result"),
               "cost_usd": resp.get("total_cost_usd"), "model_usage": list((resp.get("modelUsage") or {}).keys()),
               "prompt": prompt}
        name = f"{inst['id']}__L{L}__{'alternatives' if alt else 'base'}.json"
        json.dump(rec, open(raw / name, "w"), indent=1)
        sc = rec["score"]
        return f"{name}: " + ("unparsed" if sc is None else f"p_truth={sc['p_truth']:.2f} (ideal {sc['ideal_p_truth']:.2f})")

    with ThreadPoolExecutor(p["max_parallel"]) as ex:
        for msg in ex.map(one, jobs):
            print(msg, flush=True)


if __name__ == "__main__":
    run(sys.argv[1], load_config())
