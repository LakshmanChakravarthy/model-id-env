# Two example runs

Both runs are from the Day 4 main run (`claude-opus-5-5`, budget 60, noise sd 15). Full records are in `results/<instance>.json`, and full transcripts are in `results/transcripts/<instance>.jsonl`. The task labels are permuted per instance, so `L4` in one run is not `L4` in another.

"New rules" = the test task's rules that are not part of any trained task. "Overlap" = the largest fraction of inputs on which the test task gives the same response as a trained task (what `compare` returns). The holistic learner's similarity in the main condition is this overlap.

---

## Good design: `main-005` (main condition, part-based learner)

Selected by a fixed rule declared before looking (Day 5): among main-condition runs that were correct and contained a decisive pair, the one with the highest dissociation score.

**What Claude did.** First, it used the free `describe` and `compare` commands to search the task space ("Searching for task pairs where the two hypotheses predict opposite outcomes (free compares) before spending budget"). It found that `L4` gives the opposite answer to `L1`, and that motor rules `M1` and `M4` use disjoint buttons. Then it trained `L1-S1-M1` and `L4-S2-M4`, and tested:

| Test task | New rules | Overlap | Tests | Mean examples to criterion |
|---|---|---|---|---|
| L4-S1-M1 (before training) | 3 | 0 | 3 | 30.3 |
| **L4-S1-M1** | **0** | **0.00** | 9 | **20.2** |
| L1-S1-M2 | 1 | 0.75 | 9 | 29.4 |
| L2-S3-M3 | 3 | 0.19 | 9 | 43.3 |
| L2-S3-M2 | 3 | 0.56 | 9 | 46.0 |

**Verdict:** part-based, confidence 0.88 (correct; Brier 0.014). It used 41 of 60 budget units.

> "L4-S1-M1 has 0 new rules but 0 percent overlap with both trained tasks (L4 negates L1, and the motor button sets do not overlap). [...] The recombined task with 0 overlap was learned fastest, and the two 3-new-rule tasks were equal despite very different overlap. [...] Holistic predicts the opposite: the 0-overlap task slowest and L2-S3-M2 faster than L2-S3-M3."

**Why this is a good design.**
- **It separates the two measures completely.** Across the tested conditions, the correlation between new rules and overlap is 0, so the dissociation score is 1.0.
- **Its key task needed a deduction.** `L4-S1-M1` is built only from known rules, yet it shares no response with either trained task. Building it required working out the structure of the task space from free queries.
- **The predictions are opposite, not merely different.** The two hypotheses predict opposite orderings, and the design includes the baseline measurement taken before training.
- **The baselines on the same instance did less.** The random design was also correct here, but scored 0.35 on dissociation and had no decisive pair. The D-optimal design scored 0.81, without the staged pre/post structure.

---

## Failure: `case4-001` (case-4 condition, part-based learner)

Chosen together with the user, because the justification shows the failure most clearly. In the case-4 condition, the holistic hypothesis says that the learner's similarity measure is unobserved. A holistic learner whose similarity counts shared rules predicts the part-based pattern exactly. So part-based-looking data cannot identify part-based, and the correct verdict is `cannot_decide`.

**What Claude did.** It trained three tasks with no shared rules (`L1-S1-M1`, `L2-S2-M2`, `L3-S3-M3`) and tested recombinations against tasks with new rules:

| Test tasks | New rules | Overlap | Tests | Mean examples to criterion |
|---|---|---|---|---|
| L1-S2-M3, L1-S1-M2, L3-S1-M2 | 0 | 0.56-0.63 | 15 | about 21 |
| L1-S1-M4, L4-S2-M3, L2-S4-M1 | 1 | 0.38-0.75 | 12 | about 37 |
| L4-S4-M1 | 2 | 0.38 | 4 | 36.8 |
| L4-S4-M4 | 3 | 0.56 | 10 | 36.9 |

**Verdict:** part-based, confidence 0.80 (incorrect; Brier 0.64).

> "Cost tracked whether any rule was new, not surface similarity. L1-S1-M4 had the highest response overlap with a trained task (0.75) and shares two rules with it, yet it was among the most costly. [...] Caveats: cost did not rise from 1 to 3 new rules, the noise is large, and **a holistic learner whose hidden similarity measure is aligned with the rules cannot be fully ruled out.**"

**Why this is a failure, and what kind.**
- **The design is competent.** The 0-new-rule tasks have similar or lower overlap than the 1-new-rule tasks, and the experiment shows clearly that cost does not follow output overlap.
- **The inference oversteps.** Ruling out *overlap-based* similarity does not rule out holistic, because the prompt says the learner's similarity measure is unobserved. Claude states this alternative itself, and treats it as a caveat rather than as a reason to answer `cannot_decide`.
- **It is not a lack of knowledge.** In the comprehension control (Day 4b), Claude got the same wording and comparable data with no experiment to run, and answered `cannot_decide` in 5 of 5 runs. It has the concept, but does not apply it while experimenting.
- **The baselines on the same instance:** the D-optimal and random designs with the standard analysis also answered part-based (wrong). With the aware analysis, both were correct.

---

# Study 2: the factor-when-justified learner

In Study 2 there are three hypotheses: part-based, holistic, and factor-when-justified. The last one stores whole tasks and turns a rule into a reusable part only once the rule has appeared in k = 2 or 3 trained tasks. "Rule counts" = how many trained tasks contain each of the test task's rules. "Design score" = the exact posterior probability of the true learner given the run's own data.

## Good design: `s2main-024` (factor learner, k = 3)

Selected by a fixed rule: among factor-learner runs that Claude got right, the highest design score (0.999).

| Stage | Trained (cumulative) | Test task | Rule counts | Overlap | Tests | Mean |
|---|---|---|---|---|---|---|
| 1 | L1-S1-M1, L4-S2-M3 | **L4-S1-M1** (target) | 1, 1, 1 | 0.00 | 6 | 28.7 |
| 1 | | L3-S4-M2 (control, all new) | 0, 0, 0 | 0.19 | 5 | 28.6 |
| 1 | | L2-S3-M4 (control, all new, more similar) | 0, 0, 0 | 0.56 | 4 | 23.5 |
| 2 | + L4-S1-M3, L1-S2-M1 | **L4-S1-M1** | 2, 2, 2 | 0.375 | 4 | 31.8 |
| 3 | + L4-S1-M4, L1-S3-M1 | **L4-S1-M1** | 3, 3, 3 | 0.375 | 8 | **12.1** |
| 3 | | L3-S4-M2 (control) | 0, 0, 0 | 0.19 | 4 | 27.8 |

**Verdict:** factor-when-justified, 0.85 (correct; ideal posterior 0.999).

> "Recombination became cheap only once the rules had appeared 3 times, and this was not explained by similarity. This fits factor-when-justified with k=3, not holistic."

**Why it's good.**
- **It is the scripted before/after design, improved.** At every stage, Claude adds training tasks that raise each of the target's rule counts by one. It keeps the target's similarity to the trained tasks capped at 0.375, so the holistic account predicts no change.
- **It adds a control task.** The control has only new rules and is tested before and after, to rule out general drift.
- **It walks the threshold explicitly.** "No drop at 2" rules out k = 2; "sharp drop at 3" identifies k = 3.

## Inference failure: `s2main-009` (part-based learner)

Selected by a fixed rule: among the 4 inference errors (the ideal analysis of Claude's data is right, Claude is not), the highest design score. Here the ideal posterior gives 0.97 to part-based.

| Stage | Test task | Rule counts | Overlap | Tests | Mean | Part-based predicts |
|---|---|---|---|---|---|---|
| 1 | L3-S1-M2 | 1, 1, 1 | 0.375 | 8 | 16.0 | cheap (all rules known) |
| 1 | L2-S1-M3 | 1, 1, 1 | 0.375 | 5 | 24.8 | cheap |
| 1 | L4-S4-M4 | 0, 0, 0 | 0.19 | 8 | 26.5 | expensive (3 new) |
| 2 | L4-S4-M4 | 3, 3, 3 | 0.375 | 6 | 23.5 | now cheap |
| 2 | L3-S1-M1 | 3, 4, 5 | 0.56 | 5 | 15.4 | cheap |
| 2 | L2-S3-M3 | 2, 1, 1 | 0.50 | 5 | 27.4 | cheap |

**Verdict:** factor-when-justified, 0.40 (incorrect).

> "The 25 for L2-S1-M3 argues against part-based. [...] its mean moved only from 26.5 to 23.5. [...] L3-S1-M1, whose rules had each appeared 3 or more times, gave a mean of 15 [...] L2-S3-M3, whose rules had appeared once or twice, gave a mean of 27 [...]. That favors factoring only after repeated exposure. The overall evidence is weak."

**What went wrong.**
- **The design was good** (design score 0.97). The error is in weighing the evidence.
- **Claude treats single noisy means as decisive.** With 5 tests and a test-to-test sd of 15, a mean has a standard error of about 7. Each contrast Claude cites is within about 1.5 standard errors, but taken together the data strongly favour part-based.
- **It is visible to Claude.** Its confidence (0.40) was low.
- **The control rescued this one.** In the inference-only control (same data as a table, no experiment), Claude answered part-based (0.72), correctly. It is the only one of the 4 inference errors that the control rescued; the other 3 were repeated with the same reasoning.
