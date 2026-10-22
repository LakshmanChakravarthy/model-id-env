import numpy as np

from env.config import load_config
from harness import study4 as s4

P = load_config()["study4"]


def test_flip_symmetry_all_rules():
    for l in range(6):
        for f in range(4):
            for z in s4.Z_ALL:
                assert np.array_equal(s4.out(l, f, z, s4.ALL), s4.out(s4.COMPLEMENT[l], f, z[::-1], s4.ALL))


def test_worlds_carry_only_their_regularity():
    rng = np.random.default_rng(0)
    for _ in range(30):
        c = s4.make_world(rng, "categorical", True)
        assert s4.fits_split(c["Z"]) and not s4.ordinal_consistent(c["Z"])
        o = s4.make_world(rng, "ordinal", True)
        assert s4.ordinal_consistent(o["Z"]) and not s4.fits_split(o["Z"])
        q = s4.make_world(rng, "polarity", True)
        assert set(q["x_set"]) == set(s4.POSITIVE) and not s4.fits_split(q["Z"]) and not s4.ordinal_consistent(q["Z"])
        n = s4.make_world(rng, "categorical", False)
        assert not s4.fits_split(n["Z"]) and not s4.ordinal_consistent(n["Z"]) and n["x_set"] == s4.ALL_RULES


def test_selected_instances_meet_bands_and_truth_is_consistent():
    insts = s4.make_instances(P, 7, [("categorical", "high", 1), ("ordinal", "moderate", 1), ("polarity", "irregular", 1)])
    for inst in insts:
        assert s4.in_band(inst, inst["cell"], inst["type"], P["bands"])
        sols = s4.consistent_none(inst["known"], inst["known_ex"], inst["world"])
        truth_assign = {s: (inst["world"]["Z"][s[1]] if s[0] == "Z" else s[1])
                        for k in inst["known"] for s in s4.slots(k)}
        assert truth_assign in sols
        for key in ("ideal_digits", "ideal_colours"):
            assert abs(sum(q for _, q in inst[key]["posterior"]) - 1) < 1e-9
    ordinal = [i for i in insts if i["type"] == "ordinal"][0]
    assert "ordinal" not in ordinal["ideal_colours"]["p_hypothesis"]


def test_prompts_and_parsing():
    inst = s4.make_instances(P, 8, [("categorical", "high", 1)])[0]
    d = s4.build_prompt(inst, False, False, P)
    c = s4.build_prompt(inst, True, True, P)
    assert "0, 1, 2, or 3" in d and P["pattern"] not in d and P["alternatives"] in d
    assert "0, 1, 2, or 3" not in c and P["pattern"] in c
    assert not any(line.rstrip().endswith(("-> 0", "-> 1", "-> 2", "-> 3")) for line in c.splitlines())
    names = [inst["colours"][b] for b in inst["ideal_colours"]["modal"]]
    ans, preds = s4.parse_answer('x {"predictions": %s, "determined": false, "confidence": 0.6}' % str(names).replace("'", '"'),
                                 inst, True)
    assert preds == inst["ideal_colours"]["modal"]
    assert s4.score(inst, True, preds, ans)["R"] == 1
