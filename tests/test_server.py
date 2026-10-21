import json
import subprocess
import sys
from pathlib import Path

from env import server
from env.config import load_config
from env.environment import Environment
from harness import run_claude

CFG = load_config()


def test_query_client_roundtrip(tmp_path):
    env = Environment("holistic", 0, CFG)
    srv, port = server.start(env)
    try:
        box = run_claude.make_sandbox(tmp_path, "inst", port, "prompt")
        assert sorted(p.name for p in box.iterdir()) == ["prompt.md", "query.py"]
        q = lambda *a: json.loads(subprocess.run(["python3", "query.py", *a], cwd=box, capture_output=True,
                                                 text=True, check=True).stdout)
        assert q("budget")["budget"] == CFG["environment"]["budget"]
        name = env.name(5)
        assert len(q("describe", name)["responses"]) == 256
        assert "fraction_same_response" in q("compare", name, env.name(6))
        q("train", name)
        assert "examples_to_criterion" in q("test", env.name(6))
        assert "error" in q("test", "L9-S9-M9")
        assert "error" in q("nonsense")
        q("submit", json.dumps({"verdict": "holistic", "confidence": 0.7, "justification": "x"}))
        assert env.verdict["verdict"] == "holistic"
        assert "error" in q("test", name)
        client = (box / "query.py").read_text()
        assert "holistic" not in client and "part_based" not in client and str(env.seed) not in client.split("PORT")[0]
    finally:
        srv.shutdown()


def test_audit_flags_non_query_commands():
    events = [
        {"message": {"content": [{"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "python3 query.py budget"}},
                                 {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": "cat /etc/hosts"}},
                                 {"type": "tool_use", "id": "c", "name": "Bash", "input": {"command": "python3 query.py budget; ls"}}]}},
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "{}", "is_error": False},
                                 {"type": "tool_result", "tool_use_id": "b", "content": "denied", "is_error": True},
                                 {"type": "tool_result", "tool_use_id": "c", "content": "x", "is_error": False}]}},
    ]
    a = run_claude.audit(events)
    assert a["n_tool_calls"] == 3 and a["n_other_attempts"] == 2
    assert [l["command"] for l in a["leaks"]] == ["python3 query.py budget; ls"]
    assert not a["pass"]
