"""Study 5: simulated C-PRO-style experiments with known mechanisms, and the ideal (Bayesian) reading of their reports.

Semantics (C-PRO): a pair of stimuli, each with 4 binary features (0 red, 1 vertical, 2 high pitch, 3 constant tone).
Logic rules: both, not both, either, neither. Motor rules: left index (true -> left index, false -> left middle), left
middle, right index, right middle. Buttons: 0 left index, 1 left middle, 2 right index, 3 right middle.

Mechanism (dual route, per trial):
- exact retrieval of the task's own conjunction (practiced tasks; novel tasks after compilation): fast, accurate;
- retrieval of the practiced conjunction that shares the most rules with the task: fast; correct only where the two
  tasks' responses agree, otherwise an intrusion (the practiced task's response);
- composition by reconfiguring that practiced task: slower, with a cost per changed rule by rule type; accurate.
Accounts are parameter regions: compositional (no similarity retrieval, no compilation), conjunctive (strong similarity
retrieval, slow composition, compilation with weak decay), dual-route (moderate retrieval, compilation that decays with lag).
"""
import itertools

import numpy as np

from env import tasks

LOGIC_NAMES = ["BOTH", "NOT BOTH", "EITHER", "NEITHER"]
LOGIC = np.array([[0, 0, 0, 1], [1, 1, 1, 0], [0, 1, 1, 1], [1, 0, 0, 0]])
SENSORY_NAMES = ["RED", "VERTICAL", "HIGH PITCH", "CONSTANT TONE"]
MOTOR_NAMES = ["LEFT INDEX", "LEFT MIDDLE", "RIGHT INDEX", "RIGHT MIDDLE"]
MOTOR = np.array([[1, 0], [0, 1], [3, 2], [2, 3]])       # [button if false, button if true]
RULE_TYPES = ["logic", "sensory", "motor"]
ACCOUNTS = ["compositional", "conjunctive", "dual-route"]
X_IN = tasks.all_inputs()


def responses(task):
    l, s, m = task
    b = LOGIC[l][2 * X_IN[:, 0, s] + X_IN[:, 1, s]]
    return MOTOR[m][b]


ALL_TASKS = list(itertools.product(range(4), range(4), range(4)))
RESP = {t: responses(t) for t in ALL_TASKS}


def overlap(a, b):
    return float(np.mean(RESP[a] == RESP[b]))


def name(task):
    return f"{LOGIC_NAMES[task[0]]} / {SENSORY_NAMES[task[1]]} / {MOTOR_NAMES[task[2]]}"


# ---------- design ----------

def make_design(rng, n_novel_shared2_per_type=3, n_novel_shared1=9, short=(1, 2), long=(8, 12), trials=3):
    """Practice set (4 tasks covering 12 rules) and novel test tasks with their attributes and repetition lags."""
    perm = [rng.permutation(4) for _ in range(3)]
    practiced = [(int(perm[0][i]), int(perm[1][i]), int(perm[2][i])) for i in range(4)]
    novel_all = [t for t in ALL_TASKS if t not in practiced]

    def sharer(t):
        shared = [sum(a == b for a, b in zip(t, p)) for p in practiced]
        best = int(np.argmax(shared))
        return practiced[best], shared[best]

    pools = {"logic": [], "sensory": [], "motor": [], "shared1": []}
    for t in novel_all:
        p, k = sharer(t)
        if k == 2:
            changed = [RULE_TYPES[d] for d in range(3) if t[d] != p[d]][0]
            pools[changed].append(t)
        else:
            pools["shared1"].append(t)
    chosen = []
    for key, n in [("logic", n_novel_shared2_per_type), ("sensory", n_novel_shared2_per_type),
                   ("motor", n_novel_shared2_per_type), ("shared1", n_novel_shared1)]:
        for i in rng.choice(len(pools[key]), size=n, replace=False):
            chosen.append(pools[key][int(i)])
    novel = []
    for j, t in enumerate(chosen):
        p, k = sharer(t)
        lag2 = int(rng.integers(short[0], short[1] + 1)) if j % 2 == 0 else int(rng.integers(long[0], long[1] + 1))
        lag3 = int(rng.integers(long[0], long[1] + 1))
        novel.append({"task": t, "sharer": p, "shared": k,
                      "changed": [RULE_TYPES[d] for d in range(3) if t[d] != p[d]],
                      "overlap": overlap(t, p), "lag2": lag2, "lag2_kind": "short" if j % 2 == 0 else "long",
                      "lag3": lag3})
    return {"practiced": practiced, "novel": novel, "trials": trials, "short": short, "long": long}


# ---------- parameters ----------

def sample_params(rng, account, k):
    """Group-level parameters. Nuisance parameters (speeds, error rates, rule costs) share the same broad prior in every
    account, so overall performance levels carry little information; the accounts differ only in the mechanism
    parameters (similarity retrieval rho, compilation rho_c, its decay d, general speed-up g)."""
    u = lambda lo, hi: rng.uniform(lo, hi, size=k)
    p = {"rt_ret": u(600, 900), "rt_sim_extra": u(0, 120), "e_ret": u(0.02, 0.07), "rt_comp": u(950, 1600),
         "e_comp": u(0.03, 0.30), "cost_logic": u(60, 280), "cost_sensory": u(20, 140), "cost_motor": u(20, 140)}
    if account == "compositional":
        p.update(rho=np.zeros(k), rho_c=np.zeros(k), d=np.zeros(k), g=u(0.02, 0.08))
    elif account == "conjunctive":
        p.update(rho=u(0.2, 0.5), rho_c=u(0.4, 0.9), d=u(0.0, 0.3), g=u(0.0, 0.03))
    else:
        p.update(rho=u(0.1, 0.35), rho_c=u(0.3, 0.8), d=u(0.6, 1.2), g=u(0.01, 0.06))
    return p


def p_exact(p, occurrence, lags):
    """Probability that a compiled trace of the task is retrieved at this occurrence (lags of earlier occurrences)."""
    miss = 1.0
    for lag in lags[:occurrence - 1]:
        miss = miss * (1 - p["rho_c"] * (1 + lag) ** (-p["d"]))
    return 1 - miss


def route_stats(p, item, occurrence):
    """Expected accuracy, RT on correct trials, and share of errors that are intrusions, for one novel task."""
    lags = [item["lag2"] + 0, item["lag3"] + item["lag2"]]           # distance from earlier occurrences
    lags_seq = {2: [item["lag2"]], 3: [item["lag2"] + item["lag3"] + 1, item["lag3"]]}.get(occurrence, [])
    pe = p_exact(p, len(lags_seq) + 1, lags_seq) if occurrence > 1 else 0 * p["rho"]
    ps = (1 - pe) * p["rho"] * (item["shared"] / 2)
    pc = 1 - pe - ps
    cost = sum(p[f"cost_{c}"] for c in item["changed"])
    rt_c = (p["rt_comp"] + cost) * (1 - p["g"]) ** (occurrence - 1)
    rt_r, rt_s = p["rt_ret"], p["rt_ret"] + p["rt_sim_extra"]
    acc_e, acc_s, acc_c = 1 - p["e_ret"], item["overlap"], 1 - p["e_comp"]
    acc = pe * acc_e + ps * acc_s + pc * acc_c
    rt = (pe * acc_e * rt_r + ps * acc_s * rt_s + pc * acc_c * rt_c) / np.maximum(acc, 1e-9)
    err_intr = ps * (1 - acc_s) + (pe * p["e_ret"] + pc * p["e_comp"]) / 3.0     # random errors hit the intruder 1/3
    intr = err_intr / np.maximum(1 - acc, 1e-9)
    return acc, rt, intr


def practiced_stats(p):
    return 1 - p["e_ret"], p["rt_ret"]


# ---------- conditions and predictions ----------

LEVELS = {
    1: ["practiced", "novel"],
    2: ["practiced", "novel", "shared2", "shared1", "changed_logic", "changed_sensory", "changed_motor"],
    3: ["practiced", "novel", "shared2", "shared1", "changed_logic", "changed_sensory", "changed_motor",
        "intr_logic", "intr_sensory", "intr_motor"],
    4: ["practiced", "novel", "shared2", "shared1", "changed_logic", "changed_sensory", "changed_motor",
        "intr_logic", "intr_sensory", "intr_motor", "occ2_short", "occ2_long", "occ3"],
}


def groups(design):
    nv = design["novel"]
    return {"novel": nv, "shared2": [n for n in nv if n["shared"] == 2], "shared1": [n for n in nv if n["shared"] == 1],
            **{f"changed_{t}": [n for n in nv if n["shared"] == 2 and n["changed"] == [t]] for t in RULE_TYPES},
            "occ2_short": [n for n in nv if n["lag2_kind"] == "short"],
            "occ2_long": [n for n in nv if n["lag2_kind"] == "long"], "occ3": nv}


def predict(p, design):
    """Predicted condition means: {condition: (acc, rt)} or intrusion share; arrays over parameter samples."""
    g = groups(design)
    out = {"practiced": practiced_stats(p)}
    for cond, items, occ in [("novel", g["novel"], 1), ("shared2", g["shared2"], 1), ("shared1", g["shared1"], 1),
                             ("changed_logic", g["changed_logic"], 1), ("changed_sensory", g["changed_sensory"], 1),
                             ("changed_motor", g["changed_motor"], 1), ("occ2_short", g["occ2_short"], 2),
                             ("occ2_long", g["occ2_long"], 2), ("occ3", g["occ3"], 3)]:
        s = [route_stats(p, it, occ) for it in items]
        out[cond] = (np.mean([a for a, _, _ in s], axis=0), np.mean([r for _, r, _ in s], axis=0))
    for t in RULE_TYPES:
        s = [route_stats(p, it, 1) for it in g[f"changed_{t}"]]
        out[f"intr_{t}"] = np.mean([i for _, _, i in s], axis=0)
    return out


# ---------- simulated participants ----------

def simulate(rng, account, design, n_participants, group=None):
    """Trial-level simulation. Returns the reported summary: {condition: {"acc": (mean, se), "rt": (mean, se)}} and
    {"intr_<type>": (mean, se)}, plus the group parameters used."""
    group = group or {k: float(v[0]) for k, v in sample_params(rng, account, 1).items()}
    trials = design["trials"]
    g = groups(design)
    per = {c: {"acc": [], "rt": []} for c in ["practiced"] + list(g)}
    intr = {t: [] for t in RULE_TYPES}
    for _ in range(n_participants):
        pp = {}
        for k_, v in group.items():                       # between-participant variability
            if k_.startswith("rt"):
                pp[k_] = v * np.exp(rng.normal(0, 0.15))
            elif k_.startswith("cost"):
                pp[k_] = v * np.exp(rng.normal(0, 0.3))
            elif k_.startswith("e_") or k_ in ("rho", "rho_c"):
                pp[k_] = float(np.clip(v * np.exp(rng.normal(0, 0.3)), 0, 0.95))
            else:
                pp[k_] = v
        pp = {k_: np.array([v]) for k_, v in pp.items()}

        def trial_block(acc_p, rt_mean, n):
            correct = rng.random(n) < acc_p
            rts = rt_mean * np.exp(rng.normal(-0.02, 0.2, size=n))
            return correct, rts

        c, r = trial_block(float(1 - pp["e_ret"][0]), float(pp["rt_ret"][0]), trials * 2 * len(design["practiced"]))
        per["practiced"]["acc"].append(c.mean())
        per["practiced"]["rt"].append(r[c].mean() if c.any() else np.nan)
        for cond, items in g.items():
            occ = {"occ2_short": 2, "occ2_long": 2, "occ3": 3}.get(cond, 1)
            cs, rs = [], []
            for it in items:
                a, rt, _ = route_stats(pp, it, occ)
                cc, rr = trial_block(float(a[0]), float(rt[0]), trials)
                cs.append(cc)
                rs.append(rr)
            cs, rs = np.concatenate(cs), np.concatenate(rs)
            per[cond]["acc"].append(cs.mean())
            per[cond]["rt"].append(rs[cs].mean() if cs.any() else np.nan)
        for t in RULE_TYPES:
            errs = hits = 0
            for it in g[f"changed_{t}"]:
                a, _, ish = route_stats(pp, it, 1)
                n_err = rng.binomial(trials, float(1 - a[0]))
                errs += n_err
                hits += rng.binomial(n_err, float(min(1.0, ish[0])))
            intr[t].append(hits / errs if errs else np.nan)
    summary = {"_participants": {c: {k: list(map(float, v)) for k, v in d.items()} for c, d in per.items()},
               "practice": practice_curve(rng, group, n_participants)}
    for cond, d in per.items():
        summary[cond] = {k: (float(np.nanmean(v)), float(np.nanstd(v, ddof=1) / np.sqrt(np.sum(~np.isnan(v)))))
                         for k, v in d.items()}
    for t in RULE_TYPES:
        v = np.array(intr[t], dtype=float)
        summary[f"intr_{t}"] = (float(np.nanmean(v)), float(np.nanstd(v, ddof=1) / np.sqrt(np.sum(~np.isnan(v)))))
    return summary, group


def practice_curve(rng, group, n_participants, blocks=6):
    """Practice phase (the same form under every account): RT falls and accuracy rises over blocks."""
    rts, accs = [], []
    for _ in range(n_participants):
        rt_end = group["rt_ret"] * np.exp(rng.normal(0, 0.15))
        e_end = float(np.clip(group["e_ret"] * np.exp(rng.normal(0, 0.4)), 0.005, 0.3))
        start_gap = rng.uniform(0.12, 0.25)
        rt_b = [rt_end * (1 + 0.9 * b ** -1.5) * np.exp(rng.normal(0, 0.06)) for b in range(1, blocks + 1)]
        acc_b = [float(np.clip((1 - e_end) - start_gap * b ** -1.3 + rng.normal(0, 0.03), 0, 1))
                 for b in range(1, blocks + 1)]
        rts.append(rt_b)
        accs.append(acc_b)
    rts, accs = np.array(rts), np.array(accs)
    se = lambda a: a.std(axis=0, ddof=1) / np.sqrt(len(a))
    return [{"block": b + 1, "rt": (float(rts.mean(0)[b]), float(se(rts)[b])),
             "acc": (float(accs.mean(0)[b]), float(se(accs)[b]))} for b in range(blocks)]


# ---------- ideal reading ----------

def log_lik(pred, summary, level):
    ll = 0.0
    for cond in LEVELS[level]:
        if cond.startswith("intr_"):
            m, se = summary[cond]
            if np.isnan(m):
                continue
            ll = ll - 0.5 * ((m - pred[cond]) / max(se, 0.02)) ** 2
        else:
            a, rt = pred[cond]
            (ma, sa), (mr, sr) = summary[cond]["acc"], summary[cond]["rt"]
            ll = ll - 0.5 * ((ma - a) / max(sa, 0.005)) ** 2 - 0.5 * ((mr - rt) / max(sr, 5.0)) ** 2
    return ll


TAU = 4.0   # likelihood tempering, chosen on simulated data for calibration (ECE 0.055 -> 0.017 on a fresh validation set)


def posterior(summary, design, level, rng, k=4000, tau=TAU):
    """Posterior over accounts. The likelihood ignores participant-level variability and correlations between
    conditions, which makes the untempered posterior overconfident; tempering by tau restores calibration."""
    logm = {}
    for acc in ACCOUNTS:
        p = sample_params(rng, acc, k)
        ll = log_lik(predict(p, design), summary, level) / tau
        logm[acc] = float(np.log(np.mean(np.exp(ll - ll.max()))) + ll.max())
    mx = max(logm.values())
    w = {a: np.exp(v - mx) for a, v in logm.items()}
    z = sum(w.values())
    return {a: float(v / z) for a, v in w.items()}
