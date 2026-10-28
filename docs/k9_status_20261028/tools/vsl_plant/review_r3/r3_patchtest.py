"""r3 patch test (PRE_VP_R3, D-K9-108 / D-K9-109).  Synthetic inputs in a PID-unique temp folder; the real shared LOCK,
the real STOP_VP, plant code and VISSIM are never touched.  Existing probe.json / tree records are only read.

    python -B r3_patchtest.py <out.json>

A  vp_jobcheck.py R1 objective tolerance (|replay - record| <= 1e-9 veh*h), r3 and r2 probe.json forms.
B  vp_queue.py STOP_VP re-check right after taking the LOCK (r3) against the r2 queue (gap shown), with the LOCK,
   job runner, disk check and priority call replaced in-process by recorders.
C  vp_treefields.py on the real record (read only) and on synthetic variants.
D  compile (no bytecode written) and text presence of the r3 lines in vp_probe.py."""
import importlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
VP = Path(__file__).resolve().parents[1]
TOOLS = VP / 'tools'
sys.path.insert(0, str(TOOLS))
import vp_common as C  # noqa: E402
import vp_jobcheck as JC  # noqa: E402
import vp_treefields as TF  # noqa: E402

RES = []
ULP2 = 1.1368683772161603e-13   # the S-R1 difference of 17:49 (P1_REPORT), used as a synthetic value here


def check(name, cond, detail=''):
    RES.append({'name': name, 'ok': bool(cond), 'detail': str(detail)[:300]})


def jobcheck_hits(tmp, name, checks, stop=None, mode='A'):
    jd = tmp / ('jc_%s' % name)
    jd.mkdir(parents=True, exist_ok=True)
    C.write_json(jd / 'probe.json', {'checks': checks, 'errors': [], 'stop': stop, 'spec': {'state': {'T': 1800}},
                                     'evaluations': {}})
    saved = sys.argv
    sys.argv = ['vp_jobcheck.py', str(jd), mode, str(jd / 'jobcheck.json')]
    try:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            rc = JC.main()
    finally:
        sys.argv = saved
    rec = C.read_json(jd / 'jobcheck.json') or {}
    return rc, [h for h in rec.get('hits', []) if h.startswith('S-R1')], rec


def part_a(tmp):
    base = {'R1_costs_within_1e-9': True, 'R1_costs_same_keys': True, 'R3_repack_bit_equal': True}
    ok_r3 = dict(base, **{'R1_objective_bit_equal': False, 'R1_objective_diff': ULP2, 'R1_objective_within_1e-9': True})
    rc, r1, rec = jobcheck_hits(tmp, 'r3_2ulp', ok_r3)
    check('A1_r3_probe_2ulp_no_S-R1', r1 == [] and rec.get('r1_objective_ok') is True, r1)
    bad = dict(base, **{'R1_objective_bit_equal': False, 'R1_objective_diff': 2e-9, 'R1_objective_within_1e-9': False})
    rc, r1, rec = jobcheck_hits(tmp, 'r3_2e-9', bad)
    check('A2_r3_probe_2e-9_S-R1', len(r1) == 1 and rc == 2, r1)
    costbad = dict(ok_r3, **{'R1_costs_within_1e-9': False})
    rc, r1, _ = jobcheck_hits(tmp, 'r3_costbad', costbad)
    check('A3_costs_over_tol_S-R1', len(r1) == 1 and rc == 2, r1)
    rc, r1, _ = jobcheck_hits(tmp, 'r3_stopfield', ok_r3, stop='S-R1: synthetic')
    check('A4_probe_stop_field_still_S-R1', len(r1) == 1 and rc == 2, r1)
    # r2-form probe.json (no R1_objective_within_1e-9): judged from R1_objective_diff
    f = JC.r1_objective_ok
    check('A5_r2_form_diff_2ulp_ok', f({'R1_objective_bit_equal': False, 'R1_objective_diff': ULP2}) is True)
    check('A6_r2_form_diff_0_ok', f({'R1_objective_bit_equal': True, 'R1_objective_diff': 0.0}) is True)
    check('A7_r2_form_diff_1e-9_edge_ok', f({'R1_objective_diff': 1e-9}) is True and f({'R1_objective_diff': -1e-9}) is True)
    check('A8_r2_form_diff_over', f({'R1_objective_diff': 1.0000001e-9}) is False and f({'R1_objective_diff': -3e-9}) is False)
    check('A9_missing_nan_bool_false', f({}) is False and f({'R1_objective_diff': float('nan')}) is False
          and f({'R1_objective_diff': float('inf')}) is False and f({'R1_objective_diff': True}) is False
          and f({'R1_objective_diff': None}) is False)
    check('A10_r3_bool_wins', f({'R1_objective_within_1e-9': False, 'R1_objective_diff': 0.0}) is False
          and f({'R1_objective_within_1e-9': True, 'R1_objective_diff': 0.0}) is True)
    check('A11_tolerance_constant', JC.R1_TOL == 1e-9)
    # existing records, read only (data after; values already reported in QV3_REPORT / P1_REPORT)
    real = {}
    for nm, rel in (('P1_s31_T1800_stopped', 'plant_P/v3c3-s31_T001800'), ('A_s31_T3300', 'plant_A/v3c3-s31_T003300'),
                    ('A_s31_T3450', 'plant_A/v3c3-s31_T003450')):
        p = C.OUT / rel / 'probe.json'
        if not p.is_file():   # the P1 folder may already have been moved (*_interrupted_*); then skip it
            real[nm] = None
            continue
        ck = (C.read_json(p) or {}).get('checks') or {}
        real[nm] = {'r1_objective_ok_r3': f(ck), 'costs_ok': ck.get('R1_costs_within_1e-9'),
                    'bit_equal_r2': ck.get('R1_objective_bit_equal'), 'sha256': C.sha256_file(p)}
    check('A12_existing_records_r3_rule', all(v is None or (v['r1_objective_ok_r3'] is True and v['costs_ok'] is True)
                                               for v in real.values()) and real.get('A_s31_T3300') is not None, real)
    return real


class Rec:
    def __init__(self, stop_on_acquire=None):
        self.calls = []
        self.stop_on_acquire = stop_on_acquire   # acquire number (1-based) at which STOP_VP appears while waiting
        self.n_acq = 0

    def lock_acquire(self, job, log=print, poll_sec=2.0):
        self.n_acq += 1
        self.calls.append(('acquire', job))
        if self.stop_on_acquire == self.n_acq:
            C.write_json(C.VP / 'STOP_VP', {'by': 'synthetic other queue', 'kst': C.kst()})
        return 0.0

    def lock_release(self, log=print):
        self.calls.append(('release',))
        return True

    def run_capture(self, argv, log_path, env, cwd=None, timeout=None):
        self.calls.append(('run', str(argv[-1])))
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text('synthetic\n', encoding='utf-8')
        return 0, 0.01


def run_queue(modname, tmp, scen, stop_before=False, stop_on_acquire=None):
    root = tmp / ('q_%s_%s' % (modname, scen))
    root.mkdir(parents=True, exist_ok=True)
    name = 'q_%s_%d' % (scen, os.getpid())
    jobs = root / 'jobs.json'
    C.write_json(jobs, {'name': name, 'jobs': [{'tag': 't1', 'kind': 'py', 'args': ['job1.py']},
                                               {'tag': 't2', 'kind': 'py', 'args': ['job2.py']}]})
    rec = Rec(stop_on_acquire)
    keep = {k: getattr(C, k) for k in ('VP', 'lock_acquire', 'lock_release', 'run_capture', 'require_space',
                                       'child_env', 'set_below_normal')}
    saved_argv = sys.argv
    try:
        C.VP = root
        if stop_before:
            C.write_json(root / 'STOP_VP', {'by': 'synthetic', 'kst': C.kst()})
        C.lock_acquire, C.lock_release, C.run_capture = rec.lock_acquire, rec.lock_release, rec.run_capture
        C.require_space = lambda log: {}
        C.child_env = lambda *a, **k: {}
        C.set_below_normal = lambda: None
        mod = importlib.import_module(modname)
        sys.argv = [modname + '.py', str(jobs)]
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main()
    finally:
        sys.argv = saved_argv
        for k, v in keep.items():
            setattr(C, k, v)
    logdir = root / 'logs' / name
    log = (logdir / 'queue.log').read_text(encoding='utf-8') if (logdir / 'queue.log').is_file() else ''
    runs = [c[1] for c in rec.calls if c[0] == 'run']
    return {'acquire': sum(c[0] == 'acquire' for c in rec.calls), 'release': sum(c[0] == 'release' for c in rec.calls),
            'runs': runs, 'done': sorted(p.name for p in logdir.glob('*.done')),
            'log_after_lock': 'STOP_VP present after LOCK' in log, 'log_before': 'STOP_VP present: stop before' in log,
            'queue_end': 'QUEUE_END' in log}


def part_b(tmp):
    out = {}
    # B1: STOP_VP appears while waiting on the LOCK for the first job
    r = run_queue('vp_queue', tmp, 'b1', stop_on_acquire=1)
    out['B1_r3'] = r
    check('B1_r3_stop_during_lock_wait_runs_nothing', r['acquire'] == 1 and r['release'] == 1 and r['runs'] == []
          and r['done'] == [] and r['log_after_lock'] and r['queue_end'], r)
    r2 = run_queue('vp_queue_r2', tmp, 'b1', stop_on_acquire=1)
    out['B1_r2'] = r2
    check('B1_r2_gap_shown', r2['runs'] == ['job1.py'] and r2['done'] == ['t1.done'], r2)
    # B2: no STOP_VP -> both jobs run, LOCK taken and released per job
    r = run_queue('vp_queue', tmp, 'b2')
    out['B2_r3'] = r
    check('B2_r3_no_stop_runs_all', r['acquire'] == 2 and r['release'] == 2 and r['runs'] == ['job1.py', 'job2.py']
          and r['done'] == ['t1.done', 't2.done'] and not r['log_after_lock'] and r['queue_end'], r)
    # B3: STOP_VP present before the queue starts -> no LOCK taken (pre-check unchanged)
    r = run_queue('vp_queue', tmp, 'b3', stop_before=True)
    out['B3_r3'] = r
    check('B3_r3_stop_before_no_lock', r['acquire'] == 0 and r['release'] == 0 and r['runs'] == [] and r['log_before'], r)
    # B4: STOP_VP appears while waiting for the second job's LOCK
    r = run_queue('vp_queue', tmp, 'b4', stop_on_acquire=2)
    out['B4_r3'] = r
    check('B4_r3_stop_during_second_wait', r['acquire'] == 2 and r['release'] == 2 and r['runs'] == ['job1.py']
          and r['done'] == ['t1.done'] and r['log_after_lock'], r)
    return out


def part_c(tmp):
    real_path = Path(str(C.CODE) + '.tree.json')
    real = C.read_json(real_path)
    res = TF.check(real)
    check('C1_real_record_fields', isinstance(real, dict) and all(res.values()), res)
    variants = {'C2_time_field_ignored': (dict(real, checked_kst='2099-01-01 00:00:00 KST'), True),
                'C3_ok_false': (dict(real, ok=False), False), 'C4_ok_int': (dict(real, ok=1), False),
                'C5_missing_n': (dict(real, missing_n=1), False), 'C6_differs_list': (dict(real, differs=['x']), False),
                'C7_files_expected': (dict(real, files_expected=10568), False),
                'C8_freeze_sha': (dict(real, freeze_sha256='0' * 64), False), 'C9_not_dict': ([], False)}
    for nm, (doc, want) in variants.items():
        r = TF.check(doc)
        check(nm, (isinstance(doc, dict) and all(r.values())) == want, r)
    return {'real_fields': res, 'real_sha256': C.sha256_file(real_path), 'real_checked_kst': real.get('checked_kst')}


def part_d():
    out = {}
    for f in ('vp_probe.py', 'vp_jobcheck.py', 'vp_queue.py', 'vp_treefields.py'):
        src = (TOOLS / f).read_text(encoding='utf-8')
        try:
            compile(src, f, 'exec')
            out[f] = True
        except SyntaxError as e:
            out[f] = repr(e)
    check('D1_compile', all(v is True for v in out.values()), out)
    src = (TOOLS / 'vp_probe.py').read_text(encoding='utf-8')
    stop_line = [ln for ln in src.splitlines() if 'and mode != \'S\':' in ln and 'R1_' in ln]
    check('D2_probe_stop_uses_tolerance', len(stop_line) == 1 and 'R1_objective_within_1e-9' in stop_line[0]
          and 'R1_objective_bit_equal' not in stop_line[0], stop_line)
    check('D3_probe_writes_both_fields', "out['checks']['R1_objective_bit_equal']" in src
          and "out['checks']['R1_objective_within_1e-9'] = math.isfinite(odiff) and abs(odiff) <= 1e-9" in src)
    qsrc = (TOOLS / 'vp_queue.py').read_text(encoding='utf-8')
    i_acq = qsrc.find("C.lock_acquire('vsl_plant")
    i_re = qsrc.find("STOP_VP present after LOCK")
    i_run = qsrc.find('C.run_capture(argv')
    check('D4_queue_recheck_between_lock_and_run', 0 < i_acq < i_re < i_run, (i_acq, i_re, i_run))
    return out


def main():
    tmp = VP / 'review_r3' / ('tmp_%d' % os.getpid())
    tmp.mkdir(parents=True, exist_ok=False)
    try:
        real = part_a(tmp)
        queue = part_b(tmp)
        tree = part_c(tmp)
        comp = part_d()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # own PID-unique temp folder only
    ok = all(r['ok'] for r in RES)
    shas = {f: C.sha256_file(TOOLS / f) for f in ('vp_probe.py', 'vp_jobcheck.py', 'vp_queue.py', 'vp_treefields.py',
                                                  'vp_probe_r2.py', 'vp_jobcheck_r2.py', 'vp_queue_r2.py')}
    C.write_json(sys.argv[1], {'schema': 'vp-r3-patchtest/1', 'kst': C.kst(), 'ok': ok, 'n': len(RES),
                               'n_ok': sum(r['ok'] for r in RES), 'results': RES, 'tool_sha256': shas,
                               'existing_records_r3_rule': real, 'queue_scenarios': queue, 'tree_record': tree,
                               'compile': comp, 'temp_folder_removed': not tmp.exists(),
                               'self_sha256': C.sha256_file(__file__)})
    print('R3_PATCHTEST %d/%d ok=%s' % (sum(r['ok'] for r in RES), len(RES), ok))
    for r in RES:
        if not r['ok']:
            print('FAIL', r)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
