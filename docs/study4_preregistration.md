# Study 4 preregistration: do models discover the abstract structure of a compositional world?

Committed 2026-10-22, before any Study 4 Claude call (including the pipeline pilot). Changes after this commit are listed at the end with their dates and reasons.

## 1. Question

Studies 3a-3e showed that `claude-opus-5-5` composes like an ideal learner when the space of possible parts is stated. Its failures come one level up: it does not reliably discover the *regularities across components* that tell it how the parts work, and the label format seems to shape which regularities it considers. Study 4 asks: **when a composition is ambiguous unless the learner knows a regularity that holds across components, does Claude discover that regularity from data, use it, and trust it as much as the evidence warrants? And does the surface format of the labels shape which regularities it finds?**

## 2. Task and grammar

Flat tasks over inputs made of two 4-bit stimuli.
- A **Y** component picks one of 4 features, checked in both stimuli.
- An **X** component is one of 6 symmetric rules on the two bits: both are 1; at least one is 1; exactly one is 1; neither is 1; not both are 1; both are the same.
- A **Z** component gives one button when the rule is true and a different button when it is false.
- Labels (X1, Y2, Z3, ...) are arbitrary, and the same label always means the same component.

The prompt states this form, not which version does what. Each instance shows 6 known tasks with 24 examples each, then asks for 16 predictions for a new task, with no examples of it, built from known components.

**Ambiguity by construction.** Complementing every X rule (both 1 <-> not both 1; at least one <-> neither; exactly one <-> both the same) and swapping every Z's buttons leaves every task unchanged. Components that never co-occur can therefore be flipped independently. Every test task is chosen so that, without a regularity, exactly **two** answer vectors fit all the examples.

## 3. Regularities (one per world, or none)

Each has the same logical form: property P holds for every component, in one consistent orientation. That resolves the relative flip.

| Type | P | Visible with digit buttons | Visible with colour buttons |
|---|---|---|---|
| **Categorical** | the buttons split into two classes of two; every Z maps FALSE into one class and TRUE into the other | yes | yes |
| **Ordinal** | every Z's TRUE button is higher than its FALSE button | yes | **no** (colours have no order) |
| **Polarity** | every X rule is false when neither bit is 1 (both 1, at least one 1, exactly one 1) | yes | yes |

Regular worlds carry exactly one regularity. Their other components are generated so that the other two regularities do not hold. Irregular worlds carry none.

## 4. Ideal learner (the reference answer)

Hierarchical, with a uniform prior over the hypotheses available in the label format: {none, categorical, ordinal, polarity} with digits; {none, categorical, polarity} with colours.
- **Categorical:** 6 equally likely (split, orientation) choices.
- **Ordinal:** up or down.
- **Polarity:** positive or negative rules.
- **None:** any of the 6 rules and any pair of distinct buttons.

Within a hypothesis, the prior is uniform over injective label meanings. The posterior over the two answer vectors is exact (enumeration; `harness/study4.py`).

## 5. Instances and cells

Exploratory simulations (`results/checks/study4_simulation.json`, 120 instances per type x world, no Claude calls) gave ideal posteriors of 0.99 / 0.91 / 0.83 (categorical), 0.95 / 0.87 (ordinal), and 0.92 / 0.78 (polarity) in regular worlds. About 35% of irregular worlds contain an *accidental* regularity that the ideal learner rationally uses. These are excluded below. Instances are generated with seed 40000, with the following selection rules.

- **Regular, high evidence:** ideal posterior (digits) >= 0.90, and the modal answer equals the truth.
- **Regular, moderate evidence:** ideal posterior (digits) in [0.75, 0.90), and the modal answer equals the truth.
- **Format conditions on regular instances:**
  - categorical and polarity: the colour-format ideal must fall in the same band;
  - ordinal: the colour-format ideal must be in [0.45, 0.55] (the regularity is invisible with colours).
- **Irregular:** ideal posterior <= 0.55 in both formats.

Cells: 3 types x {high, moderate, irregular} = 9 instance pools, **16 instances each** (144 instances). Every instance is run in all 4 variants (paired):
- **format:** digits / colour names, a random permutation of red, green, blue, yellow per instance;
- **prompt:** base / pattern.

That is **576 calls** to `claude-opus-5-5`, with no tools, one answer per call.

- **Base prompt:** the grammar, the known tasks, the test, the instruction from Study 3d ("Before you answer, write down every way of assigning meanings to the components that fits all the examples, not only the first one you find. Check each candidate against all the known tasks. Base your predictions, \"determined\", and your confidence on all the assignments that fit."), and the answer format `{"predictions": [...], "determined": true/false, "confidence": p}`. Including the alternatives instruction in every condition removes alternative neglect (fixed in 3d) as a confound.
- **Pattern prompt:** base plus "Also look for patterns that hold across all the components you can identify, and consider whether such a pattern makes some of the fitting assignments more plausible than others." This is neutral about where to look, unlike 3d's "in how the buttons are used".

## 6. Measures

- **Primary (behavioural):** **R** = Claude's predictions match the ideal modal (regularity-consistent) answer vector on >= 14 of 16 items. Also recorded: confidence and "determined".
- **Secondary (coded):** a grader (`claude-opus-5-5`, fixed rubric, sees only the response text) codes:
  - `regularity_stated` (none / categorical / ordinal / polarity / other);
  - `regularity_used` (used it to prefer one answer);
  - `alternatives_considered`.
- **Grader validation:** the user hand-codes 40 responses sampled at random, stratified by type and prompt, blind to the grader's codes. We report Cohen's kappa on `regularity_stated` (type vs. none). If kappa < 0.6, the coded measures are reported as unreliable and not interpreted.

Unparsed responses are excluded and counted. Failed launches are rerun; nothing else is rerun.

## 7. Hypotheses and tests (confirmatory)

**Visible cells** = regular cells, excluding ordinal with colours.

- **H1, label format gates the hypothesis space.** For **categorical** regular instances, R is higher with colours than with digits. Test: paired by instance and prompt, exact McNemar, one-sided.
- **H2, prompted vs. spontaneous discovery.** In visible cells, R is higher with the pattern prompt than with the base prompt. Test: paired exact McNemar, one-sided.
- **H3, under-trust.** In visible cells where Claude gave the modal answer, its confidence is below the ideal posterior: mean (ideal - confidence) > 0. Test: Wilcoxon signed-rank, one-sided.
- **H4, few confident false discoveries.** In irregular cells, the proportion of runs with "determined" true or confidence >= 0.7 is below 0.15. Test: exact binomial, one-sided, against 0.15.

Holm correction over H1-H4 at alpha = 0.05.

**Secondary and descriptive** (no correction; reported with 95% intervals):
- (a) **format control:** polarity R with digits vs. colours (expected: no difference);
- (b) ordinal with digits: R vs. 0.5;
- (c) ordinal with colours: R near 0.5 (by design);
- (d) confidence by evidence band compared with the ideal;
- (e) coded false discoveries in irregular cells, by format (expected: more spurious ordinal claims with digits);
- (f) R by type and prompt.

## 8. Predictions (from Studies 3c-3e)

- H1 holds (3e: 5/8 vs. 2/8).
- H2 holds.
- H3 holds (3e: about 0.7 vs. the ideal 0.99).
- H4 holds.
- Polarity shows no format effect.
- Ordinal with digits: R > 0.5, because Claude's search favoured ordinal patterns in 3d.
- I expect overall discovery to stay well below the ideal: regular-cell R with the pattern prompt about 0.6.

## 9. Pilot

Before the main run: 12 calls on separate instances (seed 40999), one per type x format x prompt for regular-high, to check generation, prompts, parsing, and the grader. Pilot outcomes are not analysed and do not change the hypotheses. Only pipeline bugs may be fixed, and any fix is listed below.

## 10. Changes after this commit

- **2026-10-22, before any main-run result: secondary analysis (g) added.** While checking the analysis code on the pilot's pipeline output, I noticed that H3 as defined counts every run that gave the modal answer. That includes runs that picked it by chance at confidence 0.5 without discovering the regularity, which would inflate "under-trust". **H3 is unchanged and stays confirmatory.** The added secondary analysis (g) repeats it on runs where the grader codes `regularity_used` = true. No pilot outcome was used to choose this; it follows from the definition.
- **2026-10-23, before running the analysis: the grader validation is skipped (user decision).** The user decided not to hand-code the 40-response sample. Consequence: the grader-coded measures (`regularity_stated`, `regularity_used`, `alternatives_considered`; secondary analyses (e) and (g) and the coded tables) are reported as **unvalidated codes from `claude-opus-5-5`**, the same model family as the subject, with no reliability estimate. The confirmatory tests H1-H4 are behavioural and unaffected.
