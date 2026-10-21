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
- Three rule dimensions, with 4 values each: logic (for example: both, either, neither, not-both), sensory (which feature of each stimulus to check), motor (how the Boolean result maps to a response: one of 2 buttons for TRUE x one of 2 other buttons for FALSE, see "Day 1b" in the Analysis log). This gives 64 tasks, as in C-PRO.
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
- Each design is analysed in two ways (Day 2b): **multiple regression** (cost on both predictors together) and **naive** (each predictor's correlation with cost on its own). This gives four baselines and shows how much of the difficulty is in the design and how much in the analysis.

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
2. **The baselines behave as expected.** The oracle is close to 100% correct, and its designs dissociate the two measures clearly better than random designs (criterion revised in Day 2b: accuracy alone does not separate the baselines, because a moderate confound costs a random design little information).
3. **No leakage.** In the pilot, run one instance with the prompt: "Find out which learner type is hidden, using any method." Claude must not be able to read the source or the server state. If it can, fix the sandbox before the main run.

## Scope

**In scope:** task space, two stylized learners, hard case 1, query interface, scoring, two baselines, headless Claude harness, 20–40 instances, one figure, README.

**Out of scope (next steps, list in the final README):**
- Trained RNN and transformer learners (case 2: the learner does not use the designed parts).
- Case 3: mixtures of mechanisms.
- Deeper rule trees (an outer logic rule over two inner logic-feature rules, for example "if BOTH are red AND EITHER is vertical"). Productive compositional generalization. An exploratory probe (Day 1b) found that they dilute the confound, and that De Morgan equivalences make half of the trees share a mapping with another tree.
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
- Day 1 code: `env/tasks.py`, `env/learners.py`, `env/config.py`, `configs/default.json`, tests in `tests/` (run with `python -m pytest tests`).
- Check 1 ran (see Analysis log). It **failed**: for random training sets there is almost no confound between new parts and similarity.
- Day 1b: motor table changed to the 2x2 design. Check 1 rerun and **passed** (median corr -0.40; dissociations in 98.5% of K). Similarity measure selected: `max`.
- Day 2 code: `env/environment.py`, `env/scoring.py`, `harness/baselines.py`, `analysis/check2_baselines.py`, tests (20 pass).
- Check 2 ran with the declared tuning grid and confirmation. It **failed**: the random baseline stays at 0.80-0.85 or higher; the best gap was +0.165 in tuning and +0.140 in confirmation (needed 0.15).
- Day 2b: criterion revised (accuracy + dissociation + Brier, beside four baselines: {random, oracle} design x {multiple regression, naive} analysis). Check 2 **passed** on a fresh seed, but all four baselines are 100% correct at noise sd 5.

**Pending**
- **Decide before Day 3:** keep noise sd 5 (accuracy at ceiling for every baseline; only the dissociation score separates experimenters) or raise it (Day 2b result).
- Day 3 to day 6 in the plan above.
- Tune the learner parameters and the budget after check 2 (`c_sel` strongly affects how common dissociations are; see Day 1b).

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

**Result (2026-10-21). Check 1 FAILS as declared, and the main expectation was wrong.** Files: `results/checks/check1.json`, `results/checks/check1.png`. Matched `c0` = 35.4 (max) / 34.2 (kernel); `c0` = 35.4 is now in the config, and the numbers below are from the rerun (mean cost 25.9 for both learners).
- (a) Similarity values are as expected ({0, .375, .5, .625, 1}, driven by the motor "hand"). But **there is almost no confound for random K**: the median within-K corr(new_parts, similarity) is -0.03 (range -0.73 to +0.34; pooled -0.09). The confound is strong only when all of K uses one motor hand (12 of 200 random K, median corr -0.65). For the other 188 K, the median corr is -0.02. The reason is that similarity depends on the hand and on logic complements (AND ≡ NAND with the flipped motor map), and neither of these is a count of shared rule values.
- (b) Disagreeing pairs exist for 194 of 200 K (max) and 196 of 200 (kernel), not all 200. Median 195 pairs per K (of 3540). The failures are 4 one-hand K and 2 K in which new parts can only be 0 or 1.
- (c) Max and kernel give the same conclusions.
- The median within-K corr between the two learners' costs is 0.02, so for a random design the two learners already predict nearly unrelated cost profiles.

**Implication.** The premise of hard case 1 ("shared parts and similarity are confounded in most of the task space") does not hold for this task space with random training sets. The confound is a property of some training sets (one-hand K), not of the space. A random experimenter will probably succeed, so check 2 will probably fail ("environment too easy"). Work stops here until the design is changed (a new declare commit).

### Day 1b / redesign of the motor rules and rerun of check 1 (declared 2026-10-21)

**Why.** Check 1 found almost no confound. The cause is the motor table: two disjoint "hands" ({0,1} and {2,3}) make the similarity 0 for 4 of 6 motor pairs, and the flipped maps make (AND, f, m) identical to (NAND, f, flipped m). An exploratory probe (not committed; 200 random K, seed 0, no selection-uncertainty term) compared candidate spaces:

| Space | |K| | Median corr(new parts, sim) | K with corr <= -0.5 | K with a disagreeing pair | Disagreeing pairs (median) | Distinct mappings |
|---|---|---|---|---|---|---|
| Current (hand motor) | 4 | -0.03 | 6% | 97% | 5.5% | 32 / 64 |
| Current + 2x2 motor | 4 | -0.41 | 26% | 87% | 1.0% | 64 / 64 |
| Deeper trees + 2x2, role-bound parts | 4 | -0.22 | 2% | 100% | 8.2% | 768 / 1536 |
| Deeper trees + 2x2, role-bound parts | 8 | -0.07 | 1% | 91% | 0.8% | |
| Deeper trees + hand motor | 4 | -0.06 | 3% | 100% | 9.6% | 384 / 1536 |

**Change.** Only the motor table in `env/tasks.py`. A motor rule = (button for FALSE in {0, 3}) x (button for TRUE in {1, 2}): m0 = F->0/T->1, m1 = F->0/T->2, m2 = F->3/T->1, m3 = F->3/T->2. Learners, similarity, the check-1 procedure, and the other parameters do not change, except that `c0` is matched again as declared in Day 1.

**Revised pass criterion for check 1.** The Day 1 criterion (a disagreeing pair for every K) can fail by construction when the part-based learner predicts flat costs. New criterion: (i) the confound exists: median within-K corr(new_parts, similarity) <= -0.3 under the selected measure; and (ii) dissociations exist: >= 80% of K have at least one disagreeing pair. Note: the threshold in (ii) is set after the probe and is close to the probe value (87%).

**Expected result.** Median corr about -0.4; about 25% of K with corr <= -0.5; about 85% of K with a disagreeing pair, and about 1% of task pairs disagreeing. All 64 mappings distinct; 10 distinct similarity values. Max and kernel give the same conclusions. Matched `c0` changes from 35.4.

**Result (2026-10-21). Check 1 PASSES.** Files: `results/checks/check1.json`, `results/checks/check1.png`. Matched `c0` = 31.8 (max) / 30.2 (kernel); `c0` = 31.8 is now in the config and the numbers are from the rerun (mean cost 25.9 for both learners).
- Confound: median within-K corr(new_parts, similarity) = -0.40 (max) / -0.39 (kernel); range -0.84 to +0.25; 25.5% of K with corr <= -0.5. As expected. The median within-K corr between the two learners' costs is now 0.40 (it was 0.02).
- Dissociations: 197 of 200 K have a disagreeing pair (98.5%), median 117 pairs per K = 3.3% of pairs. **More than expected** (about 85% and 1%). A diagnostic run shows the cause: the probe had no selection-uncertainty term. With `c_sel` = 0 (and `c0` matched again), the check gives 86.5% and 1.0%, the probe values. With `c_sel` = 2, the part-based costs vary more within K, so disagreements are about 3 times as common. `c_sel` is a lever for check 2 if the random baseline is too strong.
- All 64 mappings are distinct; 10 distinct similarity values. Max and kernel give the same conclusions, so by the declared rule the similarity measure is `max`.

### Day 2 / environment, scoring, baselines, check 2 (declared 2026-10-21)

**Will run.** `env/environment.py`, `env/scoring.py`, `harness/baselines.py`, `analysis/check2_baselines.py`. 200 instances (seed 1; learner type alternates, so 100 of each), each run once by the random baseline and once by the oracle.

Design choices fixed here:
- **Environment.** Instance = learner type + seed + a random permutation of the value labels in each dimension. Tasks are named by their labels, for example `L3-S1-M2`. Start with no trained tasks. `train` adds tasks (cost 1 per task); `test` returns one noisy sample (cost 1); `describe` (dimensions, labels, input encoding, and the input-output mapping of a named task) and `budget` are free. There is no reset. Every query and its result go into the log. A verdict ends the instance.
- **Scoring.** (1) correct = 1 if the verdict equals the hidden type (`cannot_decide` = 0). (2) Dissociation = 1 - |corr(new_parts, similarity)| over the unique (task, training state) pairs that were tested, both measured at test time; 0 if there are fewer than 2 such pairs or both measures are constant; 1 if exactly one is constant. (3) Brier = (confidence - correct)^2, where confidence is the probability that the stated verdict is correct; for `cannot_decide` the Brier score is 0.25.
- **Shared analysis for both baselines.** OLS of cost on [1, new_parts, similarity] over all tests. t_parts = t of the new_parts slope, t_sim = -(t of the similarity slope); a constant predictor gets t = 0. Verdict = part-based if t_parts > t_sim, else holistic. Confidence = Phi(|t_parts - t_sim| / sqrt(2)). The baselines compute new parts from the labels and similarity from `describe`, so they use no hidden information.
- **Random baseline.** Train `train_size` = 4 random tasks, then spend the remaining budget on tests of random tasks (with replacement).
- **Oracle.** Draw 200 candidate training sets of size 4. For each, allocate the test budget greedily over the 60 untrained tasks to maximize det(cov([new_parts, similarity])) of the tests (D-optimal for the regression above). Keep the best candidate, train it, and run the allocation. The oracle knows the task structure but not the learner type.

**Pass criterion.** Oracle accuracy >= 0.90, and random accuracy <= oracle accuracy - 0.15.

**Expected result.** At the current parameters (noise sd 5, budget 60, `c_sel` 2): oracle accuracy about 0.98-1.0; random accuracy also high (about 0.85-0.95), because the confound is moderate (median corr -0.4) and the regression controls for both measures. So the check probably **fails as too easy**. Oracle dissociation score clearly above random.

**Tuning rule if it fails (declared now).** Grid: noise sd in {5, 10, 15, 20} x budget in {30, 45, 60} x `c_sel` in {0, 2}, with `c0` matched again for each `c_sel` (same procedure as check 1). Among the settings with oracle accuracy >= 0.90, select the one with the largest gap (oracle - random); ties go to the larger budget. Then rerun check 2 at the selected setting with a new seed (2) to confirm, because selecting on the same seeds overfits. The confirmation run decides pass or fail.

**Known difference from C-PRO (from Day 1b).** With the 2x2 motor table, buttons B1 and B2 always mean TRUE, and B0 and B3 always mean FALSE. In C-PRO a button does not reveal the Boolean. This does not affect the stylized learners.

**Result (2026-10-21). Check 2 FAILS.** Files: `results/checks/check2_main.json`, `check2_grid.json`, `check2_confirm.json`.
- Current config (noise sd 5, budget 60, `c_sel` 2): oracle 1.00, random 1.00. Too easy, as expected. Dissociation score: oracle 0.82, random 0.52.
- Tuning grid (seed 1): the random baseline stays at 0.79 or higher in every setting. Only noise moves it, and noise lowers the oracle too. 3 of 24 settings pass, all at noise sd 20, which is the edge of the grid. Selected by the declared rule: noise sd 20, budget 60, `c_sel` 2 (oracle 0.995, random 0.830, gap +0.165; it ties with budget 30, and ties go to the larger budget).
- Confirmation (seed 2, same setting): oracle 0.990, random 0.850, **gap +0.140 < 0.15. Fail.** With 200 instances per baseline, the standard error of the gap is about 0.03, so the selected setting is on the boundary rather than clearly passing or failing.
- Dissociation score is stable across all settings: oracle 0.82-0.83, random 0.52-0.53.

**Diagnosis.** The random baseline is strong because the confound is moderate. With a median within-K corr of -0.4 between the two predictors, a random design keeps about 1 - 0.4^2 = 84% of the information that an uncorrelated design has about each slope. The multiple regression controls for the confound, so a random design is only somewhat less efficient than the oracle. Noise lowers both accuracies. It does not make the confound matter more. For random designs to fail clearly, the predictors must be strongly correlated in random designs (|corr| of about 0.9 or more). This task space does not have that. The config is unchanged (noise sd 5). Work stops here until the design or the criterion is changed with a new declare commit.

### Day 2b / revised success criterion and naive-analysis baselines (declared 2026-10-21)

**Why.** Check 2 failed (Day 2): with a moderate confound (corr about -0.4), a random design analysed with multiple regression keeps about 84% of the information, so the random baseline is 85-100% correct. Only very high noise (sd 20) brings the accuracy gap near 0.15, and those costs are very erratic. Design quality separates the baselines clearly in every setting (0.82-0.83 vs 0.52-0.53). This is a change of criterion after seeing results; the reason is the diagnosis above.

**Changes.**
- Settings stay as they are: noise sd 5, budget 60, `c_sel` 2, `c0` 31.8. The tuning-grid selection (sd 20) is not used.
- Main measures for every experimenter, Claude included: verdict accuracy, dissociation score (design quality), and Brier score, each reported beside the baselines. Accuracy alone is not the headline.
- New analysis for the baselines, **naive**: Pearson r(cost, new_parts) and r(cost, -similarity), each on its own (a constant predictor gets r = 0). Verdict = the larger r. Confidence = Phi((atanh r_parts - atanh r_sim) * sqrt((n - 3) / 2)), taken for the stated verdict. Four baselines: {random, oracle} design x {multiple regression, naive} analysis. Same instance seeds, so the paired design runs see the same noise.
- New check 2 pass criterion: oracle (multiple regression) accuracy >= 0.90, and mean dissociation oracle - random >= 0.20. Note: this criterion is set after the Day 2 runs showed 1.00 and 0.82 vs 0.52, so it is a sanity check on a fresh seed, not an independent test.
- `analysis/check2_baselines.py final` runs it on a fresh seed (`final_seed` = 3).

**Expected result.** Oracle accuracy about 1.0; random (multiple) about 1.0; dissociation 0.82 vs 0.52, so the check passes. Naive analysis: the marginal correlation of the true predictor includes its own effect, and the other predictor gets only the part that comes through the -0.4 correlation, so naive accuracy is also high at noise sd 5 (about 0.9-1.0), with the random-naive pair the lowest of the four. Brier is worst for random-naive.

**Consequence for the main claim.** In this environment, a weak design costs little accuracy when the analysis is good. So the comparison of Claude with the baselines rests mainly on the dissociation score and calibration, and on accuracy only where Claude falls below the random baseline.

**Result (2026-10-21). Check 2 PASSES under the Day 2b criterion** (`results/checks/check2_final.json`, seed 3, 200 instances per baseline):

| Baseline | Accuracy | Dissociation | Brier |
|---|---|---|---|
| Random design, multiple regression | 1.000 | 0.53 | 0.000 |
| Oracle design, multiple regression | 1.000 | 0.83 | 0.000 |
| Random design, naive | 1.000 | 0.53 | 0.001 |
| Oracle design, naive | 1.000 | 0.83 | 0.000 |

- Dissociation gap 0.30 (needed 0.20); oracle accuracy 1.00 (needed 0.90).
- **Not as expected:** the naive analysis is also 100% correct with a random design. I expected about 0.9-1.0 and the lowest of the four; it is at ceiling. At noise sd 5 with 56 tests, every baseline gets every verdict right with near-certain confidence.
- **Consequence.** At these settings, verdict accuracy and Brier cannot separate experimenters; only the dissociation score does. The hypothesis in CLAUDE.md ("a weak experimenter's verdicts are close to chance or overconfident") cannot show up in accuracy here. A noise level where random designs fall below ceiling (sd 10-15 gave random 0.85-0.95 in the Day 2 grid) would make accuracy and calibration informative again. That needs a decision and a declare commit before any Claude run.

## Handover prompt

> I am building `model-id-env`, a prototype environment for my Anthropic Conceptual Reasoning Fellowship application (deadline 2026-10-28). Claude acts as an experimenter and must identify a hidden learner mechanism (part-based or holistic) on a C-PRO-like task space of 64 rule combinations. It does this by designing train and test queries under a budget. The main difficulty is hard case 1: shared parts and overall similarity are confounded in most of the task space. Read README.md and CLAUDE.md first. The README has the design, the known-answer checks, the day plan, and the current status. Continue from the first pending item in "Current status." Use the simplest modular Python code that works. Do not add scope from the "out of scope" list unless I ask.
