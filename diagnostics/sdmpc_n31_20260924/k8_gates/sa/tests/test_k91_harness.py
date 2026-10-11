"""K9-1-0 harness tests (synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k91_harness.py -v
K8_PREDECLARATION_AMENDMENT_19 r2 (sha 4ccfd8fd...): the blind guard (sections 0.4 / 3.1-4 / 5.4 -- the three section
3.1-4 self-test cases, 'G1 full 2700 BASE allowed, the same form full 4950 BASE refused', the closed allow-list,
non-scalar refusal, the k91t stage and its mark), the K9 key list / strip, the K91 arm identity (section 2.6), the
deterministic k91_outcome of sections 6.1-6.3 (NaN, null, n != 9, unclassified items included), the K9-1-0 passive
record rule (summary only for a K9-keyed run), the F17b history copies and the G5 one-sided allowance."""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import sa_common as sc  # noqa: E402
import sa_arms  # noqa: E402
import k8b_report as kr  # noqa: E402

N31 = SA.parents[1]
BASE = N31 / 'config_n31_v2.json'                                     # 319d07aa
K86H_SAF = N31 / 'config_n31_v2_stopline_observed_full.json'          # 178de6c2
SAF_K8B = N31 / 'config_n31_v2_stopline_observed_full_k8b.json'       # af2a7783
NONE = SimpleNamespace(gates_stage=None, declaration_sha=None)
OPEN = SimpleNamespace(gates_stage='k91t', declaration_sha=sc.K91_AMENDMENT19_SHA256)
OLD = SimpleNamespace(gates_stage='k8bt', declaration_sha=sc.K8B_AMENDMENT16_SHA256)
PIN = {'evidence': 'e', 'evidence_sha256': 'h'}


@pytest.fixture
def out_root(tmp_path):
    sc.c.configure(out=tmp_path / 'gates_out')
    yield tmp_path / 'gates_out'
    sc.c.configure()


def _with(src, dst, **keys):
    doc = json.loads(Path(src).read_text(encoding='utf-8-sig'))
    for dotted, value in keys.items():
        a, b = dotted.split('__')
        doc.setdefault(a, {})[b] = value
    Path(dst).write_text(json.dumps(doc), encoding='utf-8')
    return dst


def _k91(tmp_path, z1=False):
    keys = dict(urban__sc1001_wout_saturation=PIN, urban__wout_side_handoff=PIN, freeway__offramp_split_forecast=PIN)
    if z1:
        keys['urban__latent_reservation_touch'] = True
    return _with(SAF_K8B, tmp_path / ('k91z.json' if z1 else 'k91.json'), **keys)


def test_files_are_the_pins():
    assert sc.sha256_file(BASE) == sc.K8B_BASE_SHA256
    assert sc.sha256_file(K86H_SAF) == sc.K8B_K86H_ARM_SHA256['SAF']
    assert sc.sha256_file(SAF_K8B) == sc.K91_K8B_ARM_SHA256['SAF']


# ------------------------------------------------------------------------------------------------ section 3.1-4
def test_selftest_k9_key_only_tuning_refused_on_a_judging_state(out_root, tmp_path):
    only = _with(BASE, tmp_path / 'base_z1.json', urban__latent_reservation_touch=True)
    with pytest.raises(SystemExit, match='K91_BLIND_REFUSED'):
        sc.k91_guard(only, 31, 2700, NONE, 't', op='capture', harness='TL3', arm='BASE')


def test_selftest_old_k8bt_token_refused(out_root, tmp_path):
    with pytest.raises(SystemExit, match='K91_STAGE_REFUSED'):
        sc.k91_guard(_k91(tmp_path), 31, 2700, OLD, 't', op='capture', harness='TL3', arm='SAF')


def test_selftest_probe_state_allowed(out_root, tmp_path):
    keys = sc.k91_guard(_k91(tmp_path), 31, 1650, NONE, 't', op='capture', harness='TL3', arm='SAF')
    assert keys[-3:] == list(sc.K91_ARM_KEYS) and 'urban.wout_exit_law' in keys
    assert not (sc.sa_out() / 'k91_judging_stage.json').is_file()


def test_old_token_opens_nothing_even_keyless(out_root):
    with pytest.raises(SystemExit, match='K91_STAGE_REFUSED'):
        sc.k91_guard(BASE, 31, 1650, OLD, 't', op='capture', harness='TL3', arm='BASE')
    with pytest.raises(SystemExit, match='K91_STAGE_REFUSED'):
        sc.k91_guard(BASE, 31, 1650, SimpleNamespace(gates_stage='k91t', declaration_sha='0' * 64), 't',
                     op='capture', harness='TL3', arm='BASE')


# ------------------------------------------------------------------------------------------------ section 0.4
def test_g1_full_2700_base_allowed_and_4950_refused(out_root):
    assert sc.k91_guard(BASE, None, 2700, NONE, 'full', op='full', harness='FULL', arm='BASE', chain='site') == []
    with pytest.raises(SystemExit, match='K91_BLIND_REFUSED'):
        sc.k91_guard(BASE, None, 4950, NONE, 'full', op='full', harness='FULL', arm='BASE', chain='site')
    with pytest.raises(SystemExit, match='non-scalar'):
        sc.k91_guard(BASE, None, 2700, NONE, 'full', op='full', harness='FULL', arm='BASE', chain='site:hooks')


@pytest.mark.parametrize('kw,allowed', [
    (dict(op='capture', harness='DP', arm='BASE', path=BASE, T=2700), True),               # G1 DP 17
    (dict(op='capture', harness='DP', arm='SAF', path=K86H_SAF, T=3150), True),
    (dict(op='capture', harness='TL3', arm='BASE', path=BASE, T=900), True),                # G1 TL3 9
    (dict(op='capture', harness='TL3', arm='SAF', path=K86H_SAF, T=2700), True),            # G2
    (dict(op='capture', harness='TL3', arm='SAF', path=K86H_SAF, T=900), False),
    (dict(op='capture', harness='FH', arm='BASE', path=BASE, T=2700), False),
    (dict(op='capture', harness='ROBS61', arm='BASE', path=BASE, T=150), False),
    (dict(op='job', harness='TL3', arm='BASE', path=BASE, T=2700, entry='A1', H=3), True),
    (dict(op='job', harness='TL3', arm='BASE', path=BASE, T=2700, entry='OBS', H=6), False),
    (dict(op='job', harness='TL3', arm='BASE', path=BASE, T=2700, entry='OBS', H=3, variant='C11'), False),
    (dict(op='job', harness='TL3', arm='BASE', path=BASE, T=2700, entry='OBS', H=3, mode='ad'), False),
    (dict(op='job', harness='TL3', arm='BASE', path=BASE, T=2700, entry='OBS', H=3, hooks=True), False),
    (dict(op='job', harness='TL3', arm='SAF', path=K86H_SAF, T=2700, entry='OBS', H=3), True),
    (dict(op='job', harness='TL3', arm='SAF', path=K86H_SAF, T=2700, entry='A1', H=3), False),
    (dict(op='job', harness='DP', arm='BASE', path=BASE, T=2700, entry='A1', H=1), False)])
def test_closed_allow_list(out_root, kw, allowed):
    kw = dict(kw)
    path, seed, T = kw.pop('path'), 31, kw.pop('T')
    hooks = kw.pop('hooks', False)
    if allowed:
        assert sc.k91_guard(path, seed, T, NONE, 't', hooks=hooks, **kw) == []
    else:
        with pytest.raises(SystemExit, match='K91_BLIND_REFUSED'):
            sc.k91_guard(path, seed, T, NONE, 't', hooks=hooks, **kw)


def test_nonscalar_refused_on_judging_states_only(out_root):
    with pytest.raises(SystemExit, match='non-scalar'):
        sc.k91_guard(BASE, 31, 2700, NONE, 't', op='job', harness='TL3', arm='BASE', entry='A1', H=3,
                     variant='ADREF', mode='ad_full')
    assert sc.k91_guard(BASE, 31, 3300, NONE, 't', op='job', harness='TL3', arm='BASE', entry='A1', H=3,
                        variant='ADREF', mode='ad_full') == []
    assert sc.k91_nonscalar('job', 'TAN', 'ad') and sc.k91_nonscalar('job', 'C00', 'scalar')
    assert not sc.k91_nonscalar('job', 'REF', 'scalar') and not sc.k91_nonscalar('capture')


def test_keyed_by_capture_metadata_refused(out_root):
    with pytest.raises(SystemExit, match='K91_BLIND_REFUSED'):
        sc.k91_guard(K86H_SAF, 31, 2700, NONE, 't', op='job', harness='TL3', arm='SAF', entry='OBS', H=3,
                     extra_keys=['capture metadata k9_w1'])


def test_stage_open_and_mark(out_root, tmp_path):
    keys = sc.k91_guard(_k91(tmp_path), 31, 2700, OPEN, 'first', op='capture', harness='TL3', arm='SAF')
    assert 'freeway.offramp_split_forecast' in keys
    mark = json.loads((sc.sa_out() / 'k91_judging_stage.json').read_text(encoding='utf-8'))
    assert mark['amendment19_sha256'] == sc.K91_AMENDMENT19_SHA256 and mark['first']['what'] == 'first'
    sc.k91_guard(BASE, 31, 900, OPEN, 'second', op='job', harness='TL3', arm='BASE', entry='OBS', H=24)
    assert json.loads((sc.sa_out() / 'k91_judging_stage.json').read_text(encoding='utf-8'))['first']['what'] == 'first'


def test_k9_keys_and_strip(tmp_path):
    doc = json.loads(Path(_k91(tmp_path, z1=True)).read_text(encoding='utf-8'))
    assert sc.k9_keys_of(doc) == list(sc.K91_ARM_KEYS) + [sc.K91_Z1B_KEY]
    s = sc.k9_strip(doc)
    assert sc.k9_keys_of(s) == [] and sc.k9_keys_of(doc)
    assert json.dumps(s, sort_keys=True) == json.dumps(json.loads(SAF_K8B.read_text(encoding='utf-8-sig')),
                                                       sort_keys=True)
    assert sc.guard_keys_of(doc)[:3] == ['urban.stopline_approach.city_arrival', 'urban.sc1002w_saturation',
                                         'urban.wout_exit_law']


# ------------------------------------------------------------------------------------------------ section 2.6
def test_k91_arm_identity(tmp_path):
    base = json.loads(BASE.read_text(encoding='utf-8-sig'))
    arm = json.loads(Path(_k91(tmp_path)).read_text(encoding='utf-8'))
    section, k8b, k9 = sa_arms.check_k91_arm(base, arm, 'observed_full', SAF_K8B, 'SAF')
    assert k9 == list(sc.K91_ARM_KEYS) and len(k8b) == 3
    z = json.loads(Path(_k91(tmp_path, z1=True)).read_text(encoding='utf-8'))
    assert sa_arms.check_k91_arm(base, z, 'observed_full', SAF_K8B, 'SAF')[2][-1] == sc.K91_Z1B_KEY
    bad = json.loads(json.dumps(z))
    bad['urban']['latent_reservation_touch'] = False
    with pytest.raises(SystemExit, match='must be true'):
        sa_arms.check_k91_arm(base, bad, 'observed_full', SAF_K8B, 'SAF')
    bad = json.loads(json.dumps(arm))
    del bad['freeway']['offramp_split_forecast']
    with pytest.raises(SystemExit, match='three declared keys'):
        sa_arms.check_k91_arm(base, bad, 'observed_full', SAF_K8B, 'SAF')
    bad = json.loads(json.dumps(arm))
    bad['urban']['queue'] = {'other': 1}
    with pytest.raises(SystemExit, match='differs from the K8b arm'):
        sa_arms.check_k91_arm(base, bad, 'observed_full', SAF_K8B, 'SAF')


# ------------------------------------------------------------------------------------------------ sections 6.1-6.3
def _it(value=None, ok=True, judged=True):
    return {'value': value, 'threshold': '-', 'pass_': ok, 'judged': judged, 'note': None}


def _gates(bias=-1.0, n=9, e6300=100.0, e6750=-20.0, stock_pass=True, combined='PROMOTE_ELIGIBLE'):
    g = {}
    for gid in ('G-EB-0', 'G-EB-1', 'G-EB-2', 'G-EB-4', 'G-EB-6', 'G-EB-7', 'G-EB-8', 'G-EB-9', 'G-EB-13', 'G-EB-14'):
        g[gid] = {'id': gid, 'verdict': 'PASS', 'items': {'x': _it()}}
    g['G-EB-3'] = {'id': 'G-EB-3', 'verdict': 'PASS',
                   'items': {'d_W_out_TL3': _it({'n': n, 'bias': bias}, abs(bias) <= 5 if _num(bias) else None),
                             'FH_report': _it(None, None, judged=False)}}
    g['G-EB-5'] = {'id': 'G-EB-5', 'verdict': 'PASS',
                   'items': {'2700_stock': _it({'6300': {'err': e6300, 'demoted': False},
                                                '6750': {'err': e6750, 'demoted': False}}, stock_pass)}}
    g['G-EB-10'] = {'id': 'G-EB-10', 'verdict': 'INCOMPLETE', 'items': {'r': _it(None, None, judged=False)}}
    g['G-EB-11'] = {'id': 'G-EB-11', 'verdict': 'PASS',
                    'items': {k: _it() for k in ('wall_ratio', 'action_json', 'ad_vs_fd_T13', 'd_s3_hooks',
                                                 'e_state_error')}}
    return {'combined': combined, 'gates': g}


def _num(v):
    return isinstance(v, float) and math.isfinite(v)


def _fail(g, gid, item, combined='STOP'):
    g['gates'][gid]['items'][item] = _it(None, False)
    g['gates'][gid]['verdict'] = 'FAIL'
    g['combined'] = combined
    return g


def test_outcome_pass():
    o = kr.k91_outcome(_gates())
    assert o['form'] == 'PASS_J1' and o['regression']['valid'] and o['regression']['fires'] is False


@pytest.mark.parametrize('kw', [dict(bias=-5.6), dict(e6300=420.05), dict(e6750=-523.2), dict(e6300=-150.5)])
def test_outcome_regression_stop_first(kw):
    g = _gates(**kw)
    g['gates']['G-EB-4']['items']['x'] = _it(None, None)          # an incomplete gate does not delay the guard
    assert kr.k91_outcome(g)['form'] == 'STOP_REGRESSION'


def test_outcome_regression_equal_is_not_worse():
    assert kr.k91_outcome(_gates(bias=-5.559080631867624, e6300=420.0430980575379))['regression']['fires'] is False


@pytest.mark.parametrize('kw', [dict(bias=float('nan')), dict(bias=None), dict(n=8), dict(stock_pass=None),
                                dict(e6750=None), dict(e6300=float('inf'))])
def test_outcome_regression_invalid_never_passes(kw):
    o = kr.k91_outcome(_gates(**kw))
    assert o['form'] == 'REGRESSION_INVALID' and o['regression']['valid'] is False


def test_outcome_incomplete_integrity_fidelity():
    g = _gates()
    g['gates']['G-EB-6']['items']['x'] = _it(None, None)
    assert kr.k91_outcome(g)['form'] == 'INCOMPLETE'
    assert kr.k91_outcome(_fail(_gates(), 'G-EB-2', 'x'))['form'] == 'INTEGRITY_FIX'
    assert kr.k91_outcome(_fail(_gates(), 'G-EB-4', 'x'))['form'] == 'KNOWN_DEFECT_J1'
    assert kr.k91_outcome(_fail(_gates(), 'G-EB-11', 'wall_ratio'))['form'] == 'KNOWN_DEFECT_J1'
    assert kr.k91_outcome(_fail(_gates(), 'G-EB-11', 'action_json'))['form'] == 'KNOWN_DEFECT_J1'
    for item in ('ad_vs_fd_T13', 'd_s3_hooks', 'e_state_error'):
        assert kr.k91_outcome(_fail(_gates(), 'G-EB-11', item))['form'] == 'INTEGRITY_FIX'


def test_outcome_unclassified_is_integrity():
    g = _gates()
    g['gates']['G-EB-11']['items']['f_new'] = _it(None, False)
    g['gates']['G-EB-11']['verdict'] = 'FAIL'
    g['combined'] = 'STOP'
    o = kr.k91_outcome(g)
    assert o['form'] == 'INTEGRITY_FIX' and 'G-EB-11/f_new' in o['unclassified']
    g2 = _gates()
    g2['gates']['G-EB-15'] = {'id': 'G-EB-15', 'verdict': 'FAIL', 'items': {'y': _it(None, False)}}
    g2['combined'] = 'STOP'
    assert kr.k91_outcome(g2)['form'] == 'INTEGRITY_FIX'


def test_outcome_conditional_needs_its_diagnosis():
    g = _fail(_gates(), 'G-EB-7', '2700_collapse')
    assert kr.k91_outcome(g)['form'] == 'KNOWN_DEFECT_J1'
    assert kr.k91_outcome(g, {'iii': {'2700': {'iii': True}}})['form'] == 'CONDITIONAL_J1'
    g = _fail(g, 'G-EB-6', 'x')                                    # 6 is outside the list
    assert kr.k91_outcome(g, {'iii': {'2700': {'iii': True}}})['form'] == 'KNOWN_DEFECT_J1'


# ------------------------------------------------------------------------------------------------ recorder / copies
def test_worker_record_rule():
    import sa_worker
    assert sa_worker.K91_META_KEYS == sc.K9_META_KEYS
    s = {'k91': {'z1_touch_events': 3.0}, 'blocks': [{'k': 1, 'k91': {'w1_queue': {}}}, {'k': 2, 'k91': None}]}
    sa_worker.K91['keyed'] = False
    rec = sa_worker.k91_split(s)
    assert 'k91' not in s and all('k91' not in b for b in s['blocks'])
    assert rec['keyed'] is False and rec['top'] == {'z1_touch_events': 3.0} and len(rec['blocks']) == 2
    s = {'k91': {'z1_touch_events': 3.0}, 'blocks': [{'k': 1, 'k91': {'x': 1.0}}]}
    sa_worker.K91['keyed'] = True
    rec = sa_worker.k91_split(s)
    assert s['k91'] == {'z1_touch_events': 3.0} and s['blocks'][0]['k91'] == {'x': 1.0} and rec['keyed'] is True
    sa_worker.K91['keyed'] = False


def test_history_copy(out_root, tmp_path):
    dec, rep = tmp_path / 'dec', tmp_path / 'rep'
    (dec / 'obs150').mkdir(parents=True)
    for Tp in range(150, 1650, 150):
        (dec / 'obs150' / f'derived_{Tp:06d}.json').write_text(json.dumps({'t': Tp}), encoding='utf-8')
    rec = sc.k91_history_copy(rep, dec, 1650)
    assert [w[0] for w in rec['windows']] == list(range(150, 1650, 150))
    assert (rep / 'obs150' / 'derived_001500.json').read_bytes() == (dec / 'obs150' / 'derived_001500.json').read_bytes()
    assert not (rep / 'obs150' / 'derived_001650.json').exists()
    (rep / 'obs150' / 'derived_000300.json').write_text('{}', encoding='utf-8')
    with pytest.raises(SystemExit, match='differs'):
        sc.k91_history_copy(rep, dec, 1800)


def test_g5_one_sided_allowance():
    import k8b_commit_gates as cg
    a = {'x': 1.0, 'blocks': [{'k': 1.0}]}
    b = {'x': 1.0, 'blocks': [{'k': 1.0, 'k91': {'q': 2.0}}], 'k91': {'z1_touch_events': 4.0}}
    r = cg.compare_g5(a, b, [], renamed=(), allowed_one_sided=sc.K91_NEW_RECORD)
    assert r['equal'] and r['one_sided_allowed'] == 2 and r['one_sided_failing'] == 0
    r = cg.compare_g5(a, b, [], renamed=())
    assert not r['equal'] and r['one_sided_failing'] == 2
    r = cg.compare_g5(a, dict(b, x=1.0 + 2 ** -52), [], renamed=(), allowed_one_sided=sc.K91_NEW_RECORD)
    assert not r['equal'] and r['numeric_differ'] == 1
