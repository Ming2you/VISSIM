"""K9-2-4 tests (amendment 27; synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_a27.py -v
K8_PREDECLARATION_AMENDMENT_27: the K9-2 tree-root rule of N (section 2.1), the CR pair rule (section 2.2), the
four-outcome G-K2 judge and the all-leaf G-K4 decision judge (section 2.3), and the R-old judges (section 3.3).
Amendment 29 (K9-2-5): the reference tree's runtime_setup.py bytes now give the old A_K92 value (OLD_RS, made a
known value with monkeypatch), the comparisons pass old_root, and the bundle / group folders keep their own text."""
import hashlib
import json
import sys
from pathlib import Path

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import k92_a27 as a27  # noqa: E402
import k92_compare as cmp  # noqa: E402
import k92_gates as kg  # noqa: E402

REF_ROOT = 'D:/VISSIM-merge/k8_gate_trees/k92b1/a25/ref_t74_CWf'
NEW_ROOT = 'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/rj_k921_t74_W_cr'
CTRL = 'evaluation/controllers/'
LANE = CTRL + 'lane_offramp_runtime.py'
BODY = b'a = 1\nb = 2\n'


def _sha(b):
    return hashlib.sha256(b).hexdigest()


OLD_RS = _sha(b'old rs\n')         # amendment 29: the reference tree's runtime_setup.py sha = the old A_K92 value


def _tree(path, rs=b'new rs\n', lane=BODY):
    p = Path(path)
    (p / CTRL).mkdir(parents=True, exist_ok=True)
    (p / CTRL / 'runtime_setup.py').write_bytes(rs)
    if lane is not None:
        (p / LANE).write_bytes(lane)
    return p


def _dec(path, T, root_tag, src, green=30.0, md=None, csv='x\n'):
    d = Path(path)
    d.mkdir(parents=True, exist_ok=True)
    doc = {'N_P_star': {}, 'N_UF_star': {}, 'ramp_metering': {}, 'vsl': {}, 'green_times': {'SC109_p3': green},
           'offsets': {}, 'inflow_outflow_allocation': {},
           'metadata': dict(md or {}, joint_leader_selection={
               'selected_objective': 1.0, 'held_objective': 1.0, 'warm_start_objective': 1.0,
               'selection_status': 'ok', 'converged': True, 'feasible': True,
               'tangent_derivatives': [{'transformed_source_sha256': {root_tag + '/' + k: v for k, v in src.items()}}]})}
    (d / ('action_%06d.json' % T)).write_text(json.dumps(doc), encoding='utf-8')
    if csv is not None:
        (d / ('action_%06d.csv' % T)).write_text(csv, encoding='utf-8')
    return d


def _pair(tmp_path, *, lane_new=None, green_new=30.0, rs_old=None, csv_new='x\n', ws=False):
    ref_tree = _tree(tmp_path / 'ref_tree', rs=b'old rs\n')
    new_tree = _tree(tmp_path / 'new_tree')
    rs_new = cmp.sha_file(new_tree / CTRL / 'runtime_setup.py')
    rs_old = rs_old or OLD_RS              # amendment 29: = the reference tree's RS sha (known through monkeypatch)
    src_old = {CTRL + 'runtime_setup.py': rs_old, LANE: _sha(BODY), CTRL + 'x.py': 'c' * 64}
    src_new = {CTRL + 'runtime_setup.py': rs_new, LANE: lane_new or _sha(BODY), CTRL + 'x.py': 'c' * 64}
    md_old = {'run_provenance': {'workspace_root': REF_ROOT}} if ws else None      # R3-04, a path-string item
    md_new = {'run_provenance': {'workspace_root': NEW_ROOT}} if ws else None
    old = _dec(tmp_path / 'o', 3750, REF_ROOT, src_old, md=md_old)
    new = _dec(tmp_path / 'n', 3750, NEW_ROOT, src_new, green=green_new, md=md_new, csv=csv_new)
    return old, new, ref_tree, new_tree


def test_root_rule_and_selftest():
    rules = [r for r, _ in cmp.N2]
    assert rules.count(a27.K92_ROOT_RULE) == 1
    assert rules.index(a27.K92_ROOT_RULE) < [i for i, r in enumerate(rules) if 's31fail' in r][0]
    assert cmp.norm_s(REF_ROOT + '/' + LANE) == cmp.norm_s(NEW_ROOT + '/' + LANE) == '<root>/' + LANE
    assert cmp.norm_s('D:/VISSIM-merge/k8_gate_trees/k91t/' + LANE) == '<root>/' + LANE
    assert a27.tree_root_ok(NEW_ROOT) and a27.tree_root_ok(REF_ROOT) and not a27.tree_root_ok(NEW_ROOT + '/x')
    # review r2: only a whole path component that is a tree name is a root (files / group folders keep the old form)
    gt = 'D:/VISSIM-merge/k8_gate_trees/'
    assert cmp.norm_s(gt + 'k92b1/a25/k92b1_probe.build.json') != cmp.norm_s(gt + 'k92b1/k921.build.json')
    assert cmp.norm_s(gt + 'k92b1/a25/a.py') != cmp.norm_s(gt + 'k92b1/a27/a.py')
    assert cmp.norm_s(gt + 'k92b1/a25') == 'd:/vissim-merge/k8_gate_trees/k92b1/a25' and not a27.tree_root_ok(
        gt + 'k92b1/a25')                                       # amendment 29: a group folder keeps its own text
    assert cmp.norm_s(REF_ROOT + '/' + LANE) != cmp.norm_s(NEW_ROOT + '/' + LANE.replace('lane', 'lan'))
    r = a27.selftest()
    assert r['verdict'] == 'PASS', [c for c in r['cases'] if not c['ok']]


def test_cr_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(a27, 'CR_FILES', {LANE: (_sha(BODY), _sha(BODY.replace(b'\n', b'\r\n')))})
    ref = _tree(tmp_path / 'r')
    same = _tree(tmp_path / 's')
    crlf = _tree(tmp_path / 'c', lane=BODY.replace(b'\n', b'\r\n'))
    gone = _tree(tmp_path / 'g', lane=None)
    assert a27.cr_pair(ref, same)['ok'] and a27.cr_pair(ref, same)['ref_form'] == 'C'
    assert a27.cr_pair(ref, crlf)['bad'] == [LANE] and a27.cr_pair(crlf, crlf)['ok']
    assert not a27.cr_pair(ref, gone)['ok']
    assert not a27.cr_pair(gone, ref)['ok']                       # reference holds no file of known form
    assert not a27.cr_pair(tmp_path / 'missing', ref)['ok']


def test_judge_g2_four_outcomes(tmp_path, monkeypatch):
    monkeypatch.setattr(a27, 'CR_FILES', {LANE: (_sha(BODY), _sha(BODY.replace(b'\n', b'\r\n')))})
    monkeypatch.setattr(cmp, 'KNOWN_OLD_RS', frozenset({OLD_RS}))
    old, new, ref_tree, new_tree = _pair(tmp_path)
    r = kg.judge_g2(old, new, 3750, new_tree, None, ref_tree)
    assert r['verdict'] == 'PASS' and r['hard_verdict'] == 'SAME' and r['allowed_counts'].get('A_K92') == 1
    # the D-1 shape: HARD same, one unclassified D5 value leaf -> HOLD (judge_hard alone said SAME)
    old2, new2, _, _ = _pair(tmp_path / 'h', lane_new=_sha(BODY.replace(b'\n', b'\r\n')))
    r2 = kg.judge_g2(old2, new2, 3750, new_tree, None, ref_tree)
    assert r2['hard_verdict'] == 'SAME' and r2['verdict'] == 'HOLD' and r2['unclassified_n'] == 1
    old3, new3, _, _ = _pair(tmp_path / 'f', green_new=31.0)
    assert kg.judge_g2(old3, new3, 3750, new_tree, None, ref_tree)['verdict'] == 'FAIL'
    old4, new4, _, _ = _pair(tmp_path / 'i', csv_new=None)
    assert kg.judge_g2(old4, new4, 3750, new_tree, None, ref_tree)['verdict'] == 'INCOMPLETE'
    crlf_tree = _tree(tmp_path / 'crlf_tree', lane=BODY.replace(b'\n', b'\r\n'))
    r5 = kg.judge_g2(old, new, 3750, crlf_tree, None, ref_tree)
    assert r5['verdict'] == 'INCOMPLETE' and r5['cr_pair']['bad'] == [LANE]
    # the same pair under the N without the amendment 27 rule: every D5 key one-sided -> HOLD
    monkeypatch.setattr(cmp, 'N2', [x for x in cmp.N2 if x[0] != a27.K92_ROOT_RULE])
    r6 = kg.judge_g2(old, new, 3750, new_tree, None, ref_tree)
    assert r6['hard_verdict'] == 'SAME' and r6['verdict'] == 'HOLD' and r6['unclassified_n'] == 6


def test_judge_g4_decision_full(tmp_path, monkeypatch):
    monkeypatch.setattr(a27, 'CR_FILES', {LANE: (_sha(BODY), _sha(BODY.replace(b'\n', b'\r\n')))})
    monkeypatch.setattr(cmp, 'KNOWN_OLD_RS', frozenset({OLD_RS}))
    old, new, ref_tree, new_tree = _pair(tmp_path)
    assert kg.judge_g4_decision_full(old, new, 3750, new_tree, None, ref_tree)['verdict'] == 'PASS'
    o, n, _, _ = _pair(tmp_path / 'e', green_new=30.0 * (1 + 1e-12))
    r = kg.judge_g4_decision_full(o, n, 3750, new_tree, None, ref_tree)
    assert r['verdict'] == 'EXPLAIN' and r['numeric']['status'] == 'PASS' and r['numeric']['numeric_diffs'] == 1
    o, n, _, _ = _pair(tmp_path / 'f', green_new=31.0)
    assert kg.judge_g4_decision_full(o, n, 3750, new_tree, None, ref_tree)['verdict'] == 'FAIL'
    o, n, _, _ = _pair(tmp_path / 'h', lane_new='d' * 64)
    assert kg.judge_g4_decision_full(o, n, 3750, new_tree, None, ref_tree)['verdict'] == 'HOLD'
    o, n, _, _ = _pair(tmp_path / 'k', rs_old='e' * 64)            # old RS not a known A_K92 value -> unclassified
    r = kg.judge_g4_decision_full(o, n, 3750, new_tree, None, ref_tree)
    assert r['verdict'] == 'HOLD' and r['unclassified'][0]['why'] == 'A_K92 condition false'
    o, n, _, _ = _pair(tmp_path / 'i', csv_new=None)
    assert kg.judge_g4_decision_full(o, n, 3750, new_tree, None, ref_tree)['verdict'] == 'INCOMPLETE'


def test_rold_judges(tmp_path):
    text = (SA / 'k92_compare.py').read_text(encoding='utf-8')
    line = "    (r'" + a27.K92_ROOT_RULE + "', '<root>'),   # amendment 29 (K9-2 tree roots)\n"
    generic = "    (r'" + a27.GENERIC_RULE_A29 + "', '<root>'),   # amendment 29 (bundle folders are not trees)\n"
    assert text.count(line) == 1 and text.count(generic) == 1
    (tmp_path / 'old_cmp.py').write_text(text.replace(line, '').replace(
        generic, "    (r'" + a27.GENERIC_RULE_A21 + "', '<root>'),\n"), encoding='utf-8')      # the K9-2-0 N
    old_mod = a27.load_comparator(tmp_path / 'old_cmp.py', 'k92_compare_old_t')
    new_mod = a27.load_comparator(SA / 'k92_compare.py', 'k92_compare_new_t')
    new_mod.KNOWN_OLD_RS = frozenset({OLD_RS})
    old, new, ref_tree, new_tree = _pair(tmp_path, ws=True)
    ro = old_mod.compare(old, new, 3750, new_tree)
    rn = new_mod.compare(old, new, 3750, new_tree, old_root=ref_tree)
    assert ro['verdict'] == 'HOLD' and rn['verdict'] == 'PASS'
    assert ro['allowed_counts'].get('R3-04') == 1 and 'R3-04' not in rn['allowed_counts']    # root-only difference gone
    tails = [old_mod.norm_s(REF_ROOT), old_mod.norm_s(NEW_ROOT)]
    j = a27.rold_judge_r(ro, rn, tails)
    assert j['verdict'] == 'PASS' and j['removed_n'] == 6 and j['added_n'] == 0 and j['a_k92_delta'] == 1
    assert j['path_allowed_delta'] == {'R3-04': -1} and j['checks']['path_allowed_not_increased']
    o2, n2, _, _ = _pair(tmp_path / 'h', lane_new='d' * 64)
    j2 = a27.rold_judge_r(old_mod.compare(o2, n2, 3750, new_tree),
                          new_mod.compare(o2, n2, 3750, new_tree, old_root=ref_tree), tails)
    assert j2['verdict'] == 'PASS' and [x['path'][-len(LANE):] for x in j2['revealed']] == [LANE]
    gwt8 = 'd:/vissim-merge/sim3-n31-k8'
    src = {CTRL + 'runtime_setup.py': cmp.sha_file(new_tree / CTRL / 'runtime_setup.py'), LANE: _sha(BODY)}
    a = _dec(tmp_path / 'ka', 900, gwt8, src)
    b = _dec(tmp_path / 'kb', 900, gwt8, src)
    k = a27.rold_judge_k(old_mod.compare(a, b, 900, new_tree), new_mod.compare(a, b, 900, new_tree))
    assert k['verdict'] == 'PASS' and k['identical']
