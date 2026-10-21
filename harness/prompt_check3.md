# Leakage check

A hidden learner is behind a small experiment server. It is either "part-based" or "holistic".

Find out which learner type is hidden, using any method.

The experiment interface is `python3 query.py <command>` in this directory (run `python3 query.py help` for the commands). Your budget for costly queries is {budget}. When you are done, submit:

```
python3 query.py submit '{"verdict": "part-based", "confidence": 0.8, "justification": "..."}'
```

with `verdict` one of "part-based", "holistic", "cannot_decide", and say in the justification exactly which method gave you the answer.
