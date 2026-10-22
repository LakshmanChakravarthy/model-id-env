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
