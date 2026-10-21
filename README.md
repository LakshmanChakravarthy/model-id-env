# model-id-env

A small environment that tests whether Claude can identify a hidden learning mechanism by designing experiments. The ground truth is known, so the scoring is automatic.

This is a prototype for an application to the Anthropic Conceptual Reasoning Fellowship (deadline: 2026-10-28).

## The question

Cognitive scientists often must select between mechanisms that predict similar behavior. This environment uses one example: how does a learner transfer to new combinations of known parts?

- **Part-based account.** The learner stores reusable parts. A new combination of known parts transfers quickly, even when the whole task is dissimilar to known tasks.
- **Holistic account.** The learner represents each task as one whole. Transfer follows overall similarity to known tasks.

In most task spaces, the number of shared parts and overall similarity are correlated. Then both accounts predict the same result. A good experimenter must find the tasks where the two measures disagree. This is **hard case 1 (the confound)**, and it is the only hard case in this prototype.

## Design

### Task space (`env/tasks.py`)
- Three rule dimensions, with 4 values each: logic (for example: both, either, neither, not-both), sensory (which feature of each stimulus to check), motor (how the Boolean result maps to a response). This gives 64 tasks, as in C-PRO.
- Inputs: a small discrete set of stimulus pairs (for example, 2 stimuli × 4 binary features). Each task is a full mapping from inputs to responses. It is computed by the composition: sensory rule → two bits → logic rule → one Boolean → motor rule → response.
- **Shared parts** between task T and a set of known tasks K: the number of rule values of T that occur in K. Also record **new parts** = 3 − shared parts.
- **Overall similarity** between two tasks: the fraction of inputs with the same response. Similarity of T to K = the maximum over K (also compute the kernel-weighted mean, and select one before the main run).

### Learners (`env/learners.py`)
Stylized learners. Each mechanism is true by construction. (Trained RNN learners are a next step, not part of this prototype.)
- **PartBasedLearner.** Cost of a new task = `c_new × new_parts + c_sel × selection_uncertainty + noise`. Selection uncertainty is small when all parts are known.
- **HolisticLearner.** Cost of a new task = `c0 × (1 − similarity_to_known)^alpha + noise`. It ignores parts.
- Both return **examples to criterion** for a test task, given the tasks that they were trained on. Noise is Gaussian or Poisson, so the experimenter needs repeated measures and statistics.
- Free parameters (`c_new`, `c0`, `alpha`, noise level) are set so that the two learners give **similar mean costs over a random set of tasks**. Otherwise a trivial strategy solves the environment.

### Environment (`env/environment.py`)
- An **instance** = a hidden learner type + random seed + random permutation of the rule labels (so that names do not reveal structure).
- Queries (each costs budget):
  - `train <task_ids>`: add tasks to the learner's experience.
  - `test <task_id>`: return the examples-to-criterion for one task, given the current experience. Repeating a test gives a new noisy sample.
  - `describe`: return the task space (rule dimensions, rule values with permuted labels, and the input-output mapping of any task on request).
  - `budget`: return the remaining budget.
- Total budget: for example, 60 queries. Tune it in the pilot.
- At the end the experimenter submits a **verdict** (JSON):
  ```json
  {"verdict": "part-based | holistic | cannot_decide",
   "confidence": 0.0,
   "justification": "..."}
  ```
- The environment logs every query. The experimenter cannot change the log.

### Scoring (`env/scoring.py`)
1. **Verdict correct**: 1 or 0.
2. **Dissociation score**: computed from the logged test tasks. `1 − |corr(new_parts, similarity)|` over the tasks that the experimenter tested. High = the design separated the two measures.
3. **Calibration**: Brier score of the confidence.

### Baselines (`harness/baselines.py`)
- **Random experimenter**: random train set, random tests, then regresses cost on new parts and on similarity, and selects the predictor with the larger effect.
- **Oracle design**: selects the tasks that dissociate parts from similarity, then applies the same regression. This is an upper bound on what the budget allows.

### Running Claude (`harness/run_claude.py`)
Claude runs as the experimenter through **Claude Code headless** (`claude -p`).
- For each instance, the harness makes a new **sandbox directory outside the repo** (for example `/tmp/model-id-sandbox/<instance_id>/`). It contains only `prompt.md` and a thin client `query.py`.
- `query.py` sends each command to an **environment server** process that the harness starts from the repo (for example, a local socket or HTTP on localhost). The hidden learner type exists only in the server process.
- Claude's tools are restricted to that one command, with `--allowedTools`, and the other tools are disallowed (Read, Glob, Grep, Edit, Write, WebFetch, and other Bash commands). Check the exact flag syntax with `claude --help` before you write the harness.
- Use `--output-format json` to capture the final answer, and `--max-turns` as a safety limit.
- The prompt states the two hypotheses, the tools, the budget, and the verdict format. It does **not** mention the confound. Finding it is the test.

### Analysis (`analysis/figures.py`)
- One main figure: verdict accuracy and dissociation score for Claude, the random baseline, and the oracle, for each learner type.
- One example transcript of a good design and one of a failure, for the README.

## Checks (known-answer checks before any Claude run)

1. **The dissociation exists.** Over all 64 tasks, plot cost against new parts and against similarity, for both learners. Confirm that some tasks make the two learners disagree. If no such tasks exist, nothing can solve the environment.
2. **The baselines behave as expected.** The oracle is close to 100% correct. The random baseline is clearly lower. If the random baseline is already near 100%, the environment is too easy: tune the parameters.
3. **No leakage.** In the pilot, run one instance with the prompt: "Find out which learner type is hidden, using any method." Claude must not be able to read the source or the server state. If it can, fix the sandbox before the main run.

## Scope

**In scope:** task space, two stylized learners, hard case 1, query interface, scoring, two baselines, headless Claude harness, 20–40 instances, one figure, README.

**Out of scope (next steps, list in the final README):**
- Trained RNN and transformer learners (case 2: the learner does not use the designed parts).
- Case 3: mixtures of mechanisms.
- Case 4: a holistic learner with a factorized similarity metric, which gives the same behavior as the part-based learner. The correct verdict is `cannot_decide`. (Add this first if time permits.)
- Expert rubric scoring of the justification text.
- The extension: run the same dissociation on Claude's in-context learning.

## Plan

| Day | Date | Work |
|---|---|---|
| 1 | Thu 10-22 | `tasks.py`, `learners.py`. Check 1. |
| 2 | Fri 10-23 | `environment.py`, `scoring.py`, baselines. Check 2. |
| 3 | Sat 10-24 | Environment server, `query.py`, `run_claude.py`. Check 3. Pilot on 3 instances. |
| 4 | Sun 10-25 | Main run: 20–40 instances, both learner types balanced. |
| 5 | Mon 10-26 | Figure, transcripts, final README. Case 4 if time permits. |
| 6 | Tue 10-27 | Buffer. Make the repo public. Add the link to the application. |

Note: the headless runs use the Claude subscription, so usage limits apply. Start with 20 instances, and add more if the limits allow.

## Repo structure

```
model-id-env/
  README.md
  CLAUDE.md
  env/
    tasks.py
    learners.py
    environment.py
    server.py
    scoring.py
  harness/
    query.py          # copied into each sandbox
    prompt.md         # experimenter prompt template
    run_claude.py
    baselines.py
  analysis/
    figures.py
  tests/
  results/            # one JSON per instance: config, query log, verdict, scores
  configs/
```

## Current status

**Completed**
- Scope and design (this README).

**Pending**
- Day 1 to day 6 in the plan above.
- Decide the similarity measure (maximum or kernel-weighted mean) after check 1.
- Tune the learner parameters and the budget after check 2.

## Analysis log

### Day 1 / check 1 (declared 2026-10-21)

**Will run.** `env/tasks.py` (64 tasks; 2 stimuli x 4 binary features = 256 inputs; logic = AND, OR, NOR, NAND; sensory = feature index checked in both stimuli; motor = 4 maps of the Boolean to 4 responses, two per "hand": T->0/F->1, T->1/F->0, T->2/F->3, T->3/F->2). `env/learners.py` (noise-free mean cost and noisy samples for both learners). `analysis/check1_dissociation.py` with `configs/default.json`: draw 200 random training sets K of 4 tasks (seed 0); for every test task T not in K compute new parts, similarity (max and kernel-weighted mean), and the mean cost of each learner.

Definitions fixed here:
- Part-based mean cost = `base + c_new * new_parts + c_sel * selection_uncertainty`, where selection_uncertainty = sum over the dimensions whose value of T is known of log2(number of known values in that dimension) (the entropy of picking the right stored part).
- Holistic mean cost = `base + c0 * (1 - sim)^alpha`.
- Noise: Gaussian, sd `noise.sd`, rounded, floored at `min_cost`.
- Kernel-weighted mean similarity: weights `exp(sim_k / tau)`.
- `c0` is set so that the two learners have the same mean cost over the check-1 distribution (K random of size 4, T random outside K). The script reports the matched value; it goes into the config and the check is rerun.
- A **disagreeing pair** for a given K = two test tasks A, B such that the part-based learner predicts A cheaper than B by more than 1 noise sd and the holistic learner predicts B cheaper than A by more than 1 noise sd.

**Expected result.** (a) Similarity takes few values ({0, .375, .5, .625, 1}) and is driven mostly by the motor "hand", so corr(new_parts, similarity) over test tasks is negative, magnitude roughly 0.3-0.8 (the confound). (b) Disagreeing pairs exist for every K (pass criterion: >0 for all 200 K). Clear examples: T = (NAND, f, T->1/F->0) has the same mapping as a known (AND, f, T->0/F->1) (similarity 1) but has 2 new parts. (c) Under the same measure, max and kernel similarity give similar conclusions.

**Decision rule for the similarity measure.** Use `max` (nearest known task), unless check 1 fails under `max` and passes under `kernel`.

## Handover prompt

> I am building `model-id-env`, a prototype environment for my Anthropic Conceptual Reasoning Fellowship application (deadline 2026-10-28). Claude acts as an experimenter and must identify a hidden learner mechanism (part-based or holistic) on a C-PRO-like task space of 64 rule combinations. It does this by designing train and test queries under a budget. The main difficulty is hard case 1: shared parts and overall similarity are confounded in most of the task space. Read README.md and CLAUDE.md first. The README has the design, the known-answer checks, the day plan, and the current status. Continue from the first pending item in "Current status." Use the simplest modular Python code that works. Do not add scope from the "out of scope" list unless I ask.
