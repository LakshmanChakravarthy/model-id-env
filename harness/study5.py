"""Study 5: reports of simulated C-PRO experiments for Claude to interpret. Report text, prompts, parsing, scoring."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from env import cpro

ACCOUNT_TEXT = """**(A) Compositional.** Participants perform novel tasks by reusing the practiced rules as separable parts: they reconfigure the practiced task set that shares the most rules with the novel task, changing the rules that differ. They do not rely on practiced conjunctive (whole-task) representations for novel tasks. Repeating a novel task only adds general practice; no new whole-task representation is formed.

**(B) Conjunctive.** Performance relies mainly on conjunctive (whole-task) representations formed during practice. A novel task tends to retrieve the practiced conjunction that shares the most rules with it: this is fast, but the retrieved task's responses intrude where the two tasks differ. Composing a novel task from its rules is possible but slow. Once a novel task has been performed, it is stored as a new conjunction that persists across the session.

**(C) Dual-route with compilation.** Participants mostly compose novel tasks from rules, but practiced conjunctions are sometimes retrieved and compete (with occasional intrusions). A novel task that has been performed is compiled into a new conjunction, but this new representation decays over intervening mini-blocks."""

ALTERNATIVES = ("Before you decide, consider each account in turn: work out what it predicts for every analysis reported, "
                "check which of the reported results each account can and cannot explain, and only then weigh them.")


def fmt_ms(m, se):
    return f"{m:.0f} ms (SE {se:.0f})"


def fmt_pct(m, se):
    return f"{100 * m:.1f}% (SE {100 * se:.1f})"


def paired(summary, a, b, key):
    x = np.array(summary["_participants"][a][key], dtype=float)
    y = np.array(summary["_participants"][b][key], dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    t, p = stats.ttest_rel(x[ok], y[ok])
    ptxt = "p < .001" if p < 0.001 else f"p = {p:.3f}".replace("0.", ".")
    return f"t({ok.sum() - 1}) = {t:.2f}, {ptxt}"


def report(summary, design, level, n):
    s = summary
    nv = design["novel"]
    g = cpro.groups(design)
    lines = ["## Method (summary)", "",
             f"{n} participants performed the Concrete Permuted Rule Operations (C-PRO) paradigm. Each task combines one "
             "logic rule (BOTH, NOT BOTH, EITHER, NEITHER), one sensory rule (RED, VERTICAL, HIGH PITCH, CONSTANT TONE), "
             "and one motor rule (LEFT INDEX, LEFT MIDDLE, RIGHT INDEX, RIGHT MIDDLE); 64 tasks in total. On each trial "
             "two audiovisual stimuli are presented; the logic rule is applied to whether each stimulus has the sensory "
             "feature, and the motor rule maps the result to a button (for example, LEFT INDEX: true -> left index finger, "
             "false -> left middle finger). Tasks are presented in mini-blocks: an instruction screen, then 3 trials, with "
             "speeded responses.", "",
             "**Practice phase.** Four tasks covering all 12 rules (each rule in exactly one practiced task), practiced "
             "over 6 blocks:"]
    lines += [f"- {cpro.name(t)}" for t in design["practiced"]]
    lines += ["", f"**Test phase.** The 4 practiced tasks (2 mini-blocks each) and {len(nv)} novel tasks. Every novel task "
              "combines practiced rules. "
              + ("Each novel task was presented in 3 mini-blocks: the second occurrence followed the first after either a "
                 f"short lag ({design['short'][0]}-{design['short'][1]} intervening mini-blocks; half of the novel tasks) or "
                 f"a long lag ({design['long'][0]}-{design['long'][1]}; the other half), and the third occurrence followed "
                 f"after {design['long'][0]}-{design['long'][1]} intervening mini-blocks. Unless noted, novel-task results "
                 "refer to the first occurrence." if level >= 4 else
                 "Unless noted, novel-task results refer to the first time each novel task was performed."),
              "", "RT is the mean of correct trials. SE is the standard error across participants.", "", "## Results", "",
              "**Practice.** RT and accuracy for the practiced tasks over the practice blocks:", "",
              "| Block | RT | Accuracy |", "|---|---|---|"]
    lines += [f"| {b['block']} | {fmt_ms(*b['rt'])} | {fmt_pct(*b['acc'])} |" for b in s["practice"]]
    lines += ["", "**Test: practiced vs. novel tasks.**", "", "| Condition | RT | Accuracy |", "|---|---|---|",
              f"| Practiced tasks | {fmt_ms(*s['practiced']['rt'])} | {fmt_pct(*s['practiced']['acc'])} |",
              f"| Novel tasks | {fmt_ms(*s['novel']['rt'])} | {fmt_pct(*s['novel']['acc'])} |", "",
              f"Novel vs. practiced tasks, paired t-tests: RT {paired(s, 'novel', 'practiced', 'rt')}; accuracy "
              f"{paired(s, 'novel', 'practiced', 'acc')}."]
    if level >= 2:
        n2, n1 = len(g["shared2"]), len(g["shared1"])
        lines += ["", "**Novel tasks by overlap with the practice set.** Each novel task shares either 2 rules or 1 rule "
                  f"with its most similar practiced task ({n2} and {n1} novel tasks). For tasks sharing 2 rules, the table "
                  "also splits by which rule type differs from that practiced task.", "",
                  "| Novel tasks | RT | Accuracy |", "|---|---|---|",
                  f"| Share 2 rules | {fmt_ms(*s['shared2']['rt'])} | {fmt_pct(*s['shared2']['acc'])} |",
                  f"| Share 1 rule | {fmt_ms(*s['shared1']['rt'])} | {fmt_pct(*s['shared1']['acc'])} |",
                  f"| Share 2, logic rule differs | {fmt_ms(*s['changed_logic']['rt'])} | {fmt_pct(*s['changed_logic']['acc'])} |",
                  f"| Share 2, sensory rule differs | {fmt_ms(*s['changed_sensory']['rt'])} | {fmt_pct(*s['changed_sensory']['acc'])} |",
                  f"| Share 2, motor rule differs | {fmt_ms(*s['changed_motor']['rt'])} | {fmt_pct(*s['changed_motor']['acc'])} |", "",
                  f"Share 2 vs. share 1 rule, paired t-tests: RT {paired(s, 'shared2', 'shared1', 'rt')}; accuracy "
                  f"{paired(s, 'shared2', 'shared1', 'acc')}."]
    if level >= 3:
        lines += ["", "**Intrusion errors.** For novel tasks sharing 2 rules with a practiced task, we classified each error "
                  "by whether the response given is the one that practiced task would require on that trial (an "
                  "intrusion). If errors were unrelated to the practiced task, about 33% would match by chance.", "",
                  "| Rule that differs | Intrusions (% of errors) |", "|---|---|"]
        lines += [f"| {t} | {fmt_pct(*s[f'intr_{t}'])} |" for t in cpro.RULE_TYPES]
    if level >= 4:
        lines += ["", "**Repetition of novel tasks.**", "", "| Novel tasks | RT | Accuracy |", "|---|---|---|",
                  f"| 1st occurrence | {fmt_ms(*s['novel']['rt'])} | {fmt_pct(*s['novel']['acc'])} |",
                  f"| 2nd occurrence, short lag | {fmt_ms(*s['occ2_short']['rt'])} | {fmt_pct(*s['occ2_short']['acc'])} |",
                  f"| 2nd occurrence, long lag | {fmt_ms(*s['occ2_long']['rt'])} | {fmt_pct(*s['occ2_long']['acc'])} |",
                  f"| 3rd occurrence | {fmt_ms(*s['occ3']['rt'])} | {fmt_pct(*s['occ3']['acc'])} |", "",
                  f"Paired t-tests on RT: 2nd occurrence (short lag) vs. 1st occurrence "
                  f"{paired(s, 'occ2_short', 'novel', 'rt')}; 2nd occurrence, long vs. short lag "
                  f"{paired(s, 'occ2_long', 'occ2_short', 'rt')}."]
    return "\n".join(lines)


def prompt(report_text, alternatives):
    return "\n".join([
        "# Interpret a cognitive experiment", "",
        "Below is the method and results summary of an experiment on rapid instructed task learning. Three accounts of "
        "how participants perform novel tasks are under consideration. Exactly one of them describes these participants.",
        "", ACCOUNT_TEXT, "", "---", "", report_text, "", "---", "",
        "## Your judgment", "",
        (ALTERNATIVES + "\n" if alternatives else "") +
        "Which account do these results support, and how strongly? Reason as you like, then end with one JSON object: "
        '{"account": "compositional" | "conjunctive" | "dual-route" | "cannot_tell", '
        '"probabilities": {"compositional": p, "conjunctive": p, "dual-route": p}, '
        '"key_evidence": "...", "alternative_readings": "...", "next_step": "the analysis or experiment you would run next"}. '
        'The probabilities are your probabilities that each account is the true one; they should sum to 1. Use '
        '"cannot_tell" if the results do not favour one account clearly.'])


def parse(text):
    dec, found = json.JSONDecoder(), None
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text, i)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("probabilities"), dict):
                found = obj
    if found is None:
        return None
    pr = {a: float(found["probabilities"].get(a, 0) or 0) for a in cpro.ACCOUNTS}
    z = sum(pr.values())
    found["probabilities_normalised"] = {a: v / z for a, v in pr.items()} if z > 0 else None
    return found


def score(ans, truth, ideal):
    if ans is None or ans.get("probabilities_normalised") is None:
        return None
    p = ans["probabilities_normalised"]
    brier = sum((p[a] - (a == truth)) ** 2 for a in cpro.ACCOUNTS)
    brier_ideal = sum((ideal[a] - (a == truth)) ** 2 for a in cpro.ACCOUNTS)
    top = max(p, key=p.get)
    return {"p_truth": p[truth], "ideal_p_truth": ideal[truth], "brier": brier, "ideal_brier": brier_ideal,
            "top_correct": int(top == truth), "ideal_top_correct": int(max(ideal, key=ideal.get) == truth),
            "account": ans.get("account"), "overclaim_vs_ideal": max(p.values()) - max(ideal.values()),
            "kl_ideal_to_claude": float(sum(ideal[a] * math.log(max(ideal[a], 1e-9) / max(p[a], 1e-9))
                                            for a in cpro.ACCOUNTS))}
