#!/usr/bin/env python3
"""Send one command to the experiment server and print the result.

Usage:
  python3 query.py describe                 list the rule dimensions and the input encoding (free)
  python3 query.py describe <task>          the task's response to every input, as one string (free)
  python3 query.py compare <task> <task>    fraction of inputs with the same response (free)
  python3 query.py budget                   remaining budget (free)
  python3 query.py train <task> [<task>...] train the learner on these tasks (cost 1 per task)
  python3 query.py test <task>              examples to criterion for this task, one noisy sample (cost 1)
  python3 query.py submit '<verdict JSON>'  submit your final verdict (free; ends the session)
Tasks are named like L1-S2-M3.
"""
import json
import sys
import urllib.request

PORT = None  # set by the harness


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return
    body = json.dumps({"cmd": sys.argv[1], "args": sys.argv[2:]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/query", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    print(json.dumps(out["result"] if out["ok"] else {"error": out["error"]}))


if __name__ == "__main__":
    main()
