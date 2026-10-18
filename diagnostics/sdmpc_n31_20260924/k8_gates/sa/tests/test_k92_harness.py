"""K9-2-0 harness tests (synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_harness.py -v
K8_PREDECLARATION_AMENDMENT_24 (fixed d46db6dc...): the K9-2 blind guard (section 3.1-3a (a)-(f)), the section 3.1-3b
VISSIM blindness of the recorder, the K9-2 comparison additions (A_K92, A_K92-M, the declared H5 difference; section
4.2), the k92 record (section 2.0-7), and the gate calculators of k92_gates (U, G-K1 static / dynamic, G-K5, F)."""
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import sa_common as sc  # noqa: E402
import k92_common as g  # noqa: E402
import k92_compare as cmp  # noqa: E402
import k92_record as rec  # noqa: E402
import k92_gates as kg  # noqa: E402
import k92_vissim_ref as vr  # noqa: E402

N31 = SA.parents[1]
SAF_K91 = N31 / 'config_n31_v2_stopline_observed_full_k91.json'
K86H_SAF = N31 / 'config_n31_v2_stopline_observed_full.json'
NONE = SimpleNamespace(gates_stage=None, declaration_sha=None)
OPEN = SimpleNamespace(gates_stage='k92t', declaration_sha=g.K92_AMENDMENT24_SHA256)
PIN = {'evidence': 'e', 'evidence_sha256': '0' * 64}
KW = dict(op='job', harness='TL3', arm='SAF', entry='OBS', H=3)


@pytest.fixture
def out_root(tmp_path):
    sc.c.configure(out=tmp_path / 'gates_out')
    yield tmp_path / 'gates_out'
    sc.c.configure()


def _arm(tmp_path, name, w=True, hb=True):
    doc = json.loads(SAF_K91.read_text(encoding='utf-8'))
    if w:
        doc['urban']['sc109w_through_saturation'] = dict(PIN)
    if hb:
        doc['urban']['capacity']['head_floor_seed'] = dict(PIN)
    p = tmp_path / (name + '.json')
    p.write_text(json.dumps(doc), encoding='utf-8')
    return str(p)


# ------------------------------------------------------------------------------------------------ guard (3.1-3a)
def test_key_paths_and_strip(tmp_path):
    doc = json.loads(Path(_arm(tmp_path, 'b1')).read_text(encoding='utf-8'))
    assert g.k92_keys_of(doc) == ['urban.sc109w_through_saturation', 'urban.capacity.head_floor_seed']
    stripped = g.k92_strip(doc)
    assert g.k92_keys_of(stripped) == [] and json.dumps(stripped, sort_keys=True) == json.dumps(
        json.loads(SAF_K91.read_text(encoding='utf-8')), sort_keys=True)


def test_judging_state_classes():
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s47', 2400) == 'primary'                  # (a)
    assert all(g.k92_judging_state('sdmpc31_v3c3_nc_s47', T) == 'primary' for T in g.F_PRIMARY)
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s31', 1500) is None                       # (c) second sample
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s43', 1050) is None
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s47', 4800) is None                       # (c) K8b probe sample
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s31', 2700) == 'k91_judging'              # (b)
    assert g.k92_judging_state('sdmpc31_v3c3_nc_s43', 3750) == 'k91_judging'
    assert g.k92_judging_state('sdmpc31_v3c3_k8j1_s43', 3750) is None                     # (f) J1 run: no harness state
    assert len(g.F_PRIMARY) == 22 and len(g.F_SECOND_STATES) == 16


def test_guard_cases(tmp_path, out_root):
    b1, w = _arm(tmp_path, 'b1'), _arm(tmp_path, 'w', hb=False)
    seed_only = _arm(tmp_path, 'seed', w=False)
    with pytest.raises(SystemExit, match='K92_BLIND_REFUSED'):
        g.k92_guard(b1, 47, 2400, NONE, 't', **KW)
    with pytest.raises(SystemExit, match='K92_BLIND_REFUSED'):
        g.k92_guard(str(K86H_SAF), 47, 1050, NONE, 't', op='capture', harness='TL3', arm='SAF')
    with pytest.raises(SystemExit, match='K92_BLIND_REFUSED'):
        g.k92_guard(w, 31, 2700, NONE, 't', **KW)
    assert g.k92_guard(str(K86H_SAF), 31, 4500, NONE, 't', op='capture', harness='DP', arm='SAF') == []
    assert g.k92_guard(b1, 43, 1050, NONE, 't', **KW)[-2:] == ['urban.sc109w_through_saturation',
                                                               'urban.capacity.head_floor_seed']
    for args in (NONE, OPEN):
        with pytest.raises(SystemExit, match='K92_SEED_ALONE_REFUSED'):
            g.k92_guard(seed_only, 41, 1500, args, 't', **KW)
    with pytest.raises(SystemExit, match='K92_SEED_ALONE_REFUSED'):
        g.k92_guard(str(SAF_K91), 31, 1500, NONE, 't', extra_keys=['capture metadata k92_hb'], **KW)
    for stage, sha in (('k91t', sc.K91_AMENDMENT19_SHA256), ('k8bt', sc.K8B_AMENDMENT16_SHA256),
                       ('k92t', '0' * 64)):
        with pytest.raises(SystemExit, match='K92_STAGE_REFUSED'):
            g.k92_guard(b1, 31, 1500, SimpleNamespace(gates_stage=stage, declaration_sha=sha), 't', **KW)
    assert not (out_root / 'sa' / 'k92_judging_stage.json').exists()
    g.k92_guard(b1, 47, 2400, OPEN, 'first', **KW)
    mark = json.loads((out_root / 'sa' / 'k92_judging_stage.json').read_text(encoding='utf-8'))
    assert mark['first']['what'] == 'first' and mark['amendment24_sha256'] == g.K92_AMENDMENT24_SHA256


# ------------------------------------------------------------------------------------------------ 3.1-3b / record
def test_vissim_blindness_and_record_reason():
    assert g.k92_vissim_blind(47, NONE) is True and g.k92_vissim_blind(47, OPEN) is False
    assert g.k92_vissim_blind(31, NONE) is False and g.k92_vissim_blind(47) is True
    r47 = rec.build({'seed': 47, 'label': 'x'}, 0.0, 150.0, 3, None)
    r31 = rec.build({'seed': 31, 'label': 'x'}, 0.0, 150.0, 3, None)
    assert r47['vissim'] is None and r47['vissim_reason'] == g.K92_BLIND_REASON
    assert r31['vissim'] is None and r31['vissim_reason'] == 'k92_vissim_ref'


def test_record_from_rows():
    rec.K92.update(rows=[], keys={}, edges=set(), dep={}, errors=[], recv_limited=set(), responses=0)
    rec.STAGES.clear()
    rec.K92['cap'] = {rec.W: 3600.0, rec.L: 413.0}
    rows, transfers = [], []
    for t in range(1, 451):
        mv = {k: float(t) for k in rec.CHAIN}
        mv['storage:SC109_E_out'] = 10.0 + t / 10.0
        mv['storage:in_SC109_E'] = 2.0
        rows.append({'stage': 'urban', 'start_sec': float(t - 1), 'end_sec': float(t), 'dt_h': 1 / 3600.0,
                     'model_stock_veh': mv, 'inside_veh': {k: 0.0 for k in mv}})
        transfers.append({'source': 'movement:' + rec.W, 'target': 'storage:SC109_E_out', 'vehicles': 1.0,
                          'end_sec': float(t)})
    rec.collect({'residence': rows, 'transfers': transfers}, 0.0, 150.0)
    r = rec.build({'seed': 31, 'label': 'x'}, 0.0, 150.0, 3, {'k92_w': True, 'k92_hb': False})
    h = r['horizon']
    assert h['m1_chain_T150'] == 3 * 150.0 and h['m1_chain_T450'] == 3 * 450.0
    assert h['m2_w_dep_T150'] == 150.0 and h['m2_w_dep_T450'] == 450.0 and h['m3_l_dep_T450'] == 0.0
    assert abs(h['e_out_max'] - 55.0) < 1e-12 and abs(h['e_out_max_over_220'] - 55.0 / 220.0) < 1e-12
    assert h['w_capacity_bound_steps'] == 450 and r['edges'] == 1 and not r['errors']


# ------------------------------------------------------------------------------------------------ comparison (4.2)
def _decision(path, T, md, root_tag='d:/vissim-merge/sim3-n31-k8', rs_sha='a' * 64):
    d = Path(path)
    d.mkdir(parents=True, exist_ok=True)
    doc = {'N_P_star': {}, 'N_UF_star': {}, 'ramp_metering': {}, 'vsl': {}, 'green_times': {'SC109_p3': 30.0},
           'offsets': {}, 'inflow_outflow_allocation': {},
           'metadata': dict(md, joint_leader_selection={
               'selected_objective': 1.0, 'held_objective': 1.0, 'warm_start_objective': 1.0,
               'selection_status': 'ok', 'converged': True, 'feasible': True,
               'tangent_derivatives': [{'transformed_source_sha256': {
                   root_tag + '/evaluation/controllers/runtime_setup.py': rs_sha}}]})}
    (d / ('action_%06d.json' % T)).write_text(json.dumps(doc), encoding='utf-8')
    (d / ('action_%06d.csv' % T)).write_text('x\n', encoding='utf-8')
    return d


def test_a_k92_rs_key(tmp_path):
    root = tmp_path / 'root'
    (root / 'evaluation' / 'controllers').mkdir(parents=True)
    (root / 'evaluation' / 'controllers' / 'runtime_setup.py').write_bytes(b'new rs')
    new_sha = cmp.sha_file(root / 'evaluation' / 'controllers' / 'runtime_setup.py')
    old = _decision(tmp_path / 'o', 900, {}, rs_sha=sorted(cmp.KNOWN_OLD_RS)[0])
    new = _decision(tmp_path / 'n', 900, {}, rs_sha=new_sha)
    r = cmp.compare(old, new, 900, root)
    assert r['verdict'] == 'PASS' and r['allowed_counts'].get('A_K92') == 1
    bad = _decision(tmp_path / 'b', 900, {}, rs_sha='b' * 64)
    r2 = cmp.compare(bad, new, 900, root)
    assert r2['verdict'] == 'HOLD'


def test_a_k92_m_and_h5(tmp_path):
    root = tmp_path / 'root'
    (root / 'evaluation' / 'controllers').mkdir(parents=True)
    (root / 'evaluation' / 'controllers' / 'runtime_setup.py').write_bytes(b'rs')
    ev = root / 'ev.json'
    ev.write_bytes(b'{"schema": "x"}')
    ev_sha = cmp.sha_file(ev)
    rs = cmp.sha_file(root / 'evaluation' / 'controllers' / 'runtime_setup.py')
    s = 1045.1612903225805
    key = 'head_discharge_floor_173_p4_301ceabb95f116fa'
    old = _decision(tmp_path / 'o', 3900, {}, rs_sha=rs)
    md = {'k92_hb': {'evidence_sha256': ev_sha, 'rule_code_sha256': cmp.RULE_CODE_SHA256}, 'k92_hb_seed_binding': 1.0,
          key: s}
    new = _decision(tmp_path / 'n', 3900, md, rs_sha=rs)
    keyed = {'seed': s, 'floor_key': key, 'evidence_sha256': {'k92_hb': ev_sha}, 'evidence_file': {'k92_hb': 'ev.json'}}
    r = cmp.compare(old, new, 3900, root, keyed=keyed)
    assert r['hard_verdict'] == 'SAME' and r['verdict'] == 'PASS' and r['h5_declared']
    assert cmp.compare(old, new, 3900, root)['hard_verdict'] == 'DIFFERENT'          # key-off rules: H5 differs
    wrong = dict(keyed, floor_key='head_discharge_floor_173_p4_0000000000000000')
    assert cmp.compare(old, new, 3900, root, keyed=wrong)['hard_verdict'] == 'DIFFERENT'
    md2 = dict(md, k92_hb_seed_binding=0.0)
    new2 = _decision(tmp_path / 'n2', 3900, md2, rs_sha=rs)
    assert cmp.compare(old, new2, 3900, root, keyed=keyed)['hard_verdict'] == 'DIFFERENT'
    md3 = dict(md, k92_hb={'evidence_sha256': '1' * 64, 'rule_code_sha256': cmp.RULE_CODE_SHA256})
    new3 = _decision(tmp_path / 'n3', 3900, md3, rs_sha=rs)
    assert cmp.compare(old, new3, 3900, root, keyed=keyed)['verdict'] == 'HOLD'


# ------------------------------------------------------------------------------------------------ gate calculators
def test_judge_u(tmp_path):
    base = {'a::x': ['passed', None], 'a::y': ['failed', 'assert 1 < 0']}
    new = dict(base, **{'k92::t': ['passed', None]})
    assert kg.judge_u(base, new, ['k92'])['verdict'] == 'PASS'
    assert kg.judge_u(base, dict(new, **{'a::x': ['failed', 'boom']}), ['k92'])['verdict'] == 'FAIL'
    assert kg.judge_u(base, dict(new, **{'k92::t': ['skipped', 'x']}), ['k92'])['verdict'] == 'FAIL'
    xml = tmp_path / 'r.xml'
    xml.write_text('<testsuites><testsuite><testcase classname="a" name="x"/><testcase classname="a" name="y">'
                   '<failure message="assert 1 &lt; 0&#10;more"/></testcase></testsuite></testsuites>', encoding='utf-8')
    assert kg.junit_results(xml) == {'a::x': ['passed', None], 'a::y': ['failed', 'assert 1 < 0']}


def test_judge_u_root_normalization():
    base = {'a::y': ['failed', r'assert D:\T\u_b9\x.py 0x1f']}
    new = {'a::y': ['failed', r'assert D:/T/u_new/x.py 0x2a'], 'k92::t': ['passed', None]}
    assert kg.judge_u(base, new, ['k92'], roots=[r'D:\T\u_b9', r'D:\T\u_new'])['verdict'] == 'PASS'
    assert kg.judge_u(base, new, ['k92'])['verdict'] == 'FAIL'


def test_judge_diff_b_g4_arm():
    ok = 'M\tdiagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_worker.py\nA\tdiagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_x.py'
    assert kg.judge_diff_k920(ok, '')['verdict'] == 'PASS'
    assert kg.judge_diff_k920(ok + '\nM\tevaluation/controllers/runtime_setup.py', '')['verdict'] == 'FAIL'
    assert kg.judge_diff_k920(ok, 'diff --git a/x b/x')['verdict'] == 'FAIL'
    row = {'rc': 0, 'stdout_last': 'K92_EVIDENCE_CHECK_OK w values_sha256=x', 'committed_sha256': kg.K92_PIN_SHA256['w']}
    assert kg.judge_b({'w': row})['verdict'] == 'PASS'
    assert kg.judge_b({'w': dict(row, committed_sha256='0' * 64)})['verdict'] == 'FAIL'
    assert kg.judge_b({'w': dict(row, rc=1)})['verdict'] == 'FAIL'
    assert kg.judge_g4_decision({'status': 'PASS', 'numeric_diffs': 0, 'csv_same': True}) == 'PASS'
    assert kg.judge_g4_decision({'status': 'PASS', 'numeric_diffs': 2, 'csv_same': True}) == 'EXPLAIN'
    assert kg.judge_g4_decision({'status': 'FAIL'}) == 'FAIL'
    rec = {'sa_arms': {'arm_sha256': kg.PROBE_B1_ARM_SHA256['t74']}, 'cfg_arm_sha256': kg.PROBE_B1_ARM_SHA256['t9b'],
           'cfg_arm_source': 'committed x'}
    assert kg.judge_arm_identity(rec, 0)['verdict'] == 'PASS'
    assert kg.judge_arm_identity(rec, 1)['verdict'] == 'FAIL'
    assert kg.judge_arm_identity(dict(rec, cfg_arm_source='k92_common in memory'), 0)['verdict'] == 'FAIL'
    blind = kg._blind({'examples': [['/a/b', 1.0, 2.0]], 'numeric_differ': 1})
    assert blind == {'examples': ['/a/b'], 'numeric_differ': 1}


def test_judge_g3_and_arm_check(tmp_path):
    root = tmp_path / 'r'
    for part in ('w', 'hb'):
        p = root / g.K92_EVIDENCE[part]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'{}')
    base = {'urban': {'capacity': {'head_observation': {}}, 'x': 1}}
    arm = json.loads(json.dumps(base))
    arm['urban']['sc109w_through_saturation'] = {'evidence': g.K92_EVIDENCE['w'],
                                                 'evidence_sha256': kg.K92_PIN_SHA256['w']}
    arm['urban']['capacity']['head_floor_seed'] = {'evidence': g.K92_EVIDENCE['hb'],
                                                   'evidence_sha256': kg.K92_PIN_SHA256['hb']}
    r = kg._arm_check(arm, base, root)
    assert r['paths_ok'] and not r['ok']          # the file bytes here are not the pinned evidence
    good = {'seed_only_valueerror': {'raised': True, 'names_dk931': True}, 'seed_only_attribute_set': False,
            'harness_refuses_seed_only': True,
            'sa_arms': {'rc': 0, 'k92_keys': ['urban.sc109w_through_saturation', 'urban.capacity.head_floor_seed']},
            'saf_arm': {'ok': True}, 'cfg_sha256': kg.CFG_SHA256, 'cfg_arm': {'ok': True},
            'cfg_arm_source': 'k92_common.apply_k92b1(CFG) in memory'}
    assert kg.judge_g3(good)['verdict'] == 'PASS'
    assert kg.judge_g3(good, need_committed_cfg_arm=True)['verdict'] == 'FAIL'
    assert kg.judge_g3(dict(good, harness_refuses_seed_only=False))['verdict'] == 'FAIL'


def test_judge_wall():
    rows = [{'clean': True, 'ok': True, 'ratio': r} for r in (1.0, 1.001, 0.999, 1.002, 1.0, 1.001, 0.998, 1.0)]
    assert kg.judge_wall(rows)['verdict'] == 'PASS'
    assert kg.judge_wall([dict(r, ratio=1.1) for r in rows])['verdict'] == 'FAIL'
    assert kg.judge_wall(rows[:7])['verdict'] == 'INCOMPLETE'
    wide = [{'clean': True, 'ok': True, 'ratio': r} for r in (0.97, 1.0, 1.01, 1.0, 0.98, 0.99, 1.02, 1.03)]
    res = kg.judge_wall(wide)                    # amendment 26 (D-K9-47): the IQR is reported, not judged
    assert res['verdict'] == 'PASS' and res['iqr'] > kg.IQR_LIMIT
    assert res['iqr_over_reference'] is True and res['iqr_report_only'] is True
    assert kg.judge_wall([dict(x, ratio=x['ratio'] + 0.03) for x in wide])['verdict'] == 'FAIL'
    assert kg.judge_wall([dict(x, ratio=kg.WALL_LIMIT) for x in wide])['verdict'] == 'PASS'


class _Net:
    pass


def _snap(d, caps, seed_attr=None, meta=None):
    import pickle
    d.mkdir(parents=True, exist_ok=True)
    n = _Net()
    n.movement_capacity_by_movement_veh_h = dict(caps)
    n.urban_movements = {'SC109_W_SC108_to_E': {'kind': 'boundary_out'}}
    if seed_attr is not None:
        n.head_floor_seed = seed_attr
    (d / 'network.pickle').write_bytes(pickle.dumps(n))
    (d / 'metadata.json').write_text(json.dumps(meta or {}), encoding='utf-8')
    return d


def test_judge_static(tmp_path):
    caps = {'SC109_W_SC108_to_E': 619.5918367346939, 'SC109_W_SC108_to_N_SC16': 413.0612244897959, 'x': 1.0}
    off = _snap(tmp_path / 'off', caps)
    on = _snap(tmp_path / 'on', dict(caps, SC109_W_SC108_to_E=5209.8), meta={'k92_w': {'after': 5209.8}})
    assert kg.judge_static(off, on, 'W')['verdict'] == 'PASS'
    bad = _snap(tmp_path / 'bad', dict(caps, SC109_W_SC108_to_E=5209.8, x=2.0))
    assert kg.judge_static(off, bad, 'W')['verdict'] == 'FAIL'
    s = 1045.1612903225805
    key = 'head_discharge_floor_173_p4_1170360c34e5b57b'
    b1 = _snap(tmp_path / 'b1', dict(caps, SC109_W_SC108_to_E=5209.8, SC109_W_SC108_to_N_SC16=s),
               seed_attr={('173', 'p4'): s}, meta={'k92_w': {}, 'k92_hb': {}, 'k92_hb_seed_binding': 1.0, key: s})
    assert kg.judge_static(off, b1, 'B1', seed=s, floor_key=key)['verdict'] == 'PASS'
    assert kg.judge_static(off, b1, 'W', seed=s, floor_key=key)['verdict'] == 'FAIL'


def _series(d, keys, model, edges, t=None):
    import numpy as np
    d.mkdir(parents=True, exist_ok=True)
    rows = len(model)
    np.savez_compressed(d / 'k92_series.npz', keys=np.array(keys, dtype=object),
                        t_end=np.array(t or [float(i + 1) for i in range(rows)]), stage=np.zeros(rows, dtype=np.int16),
                        model=np.array(model, dtype=float), edges=np.array(edges, dtype=object).reshape(-1, 2),
                        stage_names=np.array(['urban'], dtype=object))
    (d / 'summary.json').write_text(json.dumps({'objective': 1.0, 'blocks': []}), encoding='utf-8')
    return d


def test_judge_dynamic(tmp_path):
    keys = ['movement:SC109_W_SC108_to_E', 'storage:SC108_to_SC109', 'movement:SC108_W_SC107_to_E_SC109',
            'storage:SC1001_W_out']
    edges = [('movement:SC108_W_SC107_to_E_SC109', 'storage:SC108_to_SC109')]
    off = _series(tmp_path / 'off', keys, [[1, 1, 1, 1], [2, 2, 2, 2], [3, 3, 3, 3]], edges)
    on = _series(tmp_path / 'on', keys, [[1, 1, 1, 1], [5, 2, 2, 2], [6, 4, 7, 3]], edges)
    r = kg.judge_dynamic(off, on)
    assert r['verdict'] == 'PASS' and r['classes'] == {'C0': 2, 'C1': 1, 'C3': 0}
    on2 = _series(tmp_path / 'on2', keys, [[1, 1, 1, 9], [5, 2, 2, 2], [6, 4, 7, 3]], edges)
    r2 = kg.judge_dynamic(off, on2)
    assert r2['verdict'] == 'STOP' and r2['c3_before_c0'] and r2['sc1001_sa_fw_c3_keys']


def test_f_judge():
    off = {T: {'M1_450': (10.0, 8.0), 'M2_450': (5.0, 7.0), 'M3_450': (3.0, 3.0)} for T in range(22)}
    b1 = {T: {'M1_450': (9.0, 8.0), 'M2_450': (6.0, 7.0), 'M3_450': (4.0, 3.0)} for T in range(22)}
    r = kg.f_judge(off, b1, boot_n=200)
    assert r['F-1'] and r['F-2'] and r['F-3'] and r['n'] == 22
    assert not math.isnan(r['boot_mae_diff_90'][0])


def test_k92_vissim_ref_network_identity(tmp_path, monkeypatch):
    """Amendment 25 section 1: randSeed-only normalization; anything else is a SystemExit."""
    assert vr.INPX_SHA256 == '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
    assert vr.INPX_NORM_SHA256 == 'b7f05dcd07042fce8a439529853429a642f4de7b998c96ede51ce8c2d1230eb3'
    base = (b'<?xml version="1.0"?>\r\n<network>\r\n<simulation numRuns="1" randSeed="%s" randSeedIncr="1" '
            b'simRes="10"/>\r\n<links/>\r\n</network>\r\n')

    def put(name, data):
        p = tmp_path / name
        p.write_bytes(data)
        return p
    norm = hashlib.sha256(base % b'').hexdigest()
    monkeypatch.setattr(vr, 'INPX_NORM_SHA256', norm)
    ok = vr.network_identity(put('s43.inpx', base % b'43'), 43)
    assert ok['normalized_sha256'] == norm and ok['randSeed'] == 43
    assert ok['raw_sha256'] == hashlib.sha256(base % b'43').hexdigest()
    assert ok['rule'] == 'k92-inpx-randseed-normalized/v1'
    assert vr.network_identity(put('s31.inpx', base % b'31'), 31)['normalized_sha256'] == norm
    one = base % b'43'
    bad = {'value_not_seed': (base % b'44', 43), 'leading_zero': (base % b'043', 43), 'folder_seed': (one, 41),
           'other_byte': (one.replace(b'<links/>', b'<linkz/>'), 43),
           'no_attr': (one.replace(b' randSeed="43"', b''), 43),
           'two_attr': (one.replace(b'<links/>', b'<links randSeed="43"/>'), 43),
           'other_element': (one.replace(b'<simulation ', b'<simulationX '), 43),
           'line_endings': (one.replace(b'\r\n', b'\n'), 43)}
    for name, (data, seed) in bad.items():
        with pytest.raises(SystemExit):
            vr.network_identity(put(name + '.inpx', data), seed)
