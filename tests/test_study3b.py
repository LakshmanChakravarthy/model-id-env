import numpy as np

from env import tasks
from harness import study3b as s3
from env.config import load_config

P = load_config()["study3"]["b"]


def test_flat_semantics_match_task_space():
    R = tasks.response_matrix()
    for t in range(64):
        assert np.array_equal(s3.true_out(("flat", tasks.task_parts(t))), R[t])


def test_deep_reduces_to_flat_when_conditions_equal():
    for l in range(4):
        for f in range(4):
            deep = s3.deep_out(0, l, f, l, f, (0, 1), s3.ALL)   # AND of a condition with itself
            assert np.array_equal(deep, s3.flat_out(l, f, (0, 1), s3.ALL))


def test_truth_is_always_consistent_and_stated_determined_equals_truth():
    rng = np.random.default_rng(0)
    for want in ("det", "amb"):
        inst = s3.gen_block_a(rng, P, want)
        truth = list(s3.true_out(inst["test"], np.array(inst["items"])))
        for z in (s3.Z_STATED, s3.Z_WITHHELD):
            sols = s3.consistent_assignments(inst["known"], inst["known_ex"], z)
            identity = {s: (s3.Z_STATED[s[1]] if s[0] == "Z" else s[1]) for s in s3.values_of(inst["known"])}
            assert identity in sols
        st = inst["ideal"]["stated"]
        assert st["determined"] and st["modal"] == [int(v) for v in truth]
        assert inst["ideal"]["withheld"]["determined"] == (want == "det")


def test_unlabelled_ideal_contains_truth():
    rng = np.random.default_rng(1)
    inst = s3.gen_block_b(rng, P, "low")
    truth = [int(v) for v in s3.true_out(inst["test"], np.array(inst["items"]))]
    assert inst["ideal"]["stated"]["modal"] == truth


def test_deep_instance_determined_equals_truth():
    rng = np.random.default_rng(2)
    inst = s3.gen_block_c(rng, P, "high")
    truth = [int(v) for v in s3.true_out(inst["test"], np.array(inst["items"]))]
    assert inst["ideal"]["stated"]["determined"] and inst["ideal"]["stated"]["modal"] == truth


def test_parse_and_prompt():
    rng = np.random.default_rng(3)
    inst = s3.gen_block_a(rng, P, "amb")
    p = s3.build_prompt(inst, "A", False, s3.label_maps(rng))
    assert "button for true is 1 or 2" not in p and "not both are 1" in p
    obj = s3.parse('blah {"predictions": [1,2,3,0,1,2,3,0,1,2,3,0,1,2,3,0], "determined": false, "confidence": 0.5}', 16)
    assert obj["determined"] is False
