"""C-PRO-like task space: 4 logic x 4 sensory x 4 motor rules = 64 tasks.

A task id t in 0..63 encodes (logic, sensory, motor) = (t // 16, (t // 4) % 4, t % 4).
An input is a pair of stimuli, each with n_features binary features.
Response = motor(logic(stim1[f], stim2[f])), with f the sensory feature.
"""
import itertools
import numpy as np

LOGIC_NAMES = ["both", "either", "neither", "not-both"]
# Truth tables over (a, b) in order 00, 01, 10, 11.
LOGIC_TABLES = np.array([
    [0, 0, 0, 1],  # both (AND)
    [0, 1, 1, 1],  # either (OR)
    [1, 0, 0, 0],  # neither (NOR)
    [1, 1, 1, 0],  # not-both (NAND)
])
# Motor rule m maps the Boolean to a response: row m = [response if False, response if True].
# 2 x 2 design: button for False in {0, 3} x button for True in {1, 2}. No two rules are swaps
# of each other, and only m0 and m3 share no button.
MOTOR_TABLES = np.array([
    [0, 1],
    [0, 2],
    [3, 1],
    [3, 2],
])
N_DIMS = 3


def task_parts(t):
    return (t // 16, (t // 4) % 4, t % 4)


def task_id(logic, sensory, motor):
    return logic * 16 + sensory * 4 + motor


def all_parts(n_values=4):
    return np.array([task_parts(t) for t in range(n_values ** N_DIMS)])


def all_inputs(n_features=4):
    """All stimulus pairs, shape (2**(2*n_features), 2, n_features)."""
    bits = np.array(list(itertools.product([0, 1], repeat=2 * n_features)))
    return bits.reshape(-1, 2, n_features)


def task_responses(t, inputs):
    logic, sensory, motor = task_parts(t)
    a = inputs[:, 0, sensory]
    b = inputs[:, 1, sensory]
    boolean = LOGIC_TABLES[logic][2 * a + b]
    return MOTOR_TABLES[motor][boolean]


def response_matrix(n_features=4):
    """Responses of all 64 tasks to all inputs, shape (64, n_inputs)."""
    inputs = all_inputs(n_features)
    return np.array([task_responses(t, inputs) for t in range(len(LOGIC_TABLES) ** N_DIMS)])


def similarity_matrix(responses):
    """Fraction of inputs with the same response, for every pair of tasks."""
    return (responses[:, None, :] == responses[None, :, :]).mean(axis=2)


def shared_parts(t, known):
    """Number of rule values of task t that occur in the known tasks."""
    if len(known) == 0:
        return 0
    parts = task_parts(t)
    known_parts = [task_parts(k) for k in known]
    return sum(any(kp[d] == parts[d] for kp in known_parts) for d in range(N_DIMS))


def new_parts(t, known):
    return N_DIMS - shared_parts(t, known)


def similarity_to_known(t, known, sim, measure="max", tau=0.1):
    """Similarity of task t to the known set: max, or kernel-weighted mean with weights exp(s / tau)."""
    if len(known) == 0:
        return 0.0
    s = sim[t, list(known)]
    if measure == "max":
        return float(s.max())
    if measure == "kernel":
        w = np.exp((s - s.max()) / tau)
        return float((w * s).sum() / w.sum())
    raise ValueError(f"unknown similarity measure: {measure}")
