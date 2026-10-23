# Study 5 preregistration: Claude interprets cognitive experiments on compositional task learning

Committed 2026-10-23, after the user's review of the sample reports (`docs/study5_sample_reports.md`; "all the accounts look good"; no changes requested to accuracy levels, standard errors, or design scale) and before any Study 5 Claude call. Changes after this commit are listed at the end with their dates and reasons.

## 1. Question

Studies 1-4 (artificial environments) identified failure signatures: alternative neglect, confidence that does not track evidence, and selection of the wrong kind of structure. They also found a remedy ("consider alternatives"). Study 5 asks whether these show up when Claude does a task scientists do in the user's field: **interpreting the results section of a C-PRO-style experiment on rapid instructed task learning, and judging whether participants rely on compositional or conjunctive representations.**

## 2. Materials

`env/cpro.py` (generative model, ideal reader) and `harness/study5.py` (report text, prompt).

- **Simulated experiments:**
  - 32 participants;
  - 4 practiced tasks covering all 12 rules (6 practice blocks);
  - a test phase with the practiced tasks and 18 novel tasks: 9 sharing 2 rules with a practiced task (3 each with the logic, sensory, or motor rule differing) and 9 sharing 1 rule;
  - every novel task appears 3 times (2nd occurrence after a short lag of 1-2 or a long lag of 8-12 intervening mini-blocks; 3rd after 8-12).
- **Simulated participants:** dual-route (composition by reconfiguring the practiced task sharing the most rules; retrieval of that practiced conjunction, with intrusions; compilation of repeated novel tasks with decay), with between-participant variability.
- **Accounts (true mechanism):** compositional, conjunctive, or dual-route with compilation. They differ only in the mechanism parameters; all nuisance parameters share one broad prior.
- **Evidence levels of a report:**
  1. practice curves plus practiced vs. novel;
  2. plus novel tasks by shared rules (2 vs. 1) and by the rule type that differs;
  3. plus intrusion errors by the rule type that differs;
  4. plus repetition x lag.
- **Ideal reader:** posterior over the three accounts given the reported means and SEs (Monte Carlo over each account's prior, likelihood tempered by tau = 4 for calibration; validated calibration error 0.017 on simulated data). Computed with k = 8000 per account and a fixed seed per instance.
- **Prompt:** the three accounts as reviewed by the user, the report, and a request for `{"account": ..., "probabilities": {...}, "key_evidence", "alternative_readings", "next_step"}`. Two instruction conditions: **base**, and **alternatives** ("Before you decide, consider each account in turn: work out what it predicts for every analysis reported, check which of the reported results each account can and cannot explain, and only then weigh them.").

## 3. Design

24 simulated experiments (8 per true account; seed 50000). Each is shown at all 4 levels x 2 instruction conditions: **192 calls** to `claude-opus-5-5`, no tools, one answer per call. Paired within an experiment.

## 4. Measures

From Claude's probabilities (normalised to sum to 1):
- **p_truth**, the probability given to the true account;
- **top_correct**, whether the true account has the highest probability;
- **Brier**, over the three accounts;
- **overclaim** = Claude's maximum probability minus the ideal reader's maximum probability;
- **gap** = ideal p_truth minus Claude's p_truth;
- **p_comp_excess** = Claude's p(compositional) minus the ideal's p(compositional).

Unparsed responses are excluded and counted. Failed launches are rerun; nothing else is rerun.

## 5. Hypotheses and tests (confirmatory)

- **H1a, evidence sensitivity.** Claude's p_truth is higher at level 4 than at level 1 (paired by experiment and instruction). Wilcoxon signed-rank, one-sided.
- **H1b, under-sensitivity.** Claude's increase in p_truth from level 1 to level 4 is smaller than the ideal reader's (paired: ideal increase minus Claude increase > 0). Wilcoxon, one-sided.
- **H2, overclaiming on thin evidence.** At levels 1-2, overclaim > 0 (Claude more certain than the evidence warrants). Wilcoxon, one-sided.
- **H3, the remedy.** At levels 1-2, overclaim is lower with the alternatives instruction than without (paired by experiment and level). Wilcoxon, one-sided.
- **H4, the shared-rules trap.** At level 2, when the true account is conjunctive or dual-route, Claude gives compositional more probability than the ideal reader does (p_comp_excess > 0). The standard breakdown shows faster performance for novel tasks that share more rules under every account; reading that as evidence for compositional reuse is the trap. Wilcoxon, one-sided.

Holm correction over H1a, H1b, H2, H3, H4 at alpha = 0.05.

**Secondary, descriptive** (95% intervals):
- top_correct and Brier by level, account, and instruction, beside the ideal reader;
- Claude's p_truth vs. the ideal's by level (the "dose-response" curves);
- at level 4, top_correct (prediction: >= 0.8);
- exploratory reading of `key_evidence` for which analyses Claude cites (no grader; quotations only).

## 6. Predictions

H1a holds. H1b holds. H2 holds. H3 holds. H4 holds (low confidence: Claude may know the conjunctive-vs-compositional literature well enough to avoid it). At level 4, top_correct >= 0.8.

## 7. Pilot

3 calls on a separate experiment (seed 50999; level 4, base; one per account), to check prompt rendering, parsing, and cost. Outcomes are not analysed. Only pipeline bugs may be fixed, and any fix is listed below.

## 8. Changes after this commit

(none yet)
