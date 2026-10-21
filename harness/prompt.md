# Identify the hidden learner

You are an experimenter. A hidden learner is behind a small experiment server. Your job is to find out which of two learning mechanisms it uses, by designing experiments.

## The tasks

There are 64 tasks. Each task combines one rule from each of three dimensions:
- a **logic** rule (labels L1-L4),
- a **sensory** rule (labels S1-S4),
- a **motor** rule (labels M1-M4).

A task is named by its three labels, for example `L2-S4-M1`. The labels are arbitrary: their numbers say nothing about what the rules do. Each task maps every input (a pair of stimuli with binary features) to a response button. `describe` explains the input encoding and shows any task's full input-output mapping.

## The two hypotheses

The learner is one of these. Both are equally likely a priori.

- **Part-based.** The learner stores the rules it has learned as reusable parts. The cost of learning a new task depends on how many of the task's three rules are new to the learner (not part of any task it was trained on).
- **Holistic.** The learner stores each learned task as one whole. The cost of learning a new task depends on how similar the task's overall input-output mapping is to the tasks it was trained on.

## What you can do

Run commands with `python3 query.py <command>` in this directory. That is the only tool available.

**Command rules.** Each tool call must be exactly one `python3 query.py ...` command, run from this directory. Other programs, `&&`, `;`, pipes, redirects, and absolute paths are denied automatically. If a call is denied, rewrite it in that form and continue.

| Command | Cost | What it does |
|---|---|---|
| `describe` | free | rule dimensions, labels, input encoding |
| `describe <task>` | free | the task's response to each input, as one string |
| `compare <task A> <task B>` | free | fraction of inputs on which the two tasks give the same response |
| `budget` | free | remaining budget |
| `train <task> [<task> ...]` | 1 per task | train the learner on these tasks |
| `test <task>` | 1 | the number of examples the learner needs to reach criterion on this task, given what it has been trained on so far |
| `submit '<verdict JSON>'` | free | submit your final verdict; this ends the session |

- Your budget is **{budget}**.
- Training is cumulative and cannot be undone.
- Testing does not train the learner.
- Test results are noisy. Repeating a test gives a new independent sample.

## Your verdict

When you are done, submit exactly one verdict:

```
python3 query.py submit '{"verdict": "part-based", "confidence": 0.8, "justification": "..."}'
```

- `verdict`: one of `"part-based"`, `"holistic"`, `"cannot_decide"`.
- `confidence`: your probability, from 0 to 1, that your verdict is correct.
- `justification`: a short explanation of your design and your evidence.

The JSON is wrapped in single quotes, so do not use apostrophes or single quotes inside it.

You must submit before you finish, even if your budget is not used up.
