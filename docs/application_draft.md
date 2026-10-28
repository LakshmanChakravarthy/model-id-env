# Application answers: revised draft (2026-10-27)

Based on the user's draft in `Application questions.docx`, with the proposal re-centred on interpreting neural representational-geometry results. Word counts are measured with `wc -w`, excluding the question text.

---

## Q1. Propose one or two concrete ideas for evaluating, improving, or applying Claude in your field (200 words max)

**Interpreting representational geometry: an environment with known ground truth.**

A central open question in cognitive neuroscience is how the brain balances compositional codes, which support generalization, against conjunctive codes, which reduce interference, and how that balance changes with learning. The evidence comes from representational-geometry analyses: RSA, decoding, cross-condition generalization, dimensionality. Each rests on assumptions. Decodable is not the same as used. Difficulty and RT confound geometry. Noise and voxel pooling distort it. Analyses often disagree, and a paper usually commits to one pipeline under limits of time, space, and review. Claude does not have these limits, so it can run the full multiverse of reasonable analyses and reconcile them. The open question is whether it does so correctly.

Environment: simulated neural data from RNNs and generative models whose geometry I control (factorized, conjunctive, mixed, changing with practice), passed through realistic measurement (noise, hemodynamics, voxel mixing). Claude gets the data and a scientific question, chooses and runs analyses, and reports what the geometry is and what the data cannot decide. Known ground truth makes scoring exact, and procedural generation makes it scale as an RL environment.

Hard cases: confounded difficulty, mimicking geometries, decodable but unused codes, and analyses that disagree.

---

## Q2. Experience with Claude Code or similar agentic coding products

I use Claude Code on the Amarel HPC cluster for four active repos. Claude co-authored 252 commits in six weeks.

Separate sessions for separate roles: one to brainstorm the plan, others to execute it (preprocessing fixes, QC, analyses, methods drafts), and one with a dedicated presentation skill to structure the narrative and find unclear points.

Workflow: each repo has a CLAUDE.md (problem, hypothesis, conventions, never-do list). Analyses follow a pre-registered cycle: a "declare" commit before any code, then the script and tests as a SLURM job, then a "record results" commit. Negative controls run in the same sweep.

A failure I learned from: the agent removed a hemisphere flip with a confident but wrong argument, which mirrored every brain figure. I noticed that a figure disagreed with the printed betas. We added a synthetic known-answer check. Lesson: verify agent work against known answers, not against its arguments.

For this application I built a pilot with Claude Code in one week (https://github.com/LakshmanChakravarthy/model-id-env): five studies of Claude as experimenter, learner, and reader of C-PRO experiments, each declared before it ran (the last two fully preregistered), run headless with restricted tools. Known-answer checks caught wrong design premises before the main runs: the first task space had no confound, random designs were already at ceiling, and the sandbox let read-only commands through. Claude read qualitative signatures like an expert, but weighed graded evidence poorly. Working through the pilot changed my question several times; the README records each turn, including the paths I dropped.

---

## Q3. Experience with ML/AI (150 words max)

Training custom models: I train RNNs on a compositional task (C-PRO): train on 4 tasks, test on 60 new combinations. I test biological constraints (local connectivity, input random projection) and rich versus lazy learning regimes. My work on task representation dynamics in these RNNs was accepted at the ICLR Representational Alignment workshop and at CCN 2026. I also worked on small transformers for length generalization with Takuya Ito (IBM Research).

Applying existing models: I use sparse autoencoder features of Gemma (SAELens) to test whether sparse features capture the steps of analogy solving, and relate them to fMRI data. I also use BERT and static word embeddings as stimulus models in RSA of the same data.

Adjacent techniques: activity flow modeling (connectivity-based prediction of brain activity), representational geometry, decoding, and simulations of network models.

---

## Q4. Anything else you would like to share? (about 150 words)

I work across the whole loop that this environment needs. I design human experiments and collect fMRI, I train RNNs whose geometry I can control, and I analyze language models with interpretability tools (Gemma sparse autoencoders). The proposal depends on this combination: the simulated data must be realistic enough that an expert would recognize the analysis traps.

I learned of the fellowship from Andrew Lampinen's post. I share a conviction behind his work: cognitive science can help build better AI systems, and those systems can then test cognitive theory. His results on biases in learned representations also show why the environment needs known mechanisms: representational analyses must be validated against ground truth.

Pilot code, preregistrations, and results: https://github.com/LakshmanChakravarthy/model-id-env.
