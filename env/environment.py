"""One instance: a hidden learner, a seed, and permuted labels. Logs every query.

The experimenter sees tasks only by label names such as "L3-S1-M2".
"""
import numpy as np

from env import learners, tasks

DIM_PREFIXES = ["L", "S", "M"]
DIM_NAMES = ["logic", "sensory", "motor"]
VERDICTS = ["part-based", "holistic", "cannot_decide"]


class Environment:
    def __init__(self, learner, seed, cfg):
        if learner not in ("part_based", "holistic"):
            raise ValueError(f"unknown learner: {learner}")
        self.learner = learner
        self.seed = seed
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        # label_of[d][true value] = public label index (1..4)
        self.label_of = [self.rng.permutation(cfg["tasks"]["n_values"]) + 1 for _ in range(tasks.N_DIMS)]
        self.responses = tasks.response_matrix(cfg["tasks"]["n_features"])
        self.sim = tasks.similarity_matrix(self.responses)
        self.inputs = tasks.all_inputs(cfg["tasks"]["n_features"])
        self.budget = cfg["environment"]["budget"]
        self.known = []
        self.log = []
        self.verdict = None

    # --- names ---
    def name(self, t):
        return "-".join(f"{DIM_PREFIXES[d]}{self.label_of[d][v]}" for d, v in enumerate(tasks.task_parts(t)))

    def task_of(self, name):
        try:
            labels = name.strip().split("-")
            assert len(labels) == tasks.N_DIMS
            parts = []
            for d, lab in enumerate(labels):
                assert lab[0] == DIM_PREFIXES[d]
                parts.append(int(np.where(self.label_of[d] == int(lab[1:]))[0][0]))
            return tasks.task_id(*parts)
        except (AssertionError, ValueError, IndexError):
            raise ValueError(f"bad task name: {name!r}")

    # --- queries ---
    def _record(self, query, args, result):
        self.log.append({"i": len(self.log), "query": query, "args": args, "result": result,
                         "budget_after": self.budget, "n_known": len(self.known)})
        return result

    def _check_open(self):
        if self.verdict is not None:
            raise RuntimeError("instance is finished")

    def train(self, names):
        self._check_open()
        ids = [self.task_of(n) for n in names]
        cost = self.cfg["environment"]["train_cost_per_task"] * len(ids)
        if cost > self.budget:
            return self._record("train", list(names), {"error": "not enough budget"})
        self.budget -= cost
        for t in ids:
            if t not in self.known:
                self.known.append(t)
        return self._record("train", list(names), {"trained": [self.name(t) for t in self.known]})

    def test(self, name):
        self._check_open()
        t = self.task_of(name)
        cost = self.cfg["environment"]["test_cost"]
        if cost > self.budget:
            return self._record("test", [name], {"error": "not enough budget"})
        self.budget -= cost
        c = learners.sample_cost(self.learner, t, list(self.known), self.cfg, self.sim, self.rng)
        return self._record("test", [name], {"examples_to_criterion": c})

    def describe(self, name=None):
        if name is None:
            n_values = self.cfg["tasks"]["n_values"]
            result = {
                "dimensions": {DIM_NAMES[d]: [f"{DIM_PREFIXES[d]}{i}" for i in range(1, n_values + 1)]
                               for d in range(tasks.N_DIMS)},
                "task_name_format": "L?-S?-M?",
                "n_tasks": n_values ** tasks.N_DIMS,
                "inputs": "a pair of stimuli, each with n binary features; written as two bit strings 'stim1 stim2'",
                "n_features": self.cfg["tasks"]["n_features"],
                "responses": sorted(int(r) for r in np.unique(self.responses)),
            }
            return self._record("describe", [], result)
        t = self.task_of(name)
        mapping = {self.input_string(i): int(self.responses[t, i]) for i in range(len(self.inputs))}
        return self._record("describe", [name], {"task": name, "mapping": mapping})

    def get_budget(self):
        return self._record("budget", [], {"budget": self.budget})

    def submit(self, verdict):
        self._check_open()
        if verdict.get("verdict") not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        conf = float(verdict.get("confidence", -1))
        if not 0.0 <= conf <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        self.verdict = {"verdict": verdict["verdict"], "confidence": conf,
                        "justification": str(verdict.get("justification", ""))}
        return self._record("submit", [], self.verdict)

    def input_string(self, i):
        x = self.inputs[i]
        return " ".join("".join(str(int(b)) for b in stim) for stim in x)

    # --- for scoring only (uses hidden state) ---
    def test_events(self):
        """(task id, known tasks at test time) for every successful test, in order."""
        events, known = [], []
        for e in self.log:
            if e["query"] == "train" and "trained" in e["result"]:
                known = [self.task_of(n) for n in e["result"]["trained"]]
            elif e["query"] == "test" and "examples_to_criterion" in e["result"]:
                events.append((self.task_of(e["args"][0]), tuple(known), e["result"]["examples_to_criterion"]))
        return events
