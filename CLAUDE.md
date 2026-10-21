# CLAUDE.md

## Problem
Build a small environment that tests whether Claude can identify a hidden learning mechanism by designing experiments. Ground truth is known by construction, so scoring is automatic. See README.md for the full design.

## Hypothesis being tested (about Claude, not about the learners)
A capable experimenter finds the tasks that dissociate shared parts from overall similarity, and so identifies the hidden learner. A weak experimenter tests tasks where the two measures are confounded, and its verdicts are close to chance or overconfident.

## Conventions
- Python 3, numpy, scipy, matplotlib, pandas. No other dependencies unless necessary. Ask first.
- Simple, modular research code. No frameworks, no classes that are not necessary.
- All parameters in `configs/` (YAML or JSON). No hidden constants in the code.
- Every random process takes an explicit seed.
- Each instance writes one JSON file to `results/`: config, full query log, verdict, scores.
- Cycle for each analysis: a "declare" commit (what will run and what result is expected) before the code; then the code and its tests; then a "record results" commit.
- Known-answer checks (README, "Checks") run before any Claude run. A check that fails stops the work until it is fixed.
- Keep README.md "Current status" up to date at the end of each work session.

## Never do
- Never put the hidden learner type, the learner code, or the seed in the sandbox directory, or in any file that the experimenter Claude can read.
- Never run the experimenter Claude from inside this repo. Use a sandbox directory outside the repo.
- Never mention the confound in the experimenter prompt.
- Never change a learner or the scoring after you see Claude's results, without a new "declare" commit that says why.
- Never report a Claude result without the random baseline and the oracle beside it.
- Never add items from the "out of scope" list without asking.
