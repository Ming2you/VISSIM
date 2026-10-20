"""K9-2-5 tests (amendment 29; synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_a29.py -v
K8_PREDECLARATION_AMENDMENT_29 (D-K9-53, D-K9-54): the A_K92 old-value condition (old value = the old root's
runtime_setup.py sha) and new-value condition, the A_K92-M sides and depths, the judges passing the old root, the N of
amendment 27 section 2.1 read exactly, the re-comparison helpers (strip29 / same29 / rold29), the A28-W check 12 and
the plant-row byte check; and the gaps O-1 of VERIFY_IMPL_r2 (G-K4 CR pair, A_K92 new value, EXPLAIN with an
unclassified leaf)."""
import copy
import hashlib
import sys
from pathlib import Path

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import k92_a27 as a27  # noqa: E402
import k92_a29 as a29  # noqa: E402
import k92_compare as cmp  # noqa: E402
import k92_gates as kg  # noqa: E402

LANE = 'evaluation/controllers/lane_offramp_runtime.py'
BODY = b'a = 1\nb = 2\n'
OLD_RS, NEW_RS = b'old rs\n', b'new rs\n'
TAG_O = 'd:/vissim-merge/k8_gate_trees/k92b1/a25/ref_t74_cwf'
TAG_N = 'd:/vissim-merge/k8_gate_trees/k92b1/k921_t74_w'


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(a27, 'CR_FILES', {LANE: (_sha(BODY), _sha(BODY.replace(b'\n', b'\r\n')))})
    monkeypatch.setattr(cmp, 'KNOWN_OLD_RS', frozenset({_sha(OLD_RS)}))
    ro = a29._tree(tmp_path / 'ro', OLD_RS, {LANE: BODY})
    rn = a29._tree(tmp_path / 'rn', NEW_RS, {LANE: BODY})
    return ro, rn


def _pair(tmp_path, name, va=None, vb=None, md_o=None, md_n=None, green_n=30.0, xs_o=None, xs_n=None):
    o = a29._dec(tmp_path / name / 'o', 3750, TAG_O, va or _sha(OLD_RS), md=md_o, extra_src=xs_o)
    n = a29._dec(tmp_path / name / 'n', 3750, TAG_N, vb or _sha(NEW_RS), md=md_n, green=green_n, extra_src=xs_n)
    return o, n


def test_selftests():
    r29, r27 = a29.selftest(), a27.selftest()
    assert r29['verdict'] == 'PASS', [c for c in r29['cases'] if not c['ok']]
    assert r27['verdict'] == 'PASS', [c for c in r27['cases'] if not c['ok']]


def test_a_k92_old_root_condition(tmp_path, monkeypatch):
    ro, rn = _setup(tmp_path, monkeypatch)
    o, n = _pair(tmp_path, 'p')
    r = cmp.compare(o, n, 3750, rn, old_root=ro)
    assert r['verdict'] == 'PASS' and r['allowed_counts'] == {'A_K92': 1} and r['old_root'] == str(ro)
    assert r['k92_checks'] == [{'path': a29.LEAF_A_K92, 'rule': 'A_K92', 'ok': True, 'new_is_root_rs': True,
                                'old_is_root_rs': True, 'old_known': True}]
    # R2-D1: an old value that is a known RS but not the old tree's RS bytes is unclassified (K9-2-4 allowed it)
    other = a29._tree(tmp_path / 'other', b'another old rs\n', {LANE: BODY})
    r = cmp.compare(o, n, 3750, rn, old_root=other)
    assert r['verdict'] == 'HOLD' and r['k92_checks'][0]['old_is_root_rs'] is False
    assert r['k92_checks'][0]['old_known'] is True and r['unclassified'][0]['why'] == 'A_K92 condition false'
    r = cmp.compare(o, n, 3750, rn)                                   # no old root given
    assert r['verdict'] == 'HOLD' and r['old_root'] is None
    monkeypatch.setattr(cmp, 'KNOWN_OLD_RS', frozenset())             # the old tree's RS, but not a known value
    assert cmp.compare(o, n, 3750, rn, old_root=ro)['verdict'] == 'HOLD'


def test_a_k92_new_value_condition(tmp_path, monkeypatch):
    """O-1 gap M13: the new value must be the new tree's runtime_setup.py sha."""
    ro, rn = _setup(tmp_path, monkeypatch)
    o, n = _pair(tmp_path, 'p', vb='f' * 64)
    r = cmp.compare(o, n, 3750, rn, old_root=ro)
    assert r['verdict'] == 'HOLD' and r['k92_checks'][0]['new_is_root_rs'] is False
    o, n = _pair(tmp_path, 'q')
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert cmp.compare(o, n, 3750, empty, old_root=ro)['verdict'] == 'HOLD'      # no runtime_setup.py: no exception


def test_k92m_sides_and_depth(tmp_path, monkeypatch):
    ro, rn = _setup(tmp_path, monkeypatch)
    ev = b'{"schema": "ev"}'
    a29._w(rn / 'ev.json', ev)
    keyed = {'seed': None, 'floor_key': None, 'evidence_sha256': {'k92_w': _sha(ev)},
             'evidence_file': {'k92_w': 'ev.json'}}
    w = {'evidence_sha256': _sha(ev), 'u4_sha256': cmp.U4_SHA256, 'heads': ['a'], 'after': 1.0}
    cap = {'before': {'x': 1.0}, 'after': {'x': 2.0}}
    o, n = _pair(tmp_path, 'a', md_n={'k92_w': w}, md_o={'k92_attrib_capacity_override': cap})
    r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
    assert r['verdict'] == 'PASS' and r['allowed_counts'].get('A_K92-M') == 2
    o, n = _pair(tmp_path, 'b', md_o={'k92_w': w}, md_n={'k92_attrib_capacity_override': cap})
    r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
    assert r['verdict'] == 'HOLD' and r['unclassified_n'] == 2
    assert sorted(c['side'] for c in r['k92_checks'] if 'side' in c) == ['new', 'old']
    assert all(c['why'].startswith('side:') for c in r['k92_checks'] if 'side' in c)
    for sub in (dict(w, deep={'evidence_sha256': '0' * 64}), dict(w, deep={'x_sha256': 'a' * 64}),
                dict(w, heads=[{'y_sha256': 'a' * 64}]), dict(w, deep={'action_token': 't'}),
                dict(w, rule_code_sha256=[cmp.RULE_CODE_SHA256])):
        o, n = _pair(tmp_path, 'd%d' % id(sub), md_n={'k92_w': sub})
        assert cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'HOLD'
    a29._w(ro / 'ev_old.json', ev)
    a29._w(rn / 'ev_old.json', ev)            # an old side read from the new root (K9-2-4) would pass
    keyed_o = {'seed': None, 'floor_key': None, 'evidence_sha256': {'k92_attrib_capacity_override': _sha(ev)},
               'evidence_file': {'k92_attrib_capacity_override': 'ev_old.json'}}
    # the same RS value on both sides (no A_K92 leaf): only the A_K92-M rule decides
    o, n = _pair(tmp_path, 'e', va=_sha(NEW_RS), md_o={'k92_attrib_capacity_override': dict(cap, evidence_sha256=_sha(ev))})
    assert cmp.compare(o, n, 3750, rn, keyed=keyed_o, old_root=ro)['verdict'] == 'PASS'
    assert cmp.compare(o, n, 3750, rn, keyed=keyed_o)['verdict'] == 'HOLD'        # the old side's root is old_root
    a29._w(rn / 'ev_bad.json', b'{"schema": "other"}')                             # pinned value, other file bytes
    keyed_bad = dict(keyed, evidence_file={'k92_w': 'ev_bad.json'})
    o, n = _pair(tmp_path, 'f', va=_sha(NEW_RS), md_n={'k92_w': w})
    assert cmp.compare(o, n, 3750, rn, keyed=keyed_bad, old_root=ro)['verdict'] == 'HOLD'
    assert cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'PASS'
    # review A29: the u4_sha256 / rule_code_sha256 values at any depth, the D rules on the N path (upper-case keys),
    # the side of each of the five subtrees, and the two kept rules alone (both sides present and different; key-off)
    for name, sub, want in (('u4bad', dict(w, u4_sha256='f' * 64), 'HOLD'),
                            ('rcbad', dict(w, deep={'rule_code_sha256': '0' * 64}), 'HOLD'),
                            ('rcgood', dict(w, deep={'rule_code_sha256': cmp.RULE_CODE_SHA256}), 'PASS'),
                            ('upper', dict(w, deep={'X_SHA256': 'a' * 64}), 'HOLD'),
                            ('uppertok', dict(w, deep={'PLAN_ACTION_TOKEN': 't'}), 'HOLD')):
        o, n = _pair(tmp_path, name, md_n={'k92_w': sub})
        assert cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == want, name
    for name, val, new_side in (('k92_hb', {'seed': 1384.6, 'rule_code_sha256': cmp.RULE_CODE_SHA256}, True),
                                ('k92_hb_seed_binding', 1.0, True), ('k92_attrib_capacity_override', cap, False),
                                ('k92_attrib_head_173_p4_seed', 1384.6, False)):
        own, other = ('md_n', 'md_o') if new_side else ('md_o', 'md_n')
        o, n = _pair(tmp_path, 'own_' + name, **{own: {name: val}})
        r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
        assert r['verdict'] == 'PASS' and r['allowed_counts'].get('A_K92-M') == 1, name
        o, n = _pair(tmp_path, 'other_' + name, **{other: {name: val}})
        r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
        assert r['verdict'] == 'HOLD' and [c['why'][:5] for c in r['k92_checks'] if 'side' in c] == ['side:'], name
    o, n = _pair(tmp_path, 'both', md_o={'k92_w': dict(w, wall_sec=1.0)}, md_n={'k92_w': dict(w, wall_sec=2.0)})
    r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
    assert r['verdict'] == 'HOLD' and [u['why'] for u in r['unclassified']] == ['A_K92-M: both sides present and differ']
    o, n = _pair(tmp_path, 'keyoff', md_n={'k92_hb_seed_binding': 1.0})
    r = cmp.compare(o, n, 3750, rn, old_root=ro)
    assert r['verdict'] == 'HOLD' and [u['why'] for u in r['unclassified']] == ['A_K92-M: not one-sided or not key-on']


def test_judges_pass_old_root(tmp_path, monkeypatch):
    ro, rn = _setup(tmp_path, monkeypatch)
    o, n = _pair(tmp_path, 'p')
    assert kg.judge_g2(o, n, 3750, rn, None, ro)['verdict'] == 'PASS'
    assert kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)['verdict'] == 'PASS'
    assert kg.judge_hard(o, n, 3750, rn, None, old_root=ro)['verdict_full'] == 'PASS'
    assert kg.judge_hard(o, n, 3750, rn, None)['verdict_full'] == 'HOLD'
    assert kg.judge_decisions([('x', str(o), str(n), 3750, str(rn), str(ro))])['verdict'] == 'PASS'
    assert kg.judge_decisions([('x', str(o), str(n), 3750, str(rn))])['rows']['x']['verdict'] == 'HOLD'
    assert kg.report_g2e(o, n, 3750, rn, None, old_root=ro)['unclassified_n'] == 0


def test_g4_cr_pair_and_explain(tmp_path, monkeypatch):
    """O-1 gaps M10 (G-K4 decision rows check the CR pair) and M09 (EXPLAIN needs 0 unclassified leaves)."""
    ro, rn = _setup(tmp_path, monkeypatch)
    crlf = a29._tree(tmp_path / 'crlf', NEW_RS, {LANE: BODY.replace(b'\n', b'\r\n')})
    o, n = _pair(tmp_path, 'p')
    r = kg.judge_g4_decision_full(o, n, 3750, crlf, None, ro)
    assert r['verdict'] == 'INCOMPLETE' and r['cr_pair']['bad'] == [LANE]
    o, n = _pair(tmp_path, 'e', green_n=30.0 * (1 + 1e-12))
    assert kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)['verdict'] == 'EXPLAIN'
    o, n = _pair(tmp_path, 'f', green_n=30.0 * (1 + 1e-12), xs_o={'evaluation/controllers/x.py': 'c' * 64},
                 xs_n={'evaluation/controllers/x.py': 'd' * 64})
    r = kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)
    assert r['verdict'] == 'FAIL' and r['numeric']['status'] == 'PASS' and r['unclassified_n'] == 1


def test_n_amendment27_text(tmp_path):
    """D-K9-54 (VERIFY_IMPL_r2 O-2): a file directly under k92b1 and a same-name file at a tree top differ; the group
    names are not roots under k92attrib; tree paths with the same rest still meet."""
    g = 'D:/VISSIM-merge/k8_gate_trees/'
    assert cmp.norm_s(g + 'k92b1/k921.build.json') != cmp.norm_s(g + 'k92b1/k921_t74_W/k921.build.json')
    assert cmp.norm_s(g + 'k92b1/k921_t74_W/k921.build.json') == '<root>/k921.build.json'
    assert cmp.norm_s(g + 'k92attrib/a25') == 'd:/vissim-merge/k8_gate_trees/k92attrib/a25'
    assert not a27.tree_root_ok(g + 'k92attrib/a25') and a27.tree_root_ok(g + 'k92attrib/t74_X1H1')
    assert cmp.norm_s(g + 'k92attrib/t74_CW/evaluation/a.py') == cmp.norm_s(g + 'k92b1/a27/k925/evaluation/a.py')
    assert cmp.norm_s(g + 'k92b1') != cmp.norm_s(g + 'k92b1/k921_t74_W')
    assert cmp.norm_s(g + 'k91t/a.py') == '<root>/a.py' == cmp.norm_s(g + 'k92b1x/a.py')
    m, s = a29._merge_check(cmp.norm_s)
    assert not m and not s


def test_recomparison_helpers(tmp_path, monkeypatch):
    ro, rn = _setup(tmp_path, monkeypatch)
    o, n = _pair(tmp_path, 'p')
    rep5 = cmp.compare(o, n, 3750, rn, old_root=ro)
    rep4 = a29.strip29(rep5)
    assert set(rep5) - set(rep4) == {'old_root'} and 'old_is_root_rs' not in rep4['k92_checks'][0]
    assert a29.same29(rep4, rep5, old_root=ro)['ok'] and not a29.same29(rep4, rep5, old_root=rn)['ok']
    bad = copy.deepcopy(rep5)
    bad['unclassified_n'] = 1
    assert not a29.same29(rep4, bad)['ok']
    row5 = kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)
    assert a29.same29(a29.strip29(row5), row5)['ok'] and not a29.same29(row5, row5)['ok']
    c = {'path': a29.LEAF_A_K92, 'rule': 'A_K92', 'ok': False, 'new_is_root_rs': True, 'old_is_root_rs': True,
         'old_known': False}
    assert a29.w12({'k92_checks': [c]}, 1)['ok'] and not a29.w12({'k92_checks': [dict(c, old_is_root_rs=False)]}, 1)['ok']
    assert not a29.w12({'k92_checks': [c]}, 2)['ok']
    text = (SA / 'k92_gates.py').read_text(encoding='utf-8')
    assert a29.plant_source_same(text, text)['ok']
    assert not a29.plant_source_same(text, text.replace('def judge_g4_plant(probe_job, new_job, path_roots):',
                                                        'def judge_g4_plant(probe_job, new_job, path_roots=()):'))['ok']
