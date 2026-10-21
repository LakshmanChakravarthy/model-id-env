import numpy as np

from env import tasks


def test_task_id_roundtrip():
    for t in range(64):
        assert tasks.task_id(*tasks.task_parts(t)) == t


def test_response_matrix_shape_and_distinct_mappings():
    r = tasks.response_matrix()
    assert r.shape == (64, 256)
    # (logic, f, motor) and (complement logic, f, flipped motor) give the same mapping, so 32 distinct mappings.
    assert len({tuple(row) for row in r}) == 32


def test_complement_equivalence():
    sim = tasks.similarity_matrix(tasks.response_matrix())
    both_m0 = tasks.task_id(0, 2, 0)
    notboth_m1 = tasks.task_id(3, 2, 1)
    assert sim[both_m0, notboth_m1] == 1.0
    assert tasks.new_parts(notboth_m1, [both_m0]) == 2


def test_similarity_values():
    sim = tasks.similarity_matrix(tasks.response_matrix())
    assert np.allclose(np.diag(sim), 1.0)
    assert np.allclose(sim, sim.T)
    assert set(np.round(np.unique(sim), 4)) == {0.0, 0.375, 0.5, 0.625, 1.0}
    # Different "hands" share no responses.
    assert sim[tasks.task_id(0, 0, 0), tasks.task_id(0, 0, 2)] == 0.0
    # AND vs OR on the same feature agree on 2 of 4 bit patterns.
    assert sim[tasks.task_id(0, 0, 0), tasks.task_id(1, 0, 0)] == 0.5
    # AND on feature 0 vs AND on feature 1: P(equal) = 1/16 + 9/16.
    assert sim[tasks.task_id(0, 0, 0), tasks.task_id(0, 1, 0)] == 0.625


def test_shared_and_similarity_to_known():
    sim = tasks.similarity_matrix(tasks.response_matrix())
    known = [tasks.task_id(0, 0, 0), tasks.task_id(1, 1, 2)]
    t = tasks.task_id(0, 1, 2)
    assert tasks.shared_parts(t, known) == 3
    assert tasks.new_parts(t, []) == 3
    assert tasks.similarity_to_known(t, [], sim) == 0.0
    assert tasks.similarity_to_known(t, known, sim, "max") == sim[t, known].max()
    k = tasks.similarity_to_known(t, known, sim, "kernel", tau=0.1)
    assert sim[t, known].min() <= k <= sim[t, known].max()
