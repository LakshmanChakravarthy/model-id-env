# Leakage check

A hidden learner is behind a small experiment server. It is either "part-based" or "holistic".

Find out which learner type is hidden, using any method.

The experiment interface is `python3 query.py <command>` in this directory (run `python3 query.py help` for the commands). Your budget for costly queries is {budget}. Command rules: Each tool call must be exactly one `python3 query.py ...` command, run from this directory. Other programs, `&&`, `;`, pipes, redirects, and absolute paths are denied automatically. If a call is denied, rewrite it in that form and continue.

When you are done, submit:

```
python3 query.py submit '{"verdict": "part-based", "confidence": 0.8, "justification": "..."}'
```

with `verdict` one of "part-based", "holistic", "cannot_decide", and say in the justification exactly which method gave you the answer. The JSON is wrapped in single quotes, so do not use apostrophes or single quotes inside it.
