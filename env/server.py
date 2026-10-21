"""HTTP server for one instance. Runs in a thread of the harness process; the learner lives only here.

POST /query with JSON {"cmd": ..., "args": [...]} -> {"ok": true, "result": ...} or {"ok": false, "error": ...}.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

USAGE = {
    "train": "train <task> [<task> ...]   (cost: 1 per task)",
    "test": "test <task>   (cost: 1)",
    "describe": "describe [<task>]   (free)",
    "compare": "compare <task A> <task B>   (free)",
    "budget": "budget   (free)",
    "submit": "submit '<verdict JSON>'   (free; ends the session)",
}


def dispatch(env, cmd, args):
    if cmd == "train" and args:
        return env.train(args)
    if cmd == "test" and len(args) == 1:
        return env.test(args[0])
    if cmd == "describe" and len(args) <= 1:
        return env.describe(args[0] if args else None)
    if cmd == "compare" and len(args) == 2:
        return env.compare(args[0], args[1])
    if cmd == "budget" and not args:
        return env.get_budget()
    if cmd == "submit" and len(args) == 1:
        return env.submit(json.loads(args[0]))
    raise ValueError("usage: " + USAGE.get(cmd, "commands: " + ", ".join(USAGE)))


def start(env):
    """Start the server on a free localhost port. Returns (server, port)."""
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                with lock:
                    out = {"ok": True, "result": dispatch(env, str(body.get("cmd")), [str(a) for a in body.get("args", [])])}
            except (ValueError, RuntimeError, json.JSONDecodeError) as e:
                out = {"ok": False, "error": str(e)}
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]
