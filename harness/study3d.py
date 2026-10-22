"""Study 3d: the 3c prompts (and the 3b block-A determined prompts as a control) with an instruction to generate
alternative decompositions (V1), or V1 plus an instruction to look for cross-component patterns (V2).
Writes results/study3d.json."""
import json
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env.config import load_config
from harness import study3b as s3b

ANSWER_START = "Reason as you like, then end with one JSON object"
ALT = re.compile(r"complement|negat|flip|swap|opposite|either reading|both readings|two readings|alternative|equally|"
                 r"symmetr|inver", re.I)


def with_instruction(prompt, text):
    i = prompt.index(ANSWER_START)
    return prompt[:i] + text + "\n\n" + prompt[i:]


def classify(preds, posterior):
    if preds is None:
        return None
    for rank, (v, _) in enumerate(posterior):
        if sum(a == b for a, b in zip(preds, v)) >= 14:
            return "modal" if rank == 0 else f"other{rank}"
    return "neither"


def main():
    cfg = load_config()
    s3 = cfg["study3"]
    d = s3["d"]
    c_rows = json.load(open(REPO / "results" / "study3c.json"))["rows"]
    b_rows = [r for r in json.load(open(REPO / "results" / "study3b.json"))["rows"] if r["block"] == "A" and r["set"] == "det"]
    jobs = []
    for r in c_rows:
        for variant, text in [("V1", d["alternatives"]), ("V2", d["alternatives"] + " " + d["overhypothesis"])]:
            jobs.append({"source": "3c", "cell": r["cell"], "i": r["i"], "variant": variant,
                         "prompt": with_instruction(r["prompt"], text), "ref": r})
    for r in b_rows:
        jobs.append({"source": "3b-det", "cell": "3b-det-" + ("stated" if r["regularity"] else "withheld"), "i": r["i"],
                     "variant": "V1", "prompt": with_instruction(r["prompt"], d["alternatives"]), "ref": r})
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "study3d"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    with ThreadPoolExecutor(d["max_parallel"]) as ex:
        resps = list(ex.map(s3b.call, [(j["prompt"], s3["model"], s3["max_turns"], box) for j in jobs]))
    rows = []
    for j, resp in zip(jobs, resps):
        ref = j["ref"]
        ans = s3b.parse(resp.get("result"), len(ref["truth"]))
        preds = ans["predictions"] if ans else None
        row = {"source": j["source"], "cell": j["cell"], "i": j["i"], "variant": j["variant"], "answer": ans,
               "claude_determined": None if ans is None else ans.get("determined"),
               "claude_confidence": None if ans is None else ans.get("confidence"),
               "mentions_alternative": bool(ALT.search(resp.get("result") or "")),
               "prompt": j["prompt"], "text": resp.get("result"), "cost_usd": resp.get("total_cost_usd"),
               "model_usage": list((resp.get("modelUsage") or {}).keys()),
               "baseline": {"choice": ref.get("choice"), "determined": ref.get("claude_determined"),
                            "confidence": ref.get("claude_confidence"), "accuracy": ref.get("accuracy")}}
        if j["source"] == "3c":
            row["choice"] = classify(preds, ref["ideal"]["posterior"])
            row["ideal_p_modal"] = ref["ideal"]["p_modal"]
            row["confident_error"] = bool(ans and ans.get("determined") and float(ans.get("confidence") or 0) >= 0.9
                                          and row["choice"] != "modal")
        else:
            row["accuracy"] = None if preds is None else float(np.mean([a == b for a, b in zip(preds, ref["truth"])]))
        rows.append(row)
    json.dump({"config": d, "rows": rows}, open(REPO / "results" / "study3d.json", "w"), indent=1, default=str)
    summarize(rows)


def summarize(rows):
    print("cost", round(sum(r["cost_usd"] or 0 for r in rows), 2), "unparsed", sum(r["answer"] is None for r in rows))
    for variant in ("V1", "V2"):
        for cell in ("regular-high", "regular-moderate", "irregular"):
            rr = [r for r in rows if r["source"] == "3c" and r["variant"] == variant and r["cell"] == cell and r["answer"]]
            if not rr:
                continue
            ch = {}
            for r in rr:
                ch[r["choice"]] = ch.get(r["choice"], 0) + 1
            print(f"{variant} {cell}: n={len(rr)} choices {ch} | determined {sum(bool(r['claude_determined']) for r in rr)} "
                  f"| mean conf {np.mean([float(r['claude_confidence']) for r in rr]):.2f} | confident errors "
                  f"{sum(r['confident_error'] for r in rr)} | mentions alternative {sum(r['mentions_alternative'] for r in rr)}")
    for cell in ("3b-det-stated", "3b-det-withheld"):
        rr = [r for r in rows if r["cell"] == cell and r["answer"]]
        print(f"V1 {cell}: n={len(rr)} accuracy {np.mean([r['accuracy'] for r in rr]):.2f} | determined "
              f"{sum(bool(r['claude_determined']) for r in rr)} | mean conf {np.mean([float(r['claude_confidence']) for r in rr]):.2f}")


if __name__ == "__main__":
    main()
