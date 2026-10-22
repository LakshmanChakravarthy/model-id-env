import numpy as np

from env.config import load_config
from harness import study3b as s3b
from harness import study3c as s3c

P = load_config()["study3"]["c"]


def test_regular_world_fits_a_split_and_irregular_does_not():
    assert s3c.fits_some_split(s3b.Z_STATED)
    assert not s3c.fits_some_split(s3c.random_irregular_world(np.random.default_rng(0)))


def test_global_flip_symmetry_without_overhypothesis():
    # Complementing every X and swapping every Z leaves tasks unchanged, so no Z's TRUE button is identifiable.
    comp = {0: 3, 3: 0, 1: 2, 2: 1}
    for l in range(4):
        for f in range(4):
            for z in s3b.Z_WITHHELD:
                assert np.array_equal(s3b.flat_out(l, f, z, s3b.ALL), s3b.flat_out(comp[l], f, z[::-1], s3b.ALL))


def test_cells_and_ideal():
    rng = np.random.default_rng(1)
    for cell in ("regular-high", "regular-low", "irregular"):
        inst = s3c.gen(rng, P, cell)
        idl = inst["ideal"]
        assert abs(sum(q for _, q in idl["posterior"]) - 1) < 1e-9
        assert idl["n_answers_without_overhypothesis"] == 2
        truth = [int(v) for v in s3c.out(inst["test"], inst["world"], np.array(inst["items"]))]
        assert truth in [v for v, _ in idl["posterior"]]
        if cell == "regular-high":
            assert idl["p_modal"] >= P["high_min"] and idl["modal"] == truth
        if cell == "irregular":
            assert idl["p_class"] < 1e-9 and abs(idl["p_modal"] - 0.5) < 1e-9
