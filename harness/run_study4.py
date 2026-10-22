"""Run Study 4. Usage:
  python harness/run_study4.py pilot    # 12 calls, pipeline check only (seed pilot_seed)
  python harness/run_study4.py main     # 144 instances x 4 variants = 576 calls (resumable)
  python harness/run_study4.py grade <pilot|main>   # grader codes for every raw response (resumable)
Each call is saved as results/study4/<mode>/raw/<instance>__<format>__<prompt>.json as soon as it returns."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env.config import load_config
from harness import study4 as s4

OUT = REPO / "results" / "study4"
VARIANTS = [("digits", "base"), ("digits", "pattern"), ("colours", "base"), ("colours", "pattern")]


def plan_for(mode, p):
    if mode == "pilot":
        return [(t, "high", 1) for t in s4.TYPES]
    return [(t, c, p["n_per_pool"]) for t in s4.TYPES for c in ("high", "moderate", "irregular")]


def jsonable(x):
    return json.loads(json.dumps(x, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def instances(mode, p):
    path = OUT / mode / "instances.json"
    if path.exists():
        return json.load(open(path))
    seed = p["pilot_seed"] if mode == "pilot" else p["seed"]
    insts = jsonable(s4.make_instances(p, seed, plan_for(mode, p)))
    path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(insts, open(path, "w"))
    return json.load(open(path))


def restore(inst):
    inst["known"] = [tuple(k) for k in inst["known"]]
    inst["test"] = tuple(inst["test"])
    inst["world"]["Z"] = [tuple(z) for z in inst["world"]["Z"]]
    return inst


def run(mode, cfg):
    p = cfg["study4"]
    insts = [restore(i) for i in instances(mode, p)]
    raw = OUT / mode / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    jobs = [(inst, fmt, pr) for inst in insts for fmt, pr in VARIANTS
            if not (raw / f"{inst['id']}__{fmt}__{pr}.json").exists()]
    box = Path(cfg["claude_runs"]["sandbox_root"]) / f"study4_{mode}"
    box.mkdir(parents=True, exist_ok=True)

    def one(job):
        inst, fmt, pr = job
        colours = fmt == "colours"
        prompt = s4.build_prompt(inst, colours, pr == "pattern", p)
        resp = s4.call(prompt, p["model"], p["max_turns"], box)
        if resp.get("returncode") not in (None, 0) and not resp.get("result"):
            return f"{inst['id']} {fmt} {pr}: launch failed"
        ans, preds = s4.parse_answer(resp.get("result"), inst, colours)
        rec = {"id": inst["id"], "type": inst["type"], "cell": inst["cell"], "format": fmt, "prompt_variant": pr,
               "answer": ans, "predictions_as_buttons": preds, **s4.score(inst, colours, preds, ans),
               "text": resp.get("result"), "cost_usd": resp.get("total_cost_usd"),
               "model_usage": list((resp.get("modelUsage") or {}).keys()), "prompt": prompt}
        json.dump(jsonable(rec), open(raw / f"{inst['id']}__{fmt}__{pr}.json", "w"), indent=1)
        return f"{inst['id']} {fmt} {pr}: R={rec['R']} conf={rec['confidence']}"

    with ThreadPoolExecutor(p["max_parallel"]) as ex:
        for msg in ex.map(one, jobs):
            print(msg, flush=True)


def grade(mode, cfg):
    p = cfg["study4"]
    raw, gdir = OUT / mode / "raw", OUT / mode / "grades"
    gdir.mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(raw.glob("*.json")) if not (gdir / f.name).exists()]
    box = Path(cfg["claude_runs"]["sandbox_root"]) / f"study4_grade_{mode}"
    box.mkdir(parents=True, exist_ok=True)

    def one(f):
        rec = json.load(open(f))
        resp = s4.call(s4.GRADER + (rec.get("text") or ""), p["grader_model"], p["max_turns"], box)
        code = None
        dec = json.JSONDecoder()
        txt = resp.get("result") or ""
        for i, ch in enumerate(txt):
            if ch == "{":
                try:
                    obj, _ = dec.raw_decode(txt, i)
                    if "regularity_stated" in obj:
                        code = obj
                except json.JSONDecodeError:
                    pass
        json.dump({"id": f.stem, "code": code, "text": txt, "cost_usd": resp.get("total_cost_usd")},
                  open(gdir / f.name, "w"), indent=1)
        return f"{f.stem}: {code}"

    with ThreadPoolExecutor(p["max_parallel"]) as ex:
        for msg in ex.map(one, files):
            print(msg, flush=True)


if __name__ == "__main__":
    cfg = load_config()
    if sys.argv[1] == "grade":
        grade(sys.argv[2], cfg)
    else:
        run(sys.argv[1], cfg)
