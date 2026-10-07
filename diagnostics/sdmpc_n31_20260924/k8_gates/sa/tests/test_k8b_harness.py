"""K8b-0 harness tests (synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k8b_harness.py -v
K8_PREDECLARATION_AMENDMENT_16 r2: exception kinds (2.0-6), the blind guard (0.2 / 5.4), arm identity (5.2), wall-clock
pairs (5.3.1), the keyed unit-test refusal (0.2), the W_out episode rule (2.4.2) used by the harness."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import sa_common as sc  # noqa: E402
import sa_errors  # noqa: E402
import sa_arms  # noqa: E402
import sa_wallpairs as wp  # noqa: E402
import sa_vissim_ref  # noqa: E402

TESTS = SA.parents[1] / 'tests'
K8B = SA.parents[1] / 'k8b'


@pytest.fixture
def out_root(tmp_path):
    sc.c.configure(out=tmp_path / 'gates_out')
    yield tmp_path / 'gates_out'
    sc.c.configure()


def test_wout_invariant_error_is_an_invariant_kind():
    tb = ('Traceback (most recent call last):\n'
          '  File "D:/x/evaluation/controllers/urban_flow_accounting.py", line 900, in legsplit_substep_accounted\n'
          '    raise WoutExitInvariantError(msg)\n'
          'evaluation.controllers.urban_flow_accounting.WoutExitInvariantError: |sum X - (A - sum a)| = 1e-6\n')
    assert sa_errors.error_kind(tb) == 'invariant'
    assert sa_errors.error_site(tb) == 'runtime'
    assert 'invariant' in sa_errors.INVARIANT_KINDS
    assert sa_errors.error_kind('ValueError: K8b evidence sha256 mismatch') == 'other'


@pytest.mark.parametrize('seed,T,judging', [
    (31, 1650, False), (43, 3450, False), (47, 4800, False), (43, 2400, False),     # probe sample
    (31, 900, True), (47, 2700, True), (41, 4950, True), (53, 1350, True),           # GRID9 / DP_T any seed
    (31, 1500, True), (43, 1, True), (47, 150, True),                                # other R-obs states of 31/43/47
    (41, 1500, False), (37, 1500, True), (59, 1050, True)])                          # fit seed / sealed / non-fit
def test_judging_states(seed, T, judging):
    assert sc.k8b_judging_state(seed, T) is judging


def _doc(**urban):
    return {'urban': dict({'queue': {'contiguous': True}}, **urban), 'freeway': {'lane_plant': 'x'}}


def test_guard_refuses_keyed_judging_state(out_root, tmp_path):
    keyed = tmp_path / 'keyed.json'
    keyed.write_text(json.dumps(_doc(sc1002w_saturation={'evidence': 'a', 'evidence_sha256': 'b'})), encoding='utf-8')
    plain = tmp_path / 'plain.json'
    plain.write_text(json.dumps(_doc()), encoding='utf-8')
    args = SimpleNamespace(gates_stage=None, declaration_sha=None)
    assert sc.k8b_guard(plain, 31, 2700, args, 'test') == []
    assert sc.k8b_guard(keyed, 31, 1650, args, 'test') == ['urban.sc1002w_saturation']
    with pytest.raises(SystemExit, match='K8B_BLIND_REFUSED'):
        sc.k8b_guard(keyed, 31, 2700, args, 'test')
    with pytest.raises(SystemExit, match='judging stage needs'):
        sc.k8b_guard(keyed, 31, 2700, SimpleNamespace(gates_stage='k8bt', declaration_sha='0' * 64), 'test')
    ok = SimpleNamespace(gates_stage='k8bt', declaration_sha=sc.K8B_AMENDMENT16_SHA256)
    assert sc.k8b_guard(keyed, 31, 2700, ok, 'test') == ['urban.sc1002w_saturation']
    mark = sc.sa_out() / 'k8b_judging_stage.json'
    assert json.loads(mark.read_text(encoding='utf-8'))['first']['T'] == 2700


def test_k8b_keys_and_strip():
    doc = _doc(stopline_approach={'schema': 's', 'city_arrival': {'evidence': 'e', 'evidence_sha256': 'h'}},
               wout_exit_law={'SC1001_W_out': {}}, sc1002w_saturation={'evidence': 'e', 'evidence_sha256': 'h'})
    assert sc.k8b_keys_of(doc) == ['urban.stopline_approach.city_arrival', 'urban.sc1002w_saturation',
                                   'urban.wout_exit_law']
    s = sc.k8b_strip(doc)
    assert sc.k8b_keys_of(s) == [] and s['urban']['stopline_approach'] == {'schema': 's'}
    assert sc.k8b_keys_of(doc) != []          # strip copies


def test_arm_identity_check(tmp_path, monkeypatch):
    base = _doc()
    k86h = _doc(stopline_approach={'storage': 'observed_full', 'schema': 's'})
    path = tmp_path / 'k86h.json'
    path.write_text(json.dumps(k86h), encoding='utf-8')
    monkeypatch.setitem(sc.K8B_K86H_ARM_SHA256, 'SAF', sc.sha256_file(path))
    arm = json.loads(json.dumps(k86h))
    arm['urban']['stopline_approach']['city_arrival'] = {'evidence': 'e', 'evidence_sha256': 'h'}
    arm['urban']['sc1002w_saturation'] = {'evidence': 'e', 'evidence_sha256': 'h'}
    arm['urban']['wout_exit_law'] = {'SC1001_W_out': {}}
    section, keys = sa_arms.check_k8b_arm(base, arm, 'observed_full', path, 'SAF')
    assert len(keys) == 3
    bad = json.loads(json.dumps(arm))
    bad['urban']['stopline_approach']['merge_rule'] = 'other'           # SA section changed beside the K8b keys
    with pytest.raises(SystemExit, match='differs from the k86h arm'):
        sa_arms.check_k8b_arm(base, bad, 'observed_full', path, 'SAF')
    bad2 = json.loads(json.dumps(arm))
    bad2['urban']['extra'] = 1
    with pytest.raises(SystemExit, match='outside the four declared paths'):
        sa_arms.check_k8b_arm(base, bad2, 'observed_full', path, 'SAF')
    bad3 = json.loads(json.dumps(arm))
    del bad3['urban']['wout_exit_law']
    with pytest.raises(SystemExit, match='all three'):
        sa_arms.check_k8b_arm(base, bad3, 'observed_full', path, 'SAF')


def _job(tree, label, counts, wall, ok=True, extra=None):
    d = sc.job_dir(tree, label)
    d.mkdir(parents=True, exist_ok=True)
    s = {'ok': ok, 'wall_sec': wall, 'objective_repr': '1.0', 'blocks': [{'k': 1, 'x': 2.0}], 'job': {'label': label}}
    s.update(extra or {})
    (d / 'summary.json').write_text(json.dumps(s), encoding='utf-8')
    pre, post = counts
    (d / 'vissim_counts.json').write_text(json.dumps({'vissim_count_pre': pre, 'vissim_count_post': post}),
                                          encoding='utf-8')


def test_wallpairs_selection(out_root):
    pairs = wp.pairs()
    assert len(pairs) == 63
    tree = 't'
    (_k, _s, _T, _e, bl, sl) = pairs[0]
    _job(tree, bl, (0, 0), 10.0)
    _job(tree, sl, (0, 0), 11.0)
    (_k, _s, _T, _e, bl2, sl2) = pairs[1]
    _job(tree, bl2, (0, 1), 10.0)                          # VISSIM appeared during BASE: not clean
    _job(tree, sl2, (1, 0), 30.0)
    rows = {r['saf']: r for r in wp.select(tree)}
    assert rows[sl]['source'] == 'first' and rows[sl]['ratio'] == pytest.approx(1.1)
    assert rows[sl2]['source'] is None                     # waits for a clean rerun (INCOMPLETE meanwhile)
    _job(wp.wall_tree(tree), bl2, (0, 0), 10.0)
    _job(wp.wall_tree(tree), sl2, (0, 0), 12.0)
    rows = {r['saf']: r for r in wp.select(tree)}
    assert rows[sl2]['source'] == 'rerun' and rows[sl2]['ratio'] == pytest.approx(1.2)
    _job(wp.wall_tree(tree), sl2, (0, 0), 12.0, extra={'blocks': [{'k': 1, 'x': 3.0}]})
    rows = {r['saf']: r for r in wp.select(tree)}
    assert rows[sl2]['source'] == 'rerun_mismatch'         # the rerun differs outside timing: FAIL (STOP)


def test_block_counts_frames():
    out = sa_vissim_ref._block_counts([900.1, 900.2, 1050.1, 1050.2, 1200.1, 1350.1], 900, 3)
    assert out == {'1': 2, '2': 2, '3': 1}


def test_wout_episode_rule():
    sys.path.insert(0, str(K8B))
    import wout_episodes as we
    seq = [('S', 1.0, 29), ('W', 6.0, 31), ('E', 11.0, 10484),
           ('DUP', 20.0, 119), ('DC', 25.0, 10483), ('W', 30.0, 124), ('F', 35.0, 10775),
           ('DUP', 40.0, 119), ('RW', 45.0, 10480),
           ('SIDE', 50.0, 78), ('W', 55.0, 31), ('X', 60.0, 10704)]
    eps = list(we.episodes(seq))
    assert [(e[0], e[1]) for e in eps] == [('signal', 'R_D_E'), ('direct', 'free'), ('direct', 'R_D_W'),
                                           ('side', 'side_exit')]
    assert [e[4] for e in eps] == [11.0, 35.0, 45.0, 60.0]
    from collections import Counter
    sp = we.split(Counter({('signal', 'R_D_E'): 2, ('signal', 'free'): 1, ('signal', 'side_exit'): 1}))
    assert sp['signal']['s'] == {'R_D_E': 0.5, 'R_D_W': 0.0, 'free': 0.5} and sp['direct']['s'] is None


def test_keyed_unit_test_guard(tmp_path):
    sys.path.insert(0, str(TESTS))
    import k8b_test_guard as g
    assert g.refuse_judging(31, 3300) == (31, 3300)
    with pytest.raises(g.JudgingStateRefused):
        g.refuse_judging(31, 2700)
    cap = tmp_path / 'cap'
    cap.mkdir()
    (cap / 'capture.json').write_text(json.dumps({'seed': 43, 'T': 3450, 'frame_T': 3450}), encoding='utf-8')
    assert g.keyed_capture(cap) == cap
    (cap / 'capture.json').write_text(json.dumps({'seed': 43, 'T': 3600, 'frame_T': 3600}), encoding='utf-8')
    with pytest.raises(g.JudgingStateRefused):
        g.keyed_capture(cap)
