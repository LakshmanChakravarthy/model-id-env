"""Study 3e: the 3c prompts with button labels renamed to colour names (no order), with no instruction (V0) or the
3d cross-component instruction (V2). Writes results/study3e.json."""
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
from harness.study3d import ALT, classify, with_instruction

CATEGORICAL = re.compile(r"(two|pair of) (buttons|colou?rs) (are|is) (always )?(used )?for true|"
                         r"(always|only) (one of|either) \w+ (or|and) \w+ (for|when) (true|false)|class(es)?|"
                         r"group(s|ed)? of (buttons|colou?rs)|true (buttons|colou?rs)|false (buttons|colou?rs)", re.I)


def recolour(prompt, colours):
    """Rename buttons 0-3 to colours[0-3] in the intro, the worked example, every example output, and the format."""
    p = prompt.replace("one of four buttons: 0, 1, 2, or 3.", "one of four buttons: red, green, blue, or yellow.")
    p = p.replace("`1011 0110 -> 2` means: stimulus 1 is 1011, stimulus 2 is 0110, and the correct button is 2.",
                  f"`1011 0110 -> {colours[2]}` means: stimulus 1 is 1011, stimulus 2 is 0110, and the correct button is "
                  f"{colours[2]}.")
    p = re.sub(r"-> ([0-3])$", lambda m: f"-> {colours[int(m.group(1))]}", p, flags=re.M)
    p = p.replace('{"predictions": [the buttons, in order]', '{"predictions": [the button names as strings, in order]')
    assert not re.search(r"-> [0-3]\s*$", p, flags=re.M) and "0, 1, 2, or 3" not in p
    return p


def main():
    cfg = load_config()
    s3 = cfg["study3"]
    e = s3["e"]
    c_rows = json.load(open(REPO / "results" / "study3c.json"))["rows"]
    d = s3["d"]
    jobs = []
    for n, r in enumerate(c_rows):
        perm = np.random.default_rng(e["seed"] + n).permutation(len(e["colors"]))
        colours = [e["colors"][int(k)] for k in perm]           # colours[button] = colour name
        base = recolour(r["prompt"], colours)
        for variant, prompt in [("V0", base), ("V2", with_instruction(base, d["alternatives"] + " " + d["overhypothesis"]))]:
            jobs.append({"cell": r["cell"], "i": r["i"], "variant": variant, "colours": colours, "prompt": prompt, "ref": r})
    box = Path(cfg["claude_runs"]["sandbox_root"]) / "study3e"
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    with ThreadPoolExecutor(e["max_parallel"]) as ex:
        resps = list(ex.map(s3b.call, [(j["prompt"], s3["model"], s3["max_turns"], box) for j in jobs]))
    rows = []
    for j, resp in zip(jobs, resps):
        ref = j["ref"]
        ans = s3b.parse(resp.get("result"), len(ref["truth"]))
        inv = {c.lower(): b for b, c in enumerate(j["colours"])}
        preds = None
        if ans:
            preds = [inv.get(str(v).strip().lower()) for v in ans["predictions"]]
            if any(v is None for v in preds):
                preds = None
        choice = classify(preds, ref["ideal"]["posterior"])
        text = resp.get("result") or ""
        rows.append({"cell": j["cell"], "i": j["i"], "variant": j["variant"], "colours": j["colours"], "answer": ans,
                     "predictions_as_buttons": preds, "choice": choice,
                     "claude_determined": None if ans is None else ans.get("determined"),
                     "claude_confidence": None if ans is None else ans.get("confidence"),
                     "confident_error": bool(ans and ans.get("determined") and float(ans.get("confidence") or 0) >= 0.9
                                             and choice != "modal"),
                     "mentions_alternative": bool(ALT.search(text)), "states_categorical": bool(CATEGORICAL.search(text)),
                     "ideal_p_modal": ref["ideal"]["p_modal"], "prompt": j["prompt"], "text": text,
                     "cost_usd": resp.get("total_cost_usd"), "model_usage": list((resp.get("modelUsage") or {}).keys())})
    json.dump({"config": e, "rows": rows}, open(REPO / "results" / "study3e.json", "w"), indent=1, default=str)
    print("cost", round(sum(r["cost_usd"] or 0 for r in rows), 2), "unparsed", sum(r["predictions_as_buttons"] is None for r in rows))
    for variant in ("V0", "V2"):
        for cell in ("regular-high", "regular-moderate", "irregular"):
            rr = [r for r in rows if r["variant"] == variant and r["cell"] == cell and r["predictions_as_buttons"]]
            ch = {}
            for r in rr:
                ch[r["choice"]] = ch.get(r["choice"], 0) + 1
            print(f"{variant} {cell}: n={len(rr)} choices {ch} | determined {sum(bool(r['claude_determined']) for r in rr)} | "
                  f"mean conf {np.mean([float(r['claude_confidence']) for r in rr]):.2f} | confident errors "
                  f"{sum(r['confident_error'] for r in rr)} | states categorical {sum(r['states_categorical'] for r in rr)}")


if __name__ == "__main__":
    main()
