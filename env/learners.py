"""Stylized learners. Each returns examples to criterion for a test task, given known tasks.

mean_cost_* are noise-free; sample_cost adds Gaussian noise, rounds, and floors at min_cost.
"""
import numpy as np

from env import tasks


def selection_uncertainty(t, known):
    """Sum over the dimensions whose value of t is known of log2(number of known values in that dimension)."""
    parts = tasks.task_parts(t)
    known_parts = [tasks.task_parts(k) for k in known]
    total = 0.0
    for d in range(tasks.N_DIMS):
        values = {kp[d] for kp in known_parts}
        if parts[d] in values:
            total += np.log2(len(values))
    return total


def mean_cost_part_based(t, known, p):
    return p["base"] + p["c_new"] * tasks.new_parts(t, known) + p["c_sel"] * selection_uncertainty(t, known)


def mean_cost_holistic(t, known, p, sim, measure="max", tau=0.1):
    s = tasks.similarity_to_known(t, known, sim, measure, tau)
    return p["base"] + p["c0"] * (1.0 - s) ** p["alpha"]


def factored_library(known, k):
    """Study 2: the (dimension, value) rules that occur in at least k trained tasks."""
    counts = {}
    for kt in set(known):
        for d, v in enumerate(tasks.task_parts(kt)):
            counts[(d, v)] = counts.get((d, v), 0) + 1
    return {dv for dv, n in counts.items() if n >= k}


def mean_cost_factor(t, known, cfg, sim, k):
    """Study 2: factor-when-justified learner. The cheaper of recombining factored rules and adapting
    the nearest stored whole task."""
    p = cfg["part_based"]
    library = factored_library(known, k)
    parts = tasks.task_parts(t)
    new = sum((d, v) not in library for d, v in enumerate(parts))
    sel = 0.0
    for d, v in enumerate(parts):
        if (d, v) in library:
            sel += np.log2(sum(1 for dd, _ in library if dd == d))
    part_route = p["base"] + p["c_new"] * new + p["c_sel"] * sel
    holistic_route = mean_cost_holistic(t, known, cfg["holistic"], sim,
                                        cfg["similarity"]["measure"], cfg["similarity"]["kernel_tau"])
    return min(part_route, holistic_route)


def mean_cost(learner, t, known, cfg, sim, k=None):
    # factorized_holistic (case 4): a holistic learner whose similarity metric is factorized over the
    # rule dimensions. Its cost is defined to equal the part-based learner's (equivalence by construction).
    if learner == "factor_when_justified":
        return mean_cost_factor(t, known, cfg, sim, k)
    if learner in ("part_based", "factorized_holistic"):
        return mean_cost_part_based(t, known, cfg["part_based"])
    if learner == "holistic":
        return mean_cost_holistic(t, known, cfg["holistic"], sim,
                                  cfg["similarity"]["measure"], cfg["similarity"]["kernel_tau"])
    raise ValueError(f"unknown learner: {learner}")


def sample_cost(learner, t, known, cfg, sim, rng, k=None):
    m = mean_cost(learner, t, known, cfg, sim, k)
    noisy = round(m + rng.normal(0.0, cfg["noise"]["sd"]))
    return int(max(cfg["noise"]["min_cost"], noisy))
