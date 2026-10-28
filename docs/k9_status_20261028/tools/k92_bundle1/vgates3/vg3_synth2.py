"""VerifyGates 2 — synthetic end-to-end runs of every module's main() on a fake tree (vgates3/dev/fake), module
constants patched to it.  No k92t / V4 / sealed / NC file is read.  Exit 0 only when every module runs and gives the
expected verdicts."""
import importlib
import json
import math
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vg3lib as V  # noqa: E402

F = HERE / 'dev' / 'fake'
RES = []


def check(name, got, want):
    ok = got == want
    RES.append(ok)
    print('%s %s got=%s want=%s' % ('OK ' if ok else 'BAD', name, got, want))


def wj(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding='utf-8')


def lab(seed, T):
    return 'TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed)


def build():
    import numpy as np
    if F.exists():
        shutil.rmtree(F)
    ok2, outk, nc3 = F / 'OK2', F / 'OK2' / 'k92t', F / 'NC3'
    # F arms
    states = [(47, T) for T in V.F_PRIMARY] + [(31, T) for T in V.F_SECOND[31]] + [(43, T) for T in V.F_SECOND[43]]
    vref = {'schema': 'k92-vissim-ref/v1', 'seeds': {}}
    for s in (47, 31, 43):
        vref['seeds']['s%d' % s] = {'states': {}, 'network_identity': {'raw_sha256': None, 'normalized_sha256': None},
                                    'fzp': {'sha256': None}}
    fzp_rows = {47: [], 31: [], 43: []}

    def cnt(s, k):
        return (k + s) % 7 + 3                                       # vehicles on link 173 at frame k
    frames = {47: set(), 31: set(), 43: set()}
    for s, T in states:
        st = {}
        for d in (150, 450):
            k = (T + d) // 5
            n = cnt(s, k)
            st['m1_T%d' % d] = n
            st['m1_by_link_T%d' % d] = {str(x): (n if x == 173 else 0) for x in V.CHAIN_LINKS}
            st['m2_T%d' % d] = 10 + d // 150
            st['m3_T%d' % d] = 2 + d // 150
            frames[s].add(k)
        vref['seeds']['s%d' % s]['states'][str(T)] = st
    pers = {'schema': 'k92-vissim-ref/v1', 'seeds': {'s47': {'states': {}, 'network_identity': {}}}}
    for T in V.F_PRIMARY:
        if T - 450 >= 900:
            pers['seeds']['s47']['states'][str(T - 450)] = {'m1_T450': cnt(47, T // 5)}
            frames[47].add(T // 5)
    for s in (47, 31, 43):
        for k in sorted(frames[s]):
            fzp_rows[s] += [(5.0 * k + 0.1, 173)] * cnt(s, k)
    for s in (47, 31, 43):
        # fake inpx with randSeed
        b = ('<x><simulation a="1" randSeed="%d" b="2"/></x>' % s).encode()
        p = nc3 / ('s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (s, s))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        V.INPX_RAW[s] = V.sha_bytes(b)
        V.INPX_NORM = V.sha_bytes(b'<x><simulation a="1" randSeed="" b="2"/></x>')
        vref['seeds']['s%d' % s]['network_identity'] = {'raw_sha256': V.sha_bytes(b), 'normalized_sha256': V.INPX_NORM}
        if s == 47:
            pers['seeds']['s47']['network_identity'] = {'raw_sha256': V.sha_bytes(b)}
        lines = [b'$VISION\n', b'* x\n', b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX\n']
        for i, (t, lk) in enumerate(sorted(fzp_rows[s])):
            lines.append(('%.2f;%d;%d;1\n' % (t, i, lk)).encode())
        lines.append(b'1000.10;99;999;1\n')
        fz = nc3 / ('s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (s, s))
        fz.parent.mkdir(parents=True, exist_ok=True)
        fz.write_bytes(b''.join(lines))
        vref['seeds']['s%d' % s]['fzp'] = {'sha256': V.sha_file(fz)}
    wj(outk / 'f_vref' / 'sa' / 'k92_vissim_ref.json', vref)
    wj(outk / 'f_persist30' / 'sa' / 'k92_vissim_ref.json', pers)
    bias = {'OFF': 5.0, 'W': 3.0, 'B1': 1.0}
    for arm, root in (('OFF', 'f_off'), ('W', 'f_w'), ('B1', 'f_b1')):
        for s, T in states:
            d = outk / root / 'sa' / 'jobs' / 'k92t' / lab(s, T)
            vs = vref['seeds']['s%d' % s]['states'][str(T)]
            c3 = [1.0, 2.0, vs['m1_T450'] + bias[arm] - 3.0]
            c1 = [0.5, 0.5, vs['m1_T150'] + bias[arm] - 1.0]
            dep_w = [(vs['m2_T450'] + bias[arm]) / 3.0] * 3
            dep_l = [(vs['m3_T450'] + bias[arm] * 0.1) / 3.0] * 3
            blocks = []
            for k in range(3):
                ch = c1 if k == 0 else c3
                blocks.append({'k': k + 1, 'chain': dict(zip(V.CHAIN_KEYS, ch)), 'chain_sum': math.fsum(ch),
                               'departures': {V.W_KEY: dep_w[k], V.L_KEY: dep_l[k]}})
            hz = {'m1_chain_T150': math.fsum(c1), 'm1_chain_T450': math.fsum(c3), 'm2_w_dep_T150': dep_w[0],
                  'm2_w_dep_T450': math.fsum(dep_w), 'm3_l_dep_T150': dep_l[0], 'm3_l_dep_T450': math.fsum(dep_l)}
            wj(d / 'k92_record.json', {'horizon': hz, 'blocks': blocks, 'errors': [], 'seed': s})
            wj(d / 'summary.json', {'ok': True})
            keys = sorted(V.CHAIN_KEYS + ('storage:other',))
            model = np.full((3, len(keys)), np.nan)
            for i, (te, ch) in enumerate(((T + 150.0, c1), (T + 300.0, c3), (T + 450.0, c3))):
                for kk, v in zip(V.CHAIN_KEYS, ch):
                    model[i, keys.index(kk)] = v
            np.savez_compressed(d / 'k92_series.npz', keys=np.array(keys, dtype=object),
                                t_end=np.array([T + 150.0, T + 300.0, T + 450.0]), model=model,
                                stage=np.zeros(3, dtype=np.int16), edges=np.array([['a', 'b']], dtype=object),
                                stage_names=np.array(['urban'], dtype=object))
            tag = '%06d' % T + ('' if s == 31 else '_s%d' % s)
            wj(outk / root / 'sa' / 'cap' / 'k92t' / 'TL3' / tag / 'SAF' / 'capture.json', {'ok': True})
    # steps
    names = (['prep_%s_s%d' % (a, s) for a in ('f_off', 'f_w', 'f_b1') for s in (31, 43, 47)] + ['arms_ja_f', 'arms_f_b1']
             + ['f_%s_%s' % (a, x) for a in ('f_off', 'f_w', 'f_b1') for x in ('cap_s47', 'cap_s31', 'cap_s43', 'jobs')]
             + ['f_vref'])
    rows = [{'name': n, 'rc': 0, 'vissim_pre': 0, 'vissim_post': 0} for n in names]
    rows.append({'name': 'f_persist', 'rc': 1, 'vissim_pre': 0, 'vissim_post': 0})
    while len(rows) < 59:
        rows.append({'name': 'j_other_%d' % len(rows), 'rc': 0, 'vissim_pre': 0, 'vissim_post': 0})
    rows += [{'name': 'judge_fcount', 'rc': 0}, {'name': 'f_persist30', 'rc': 0}, {'name': 'judge_f', 'rc': 0},
             {'name': 'jb_unit', 'rc': 1}, {'name': 'post_sealedscan', 'rc': 3}]
    (outk / 'steps.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    return ok2, outk, nc3


def main():
    ok2, outk, nc3 = build()
    V.OK2, V.OUTK, V.NC3 = ok2, outk, nc3
    V.OUTV = F / 'out'
    V.LOG_MD = F / 'LOG.md'
    wj(outk / 'judge' / 'f.json', {'verdict': 'X'})
    wj(outk / 'judge' / 'jb.json', {'verdict': 'X'})
    wj(outk / 'judge' / 'f_jobs.json', {'verdict': 'X'})
    V.LOG_MD.write_text('x %s y %s\n' % (V.sha_file(outk / 'judge' / 'f.json'), V.sha_file(outk / 'judge' / 'jb.json')),
                        encoding='utf-8')
    vf = importlib.import_module('vg3_f')
    vf.ARMS = {'OFF': outk / 'f_off', 'W': outk / 'f_w', 'B1': outk / 'f_b1'}
    vf.main()
    r = json.loads((V.OUTV / 'f.json').read_text(encoding='utf-8'))
    check('F verdict', r['verdict'], 'PASS')
    check('F F1 F2 F3 n', [r['f_judge'][k] for k in ('F-1', 'F-2', 'F-3', 'n')], [True, True, True, 22])
    check('F mae OFF M1', round(r['table']['OFF']['M1_450']['mae'], 9), 5.0)
    check('F mae B1 M1', round(r['table']['B1']['M1_450']['mae'], 9), 1.0)
    check('F fcount', r['fcount_verdict'], 'PASS')
    check('F model crosscheck', [r['model_crosscheck'][a]['all_bit_equal'] for a in ('OFF', 'W', 'B1')], [True] * 3)
    check('F fzp m1', [r['fzp_m1'][s]['m1_equal'] for s in ('s47', 's31', 's43')], [44, 16, 16])
    check('F fzp sha', [r['fzp_m1'][s]['fzp_sha_equals_vref'] for s in ('s47', 's31', 's43')], [True] * 3)
    check('F fzp persist', r['fzp_m1']['s47']['persist_equal'], 21)
    check('F persist', [r['persistence']['n'], r['persistence']['complete'],
                        r['persistence']['overlap_with_f_vref']], [21, True, {'n': 15, 'n_equal': 15}])
    check('F steps', [r['steps']['f_steps_rc0_vissim0'], r['steps']['f_persist_rc1'], r['steps']['a30_steps_rc0'],
                      r['steps']['names_declared']], [True] * 4)
    check('F identity', all(r['network_identity']['s%d' % s]['recomputed_raw_ok'] for s in (47, 31, 43)), True)
    check('F variant', r['variant_F1_with_fzp_m1'], True)
    check('F agree (fake recorded)', r['agree_all'], False)
    # recorded = mine -> agreement true
    rec = {'verdict': r['verdict'], 'f_judge': r['f_judge'], 'table': r['table'], 'report_T150': r['report_T150'],
           'report_W_vs_OFF': r['report_W_vs_OFF'], 'job_counts': r['job_counts'], 'n_primary': r['n_primary'],
           'missing': r['missing'], 'network_identity_ok': {'47': True, '31': True, '43': True},
           'persist_identity_ok': True, 'report_second_sample': r['second_sample'],
           'report_persistence_M1_450': dict(r['persistence'], label_ko='x')}
    wj(outk / 'judge' / 'f.json', rec)
    wj(outk / 'judge' / 'f_jobs.json', {'verdict': 'PASS', 'job_counts': r['job_counts']})
    V.LOG_MD.write_text('x %s y %s\n' % (V.sha_file(outk / 'judge' / 'f.json'), V.sha_file(outk / 'judge' / 'jb.json')),
                        encoding='utf-8')
    vf.main()
    r2 = json.loads((V.OUTV / 'f.json').read_text(encoding='utf-8'))
    check('F agree (recorded = mine)', [r2['agree_all'], [k for k, v in r2['agreement'].items() if not v]], [True, []])
    # J / F not fixed -> refusal
    V.LOG_MD.write_text('nothing\n', encoding='utf-8')
    try:
        vf.main()
        check('F refuses without LOG sha', False, True)
    except SystemExit:
        check('F refuses without LOG sha', True, True)
    # post: fake sealed root
    sealed = ok2 / 'sealed_s47'
    V.SEALED, V.OUT30 = sealed, ok2 / 'a30'
    for c in ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3'):
        inv = {}
        for seed, sub in ((31, 'TL3_1500_SAF_OBS_H3'), (43, 'TL3_1050_s43_SAF_OBS_H3'), (47, 'TL3_3450_s47_SAF_OBS_H3')):
            p = sealed / c / 'plant' / 'new' / 'sa' / 'jobs' / 'x' / sub / 'k92_record.json'
            doc = {'seed': seed, 'vissim': None if seed == 47 else {'m': 1},
                   'vissim_reason': 'k92_blind_s47' if seed == 47 else 'k92_vissim_ref'}
            wj(p, doc)
            rel = p.relative_to(sealed / c).as_posix()
            inv[rel] = [p.stat().st_size, V.sha_file(p)]
        wj(ok2 / 'commit' / c / 'sealed_s47_index.json', {'inventory': inv})
    (sealed / 'a27' / 'logs').mkdir(parents=True)
    (sealed / 'a27' / 'logs' / 'r.txt').write_text('x', encoding='utf-8')
    wj(ok2 / 'a27' / 'sealed_index.json', {'runs': [{'stdout_file': 'r.txt', 'size': 1}]})
    files = []
    for n in ('f_f_off_jobs.log', 'f_f_w_jobs.log', 'f_f_b1_jobs.log'):
        p = sealed / 'k92t' / 'logs' / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('log', encoding='utf-8')
        files.append({'to': str(p), 'from': str(outk / 'logs' / n), 'size': 3, 'sha256': V.sha_file(p)})
    wj(V.OUT30 / 'sealed_k92t_index.json', {'n': 3, 'files': files,
                                            'amendment30_sha256': 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a'})
    wj(outk / 'judge' / 'sealed_records.json', {'ok': False, 'sealed_records': {'files': 12, 's47': 12, 'bad': 8},
                                                'n_bad': 8})
    for k in ('STOP_f.json', 'k92_judging_stage.json', 'start/scans.json', 'stages/start.json'):
        wj(outk / k, {})
    V.LOG_MD.write_text('x %s y %s\n' % (V.sha_file(outk / 'judge' / 'f.json'), V.sha_file(outk / 'judge' / 'jb.json')),
                        encoding='utf-8')
    vp = importlib.import_module('vg3_post')
    vp.main()
    r = json.loads((V.OUTV / 'post.json').read_text(encoding='utf-8'))
    rs = r['record_scan']
    check('POST counts', [rs['files'], rs['s47_declared'], rs['bad_declared'], rs['s47_literal'], rs['bad_literal']],
          [12, 4, 0, 12, 8])
    check('POST literal reproduces', r['literal_rule_reproduces_recorded'], True)
    check('POST sealed index', r['sealed_index']['ok'], True)
    # gk4 (fake rows)
    vg = importlib.import_module('vg3_gk4')
    rows, rj = [], {}
    for i, (name, old, new, roots) in enumerate(vg.ROWS):
        o, n = F / 'gk4' / name / 'old', F / 'gk4' / name / 'new'
        doc = {'x': 1.0, 'p': str(roots[0]) + '/a', 'sha256': 'aa'}
        wj(o / 'summary.json', doc)
        wj(n / 'summary.json', dict(doc, p=str(roots[3]) + '/a', sha256='bb'))
        wj(o / 'k92_record.json', {'h': 1.0})
        wj(n / 'k92_record.json', {'h': 1.0 if i < 3 else 1.0 + 1e-12})
        rows.append((name, o, n, roots))
        rj[name] = {'verdict': 'PASS', 'parts': {'summary.json': {'verdict': 'PASS'}, 'k92_record.json': {'verdict': 'PASS'}}}
    vg.ROWS = rows
    wj(ok2 / 'a27' / 'judge' / 'rjg4.json', {'rows': rj})
    with open(V.LOG_MD, 'a', encoding='utf-8') as f:
        f.write('- [t] k92t30 구동기: J·F 판정 값 고정 확인(f.json ...\n')
    vg.main()
    r = json.loads((V.OUTV / 'gk4_plant.json').read_text(encoding='utf-8'))
    check('GK4 verdicts', r['rows']['plant_K9-2-2_TL3_1050_s43_SAF_OBS_H3']['verdict'], 'EXPLAIN')
    check('GK4 others', sorted(v['verdict'] for k, v in r['rows'].items() if 'K9-2-2_TL3_1050' not in k), ['PASS'] * 3)
    check('GK4 agree', r['agree_all'], False)
    # jb (fake gates files)
    vj = importlib.import_module('vg3_jb')
    old = {'gates': {g: {'verdict': 'PASS', 'items': {'a': {'value': [1, 2.5], 'pass_': True},
                                                      'b': {'value': 1, 'pass_': None}}} for g in vj.GATES}}
    new = json.loads(json.dumps(old))
    new['gates']['G-EB-3']['items']['a']['value'] = [1, 2.5000001]
    vj.OLD, vj.NEW, vj.OLD_SHA = F / 'gk91.json', F / 'jb' / 'gk92.json', None
    wj(vj.OLD, old)
    wj(vj.NEW, new)
    vj.OLD_SHA = V.sha_file(vj.OLD)
    vj.JB = F / 'jb'
    wj(outk / 'judge' / 'jb.json', {'verdict': 'DIFF'})
    vj.main()
    r = json.loads((V.OUTV / 'jb.json').read_text(encoding='utf-8'))
    check('JB verdict', [r['verdict'], r['n_judged'], r['differing']], ['DIFF', 9, ['G-EB-3/a']])
    # jwall
    for i, labx in enumerate(['TL3_%d_SAF_OBS_H3' % T for T in V.GRID9] + ['TL3_900_s43_SAF_OBS_H3',
                                                                          'TL3_900_s47_SAF_OBS_H3']):
        for side, w in (('ja', 100.0), ('jb', 100.0 + i * 0.1)):
            d = outk / side / 'sa' / 'jobs' / 'k92t' / labx
            wj(d / 'summary.json', {'ok': True, 'wall_sec': w})
            wj(d / 'vissim_counts.json', {'vissim_count_pre': 0, 'vissim_count_post': 0,
                                          'start': 1.0 if side == 'ja' else 3.0, 'end': 2.0 if side == 'ja' else 4.0})
    wj(outk / 'judge' / 'jwall.json', {'verdict': 'PASS', 'median': 1.05, 'n_clean': 11, 'limit': V.WALL_LIMIT})
    vw = importlib.import_module('vg3_jwall')
    vw.main()
    r = json.loads((V.OUTV / 'jwall.json').read_text(encoding='utf-8'))
    check('JWALL median', [r['verdict'], r['median'], r['n_clean']], ['PASS', 1.005, 11])
    # J-0 (fake captures, synthetic template pickles)
    import pickle
    import types
    mod = types.ModuleType('fakeproj.cfg')
    sys.modules['fakeproj'] = types.ModuleType('fakeproj')
    sys.modules['fakeproj.cfg'] = mod

    class Obj(object):
        pass
    Obj.__module__ = 'fakeproj.cfg'
    Obj.__qualname__ = 'Obj'
    mod.Obj = Obj

    def tpl(w, l_):
        net = Obj()
        net.movement_capacity_by_movement_veh_h = {V.W_KEY: w, V.L_KEY: l_, 'X': 7.0}
        cfg = Obj()
        cfg.network = net
        o = Obj()
        o.cfg = cfg
        return pickle.dumps({'owned': [o]})
    t_off, t_on = tpl(619.59, 1045.1612903225805), tpl(5209.8, 1045.1612903225805)
    t_off_low, t_on_low = tpl(619.59, 413.06), tpl(5209.8, 1045.1612903225805)
    j0rows = {}
    vj0 = importlib.import_module('vg3_j0')
    states = ([('TL3', T, s) for s in (31, 43, 47) for T in V.GRID9] + [('DP', T, None) for T in V.DP_T]
              + [('ROBS61', T, 31) for T in V.ROBS61_T])
    tb = ('Traceback (most recent call last):\n  File "D:\\T\\evaluation\\controllers\\a.py", line 5, in run\n'
          '    x()\nValueError: Previous command\n')
    for h, T, s in states:
        key = '%s_%d%s' % (h, T, '' if s in (None, 31) else '_s%d' % s)
        for side in ('ja', 'jb'):
            d = vj0.cdir(outk / side, h, T, s)
            d.mkdir(parents=True, exist_ok=True)
            if h == 'ROBS61' and T in (1, 150):
                wj(d / 'capture_failed.json', {'ok': False, 'error': tb})
                continue
            md = {k: {'v': 1} for k in V.META7}
            md['stopline_approach_install_check'] = {'passed': True}
            md['stopline_approach_initial'] = {'posthead_veh': 1.0}
            if side == 'jb':
                md['k92_w'] = {'x': 1}
            wj(d / 'capture.json', {'ok': True, 'metadata': md, 'probes': {'sa': {}, 'ports': {}, 'records': {},
                                                                           'provenance': {'127': {}},
                                                                           'occupancy': {'SC1001_W_out': 1}}})
            low = (h == 'TL3' and s == 43 and T == 900)
            (d / 'template.pickle').write_bytes((t_off_low if low else t_off) if side == 'ja' else
                                                (t_on_low if low else t_on))
        j0rows[key] = {'verdict': 'PASS'}
    wj(outk / 'judge' / 'j0.json', {'verdict': 'PASS', 'rows': j0rows, 'robs61_init_61': {'count': 61}})
    vj0.main()
    r = json.loads((V.OUTV / 'j0.json').read_text(encoding='utf-8'))
    check('J0', [r['verdict'], r['n_states'], r['robs61_init_61'], r['seed_bound_states'], r['agree_all']],
          ['PASS', 105, {'initialized': 59, 'identical_failure': 2, 'count': 61}, ['TL3_900_s43'], True])
    del sys.modules['fakeproj.cfg'], sys.modules['fakeproj']
    # J-a (fake V4 / ja; decisions on synthetic folders; real k91t / k92t trees for RS / CAO / R-CR)
    vja = importlib.import_module('vg3_ja')
    V.V4 = F / 'V4'
    jarows = {}
    for labx in vja.JOBS:
        wj(V.V4 / 'sa' / 'jobs' / 'k91t' / labx / 'summary.json', {'ok': True, 'a': 1.0, 'wall_sec': 1.0, 'p': 'x'})
        wj(outk / 'ja' / 'sa' / 'jobs' / 'k92t' / labx / 'summary.json',
           {'ok': True, 'a': 1.0 if labx != vja.JOBS[3] else 1.5, 'wall_sec': 2.0, 'p': 'y'})
        jarows[labx] = {'verdict': 'SAME' if labx != vja.JOBS[3] else 'DIFF'}
    for name in vja.FULL:
        for side, root in (('old', V.V4 / 'sa' / 'full' / 'k91t' / name), ('new', outk / 'ja' / 'sa' / 'full' / 'k92t' / name)):
            root.mkdir(parents=True, exist_ok=True)
            (root / 'action_002700.json').write_text(json.dumps({'green_times': {}, 'metadata': {'a': 1}}),
                                                     encoding='utf-8')
            (root / 'action_002700.csv').write_bytes(b'a\n')
        jarows[name] = {'verdict': 'PASS', 'hard_verdict': 'SAME', 'unclassified_n': 0}
    wj(outk / 'judge' / 'ja.json', {'verdict': 'FAIL', 'n_items': 23, 'rows': jarows})
    vja.main()
    r = json.loads((V.OUTV / 'ja.json').read_text(encoding='utf-8'))
    check('JA', [r['verdict'], r['n_items'], r['not_same'], r['cr']['k91t'], r['cr']['k92t'], r['cr']['ok'],
                 r['agree_all']], ['FAIL', 23, [vja.JOBS[3]], 'AAAAAA---X', 'AAAAAAAAAA', True, True])
    bad = RES.count(False)
    print('VG3_SYNTH2 cases=%d bad=%d' % (len(RES), bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
