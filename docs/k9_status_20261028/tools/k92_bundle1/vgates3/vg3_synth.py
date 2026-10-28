"""VerifyGates 2 — synthetic checks of vg3lib before pinning (no k92t / V4 output is read; the only real file read is
the k91t tree runtime_setup.py bytes for the A_K92 known-old-value case).  Writes its cases under vgates3/dev/synth.
Prints one line per case and a summary; exit 0 only when every case gives the expected result."""
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vg3lib as V  # noqa: E402

D = HERE / 'dev' / 'synth'
RES = []


def check(name, got, want):
    ok = got == want
    RES.append(ok)
    print('%s %s got=%s want=%s' % ('OK ' if ok else 'BAD', name, got, want))


def base_doc():
    return {'N_P_star': {'a': 1.0}, 'green_times': {'SC1': [30.0, 40.0]}, 'offsets': {}, 'vsl': {}, 'ramp_metering': {},
            'N_UF_star': {}, 'inflow_outflow_allocation': {},
            'prediction': {'wall_sec': 1.5, 'x': 2.0}, 'prediction_error': {'e': 0.1},
            'metadata': {'decision_wall_sec': 3.0, 'sdmpc_active': True, 'head_x': 1.0,
                         'joint_leader_selection': {'selected_objective': 10.0, 'held_objective': 11.0,
                                                    'warm_start_objective': 12.0, 'selection_status': 'ok',
                                                    'converged': True, 'feasible': True,
                                                    'tangent_derivatives': [{'transformed_source_sha256': {}}]},
                         'foo': 1, 'timing': {'wall_sec': 1.0, 'started_at': '2026-10-20T10:00:00'},
                         'final_check_reserve': {'seconds': 5.0},
                         'run_provenance': {'inputs': {'tuning_json': {'path': '', 'sha256': ''}}},
                         'paths': {'tree': 'D:\\VISSIM-merge\\k8_gate_trees\\k91t\\evaluation\\controllers\\a.py'}}}


def write_case(name, old, new, csv_old=b'a,b\n1,2\n', csv_new=b'a,b\n1,2\n', prog_old=None, prog_new=None,
               new_rs=b'new rs bytes\n', new_cao=b'new cao\n'):
    root = D / name
    if root.exists():
        shutil.rmtree(root)
    for side, doc, csv, prog in (('old', old, csv_old, prog_old), ('new', new, csv_new, prog_new)):
        d = root / side
        d.mkdir(parents=True)
        if doc is not None:
            (d / 'action_002700.json').write_text(json.dumps(doc), encoding='utf-8')
        if csv is not None:
            (d / 'action_002700.csv').write_bytes(csv)
        if prog is not None:
            (d / 'action_002700.joint.progress.jsonl').write_text('\n'.join(json.dumps(r) for r in prog) + '\n',
                                                                  encoding='utf-8')
    nr = root / 'newroot' / 'evaluation' / 'controllers'
    nr.mkdir(parents=True)
    (nr / 'runtime_setup.py').write_bytes(new_rs)
    (nr / 'control_area_objective.py').write_bytes(new_cao)
    return root


def run_case(name, old, new, want, **kw):
    root = write_case(name, old, new, **kw)
    r = V.decision_compare(root / 'old', root / 'new', 2700, root / 'newroot', V.K91T_TREE)
    check('dec ' + name, r['verdict'], want)
    return r


def main():
    if D.exists():
        shutil.rmtree(D)
    D.mkdir(parents=True)
    b = base_doc()
    j = json.dumps(b)
    run_case('S01_same', json.loads(j), json.loads(j), 'PASS')
    n = json.loads(j)
    n['green_times']['SC1'][0] = 31.0
    run_case('S02_hard_h2', json.loads(j), n, 'FAIL')
    n = json.loads(j)
    n['metadata']['foo'] = 2
    run_case('S03_unclassified', json.loads(j), n, 'HOLD')
    rs_old = V.sha_file(V.K91T_TREE / 'evaluation/controllers/runtime_setup.py')
    key = 'D:\\VISSIM-merge\\k8_gate_trees\\k91t\\evaluation\\controllers\\runtime_setup.py'
    o, n = json.loads(j), json.loads(j)
    o['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][key] = rs_old
    n['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][
        'D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\a27\\k92t\\evaluation\\controllers\\runtime_setup.py'] = \
        V.sha_bytes(b'new rs bytes\n')
    r = run_case('S04_a_k92_ok', o, n, 'PASS')
    check('S04 a_k92 allowed', r['allowed'].get('A_K92'), 1)
    n2 = json.loads(json.dumps(n))
    o2 = json.loads(json.dumps(o))
    o2['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][key] = 'ab' * 32
    run_case('S05_a_k92_old_not_root', o2, n2, 'HOLD')
    n3 = json.loads(json.dumps(n))
    n3['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][
        'D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\a27\\k92t\\evaluation\\controllers\\runtime_setup.py'] = 'cd' * 32
    run_case('S05b_a_k92_new_not_root', json.loads(json.dumps(o)), n3, 'HOLD')
    o, n = json.loads(j), json.loads(j)
    ck = 'D:\\VISSIM-merge\\k8_gate_trees\\k91t\\evaluation\\controllers\\control_area_objective.py'
    nk = 'D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\a27\\k92t\\evaluation\\controllers\\control_area_objective.py'
    o['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][ck] = 'ef' * 32
    n['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][nk] = \
        V.sha_bytes(b'new cao\n')
    run_case('S06_cao_ok', o, n, 'PASS')
    n['metadata']['joint_leader_selection']['tangent_derivatives'][0]['transformed_source_sha256'][nk] = '12' * 32
    run_case('S06b_cao_bad', o, n, 'HOLD')
    o, n = json.loads(j), json.loads(j)
    n['metadata']['timing']['wall_sec'] = 9.0
    n['metadata']['timing']['started_at'] = '2026-10-21T11:00:00'
    run_case('S07_f3', o, n, 'PASS')
    n = json.loads(j)
    n['metadata']['final_check_reserve']['seconds'] = 6.0
    run_case('S07b_reserve_seconds', json.loads(j), n, 'HOLD')
    o, n = json.loads(j), json.loads(j)
    o['metadata']['run_id_hex'] = 'aa' * 16
    n['metadata']['run_id_hex'] = 'bb' * 16
    run_case('S08_f1', o, n, 'PASS')
    o['metadata']['evidence_sha256'] = 'aa' * 32
    n['metadata']['evidence_sha256'] = 'bb' * 32
    run_case('S08b_d2_overrides_f1', o, n, 'HOLD')
    o, n = json.loads(j), json.loads(j)
    o['metadata']['paths']['tree'] = 'D:\\VISSIM-merge\\k8_gate_trees\\k91t\\evaluation\\x.py'
    n['metadata']['paths']['tree'] = 'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t/evaluation/x.py'
    run_case('S09_root_norm', o, n, 'PASS')
    n['metadata']['paths']['tree'] = 'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t/evaluation/y.py'
    run_case('S09b_root_norm_tail', o, n, 'HOLD')
    o = json.loads(j)
    o['metadata']['D:\\VISSIM-merge\\k8_gate_trees\\k91t\\a'] = 1
    o['metadata']['D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t/a'] = 1
    run_case('S10_collision', o, json.loads(j), 'INCOMPLETE')
    run_case('S11_missing_csv', json.loads(j), json.loads(j), 'INCOMPLETE', csv_new=None)
    run_case('S12_csv', json.loads(j), json.loads(j), 'FAIL', csv_new=b'a,b\n1,3\n')
    p1 = [{'stage': 'x', 'objective': 1.0, 'held_objective': 2.0, 'seconds': 1.0}]
    p2 = [{'stage': 'x', 'objective': 1.5, 'held_objective': 2.0, 'seconds': 1.0}]
    run_case('S13_progress', json.loads(j), json.loads(j), 'FAIL', prog_old=p1, prog_new=p2)
    p3 = [{'stage': 'x', 'objective': 1.0, 'held_objective': 2.0, 'seconds': 9.0}]
    run_case('S13b_progress_timing', json.loads(j), json.loads(j), 'PASS', prog_old=p1, prog_new=p3)
    n = json.loads(j)
    n['metadata']['decision_wall_sec'] = 7.0
    n['prediction']['wall_sec'] = 9.0
    run_case('S14_v', json.loads(j), n, 'PASS')
    tun = D / 'tuning.json'
    tun.write_bytes(b'{"x": 1}\n')
    o, n = json.loads(j), json.loads(j)
    o['metadata']['run_provenance']['inputs']['tuning_json'] = {'path': 'C:/old/tuning.json', 'sha256': 'aa' * 32}
    n['metadata']['run_provenance']['inputs']['tuning_json'] = {'path': str(tun), 'sha256': V.sha_file(tun)}
    run_case('S15_r3_03', o, n, 'PASS')
    n['metadata']['run_provenance']['inputs']['tuning_json']['sha256'] = 'cc' * 32
    run_case('S15b_r3_03_bad', o, n, 'HOLD')
    n = json.loads(j)
    n['metadata']['k92_w'] = {'evidence_sha256': 'aa' * 32}
    run_case('S16_k92m_keyoff', json.loads(j), n, 'HOLD')
    n = json.loads(j)
    n['metadata']['foo'] = 1.0
    run_case('S17_type', json.loads(j), n, 'HOLD')
    n = json.loads(j)
    n['green_times']['SC1'] = [30, 40.0]
    run_case('S17b_type_hard', json.loads(j), n, 'FAIL')
    n = json.loads(j)
    n['metadata']['lst'] = [1, 2]
    o = json.loads(j)
    o['metadata']['lst'] = [1]
    run_case('S18_list_len', o, n, 'HOLD')
    n = json.loads(j)
    n['metadata']['head_new'] = 2.0
    run_case('S19_h5_one_side', json.loads(j), n, 'FAIL')
    # N table (amendment 29 section 2.5)
    base = 'D:/VISSIM-merge/k8_gate_trees/'
    table = [
        ('D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\k921_t74_W\\evaluation\\controllers\\runtime_setup.py',
         '<root>/evaluation/controllers/runtime_setup.py'),
        (base + 'k92b1/k921.build.json', 'd:/vissim-merge/k8_gate_trees/k92b1/k921.build.json'),
        (base + 'k92b1/k921_t74_W/k921.build.json', '<root>/k921.build.json'),
        (base + 'k92b1/a25/k92b1_probe.build.json', 'd:/vissim-merge/k8_gate_trees/k92b1/a25/k92b1_probe.build.json'),
        (base + 'k92attrib/a25', 'd:/vissim-merge/k8_gate_trees/k92attrib/a25'),
        (base + 'k92attrib/a25/x.py', 'd:/vissim-merge/k8_gate_trees/k92attrib/a25/x.py'),
        (base + 'k92attrib/t74_X1H1/evaluation/x.py', '<root>/evaluation/x.py'),
        (base + 'k92b1/a27/k925/diagnostics/x.json', '<root>/diagnostics/x.json'),
        (base + 'k92b1', 'd:/vissim-merge/k8_gate_trees/k92b1'),
        (base + 'k92attrib', 'd:/vissim-merge/k8_gate_trees/k92attrib'),
        (base + 'k92b1/a27', 'd:/vissim-merge/k8_gate_trees/k92b1/a27'),
        (base + 'k92b1.x', 'd:/vissim-merge/k8_gate_trees/k92b1.x'),
        (base + 'k91t/evaluation/a.py', '<root>/evaluation/a.py'),
        (base + 'k92b1x/a.py', '<root>/a.py'),
        ('x ' + base + 'k92b1/a25/ref_t74_CWf;y', 'x d:/vissim-merge/k8_gate_trees/k92b1/a25/ref_t74_cwf;y'),
        ('D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824/evaluation/a.py', '<root>/evaluation/a.py'),
        ('D:\\VISSIM-merge\\sim3-n31-k8\\evaluation\\a.py', '<root>/evaluation/a.py'),
        ('D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31/x', '<run>/x'),
        ('sdmpc31_v3c3_nc_s43 run', '<name> run'),
        (base + 'k92b1/a25/ref_t74_CWf/evaluation/a.py', '<root>/evaluation/a.py'),
    ]
    for s, want in table:
        check('N ' + s[:60], V.n_str(s), want)
        low = s.lower().replace('\\', '/')
        if 'k92b1' in low or 'k92attrib' in low:
            check('Ncomp ' + s[:60], V.k92_root_by_components(low), V.N_RULES[2][0].sub('<root>', low))
    # G5
    a = {'x': 1, 'y': 2.5, 'wall_sec': 1.0, 'flag': True, 's': 'p', 'job_path': 'a', 'n': float('nan')}
    c = V.g5_compare(a, dict(a))
    check('G5 same', (c['numeric_differ'], c['numeric_one_sided']), (0, 0))
    c = V.g5_compare(a, dict(a, y=2.6))
    check('G5 num diff', c['numeric_differ'], 1)
    c = V.g5_compare(a, dict(a, wall_sec=9.0, job_path='b'))
    check('G5 timing/path excluded', (c['numeric_differ'], c['string_differ']), (0, 0))
    c = V.g5_compare(a, dict(a, z=1.0))
    check('G5 one sided', c['numeric_one_sided'], 1)
    c = V.g5_compare(a, dict(a, flag=False, x=1.0))
    check('G5 bool invisible, int=float', c['numeric_differ'], 0)
    c = V.g5_compare({'sha256': 'a', 'p': 'D:/A/b'}, {'sha256': 'b', 'p': 'D:/C/b'}, path_roots=['D:/A', 'D:/C'])
    check('G5 hash/path strings', (c['hash_strings_differ'], c['path_strings_differ'], c['string_differ']), (1, 1, 0))
    c = V.g5_compare({'v': 1.0}, {'v': 1.0 + 1e-12}, tol_rel=1e-9)
    check('G5 tol', (c['numeric_differ'], c['numeric_above_tol']), (1, 0))
    # tracebacks
    tb = ('Traceback (most recent call last):\n  File "D:\\T1\\evaluation\\controllers\\a.py", line 5, in run\n'
          '    x()\n  File "C:\\Python\\lib\\x.py", line 9, in y\n    z\nValueError: boom\n')
    s1 = V.tb_signature(tb)
    s2 = V.tb_signature(tb.replace('D:\\T1', 'D:\\T2'))
    check('TB same across roots', s1 == s2 and len(s1[1]) == 1, True)
    check('TB exc', s1[0], 'ValueError: boom')
    check('TB differ', V.tb_signature(tb.replace('boom', 'bang')) == s1, False)
    check('TB none', V.tb_signature('no traceback'), None)
    # stub unpickler on a synthetic pickle with a fake module class
    import pickle
    import types
    mod = types.ModuleType('fakeproj.cfg')
    sys.modules['fakeproj'] = types.ModuleType('fakeproj')
    sys.modules['fakeproj.cfg'] = mod

    class Net(object):
        pass
    Net.__module__ = 'fakeproj.cfg'
    Net.__qualname__ = 'Net'
    mod.Net = Net
    net = Net()
    net.movement_capacity_by_movement_veh_h = {'A': 1.5, 'B': 2}
    cfg = Net()
    cfg.network = net
    ow = Net()
    ow.cfg = cfg
    p = D / 'tpl.pickle'
    p.write_bytes(pickle.dumps({'owned': [ow]}))
    del sys.modules['fakeproj.cfg'], sys.modules['fakeproj']
    check('stub caps', V.template_caps(p), {'A': 1.5, 'B': 2.0})
    bad = RES.count(False)
    print('VG3_SYNTH cases=%d bad=%d' % (len(RES), bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
