"""C1 mini probe (K8 amendment C1 a98580dd..., section 5; report only, not a verdict).  Probe tree
TC1/trees/probe_<patch sha8> = git archive c20aff1d + C1D/tools/c1_probe.patch.  One heavy job at a time under the
shared LOCK (per decision / per plant state), BELOW_NORMAL, python -B, PYTHONHASHSEED=0.

    python -B c1_probe.py decisions   5 states (c1_states /probe_decisions_T900) x 7 arms {off, omega, m, h, c1, m_cap1,
                                      m_noheld}: gprep copy + the tree's k92_replay.py --tuning <arm> (R-obs: wu-link)
    python -B c1_probe.py plant       16 states (/probe_plant_jobs) x {off, omega, h}: the tree's SA harness captures +
                                      TL3 H3 OBS jobs (k8b_commit_gates capture / job; old k92_guard, F_SECOND states)
    python -B c1_probe.py report      C1D/C1_PROBE_RESULTS.json (+ .md written by hand from it); stop rules 1-4
Outputs TC1/out/probe/.  BLIND: v3c3-s47 never touched (states come from the declared lists only)."""
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402

MAN = json.loads((C.TOOLS / 'c1_probe_patch_manifest.json').read_text(encoding='utf-8'))
PROBE = C.TC1 / 'trees' / ('probe_' + MAN['patch_sha256'][:8])
OUTP = C.TC1 / 'out' / 'probe'
NUMBA = OUTP / 'numba_cache'
STATES = json.loads((C.DECL / 'c1_states.json').read_text(encoding='utf-8'))
ARMS = json.loads((C.TOOLS / 'arms' / 'ARMS.json').read_text(encoding='utf-8'))['arms']
DEC_ARMS = ('off', 'omega', 'm', 'h', 'c1', 'm_cap1', 'm_noheld')
PLANT_ARMS = ('off', 'omega', 'h')
LOG = C.make_logger(OUTP / 'logs' / 'c1_probe.log')
STALL_SEC = 45 * 60
SA_REL = C.N31 + '/k8_gates/sa'
WALL_LIMIT = 1500.0


def scode(st):
    seed = int(st['run'].rsplit('_s', 1)[1])
    return ('va' if st['kind'] == 'va' else 'robs') + 's%d' % seed


def dec_tag(st, arm):
    return 't%06d_%s_%s' % (st['T'], scode(st), arm)


def run_dir_of(run):
    C.blind_guard(run)
    for kind in ('va', 'robs'):
        d = C.RUNS[kind] / run
        if d.is_dir():
            return d
    raise SystemExit('run folder not found: ' + run)


def kill_tree(pid):
    subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)


def run_watched(argv, log_path, env, progress, cwd=None):
    t0 = time.time()
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8', errors='replace') as out:
        proc = subprocess.Popen([str(a) for a in argv], stdout=out, stderr=subprocess.STDOUT, env=env,
                                cwd=str(cwd) if cwd else None, creationflags=C.BELOW_NORMAL)
        last, killed = time.time(), False
        while proc.poll() is None:
            time.sleep(20)
            try:
                last = max(last, os.path.getmtime(progress))
            except OSError:
                pass
            if time.time() - last > STALL_SEC:
                LOG('STALL %s no progress for %ds: killing own PID tree %d' % (Path(log_path).name, STALL_SEC, proc.pid))
                kill_tree(proc.pid)
                killed = True
                break
        rc = proc.wait()
    return rc, time.time() - t0, proc.pid, killed


def blind_compare(cmp):
    out = {'verdict': cmp.get('verdict'), 'checks': {k: (v or {}).get('ok') for k, v in (cmp.get('checks') or {}).items()}}
    out['derived_differences_n'] = len(((cmp.get('checks') or {}).get('derived') or {}).get('differences') or [])
    out['action_controls_differences_n'] = len(((cmp.get('checks') or {}).get('action_controls') or {}).get('differences') or [])
    return out


def one_decision(st, arm):
    tag = dec_tag(st, arm)
    runs = OUTP / 'dec'
    d = runs / tag
    summary_path = runs / (tag + '.summary.json')
    if summary_path.is_file():
        LOG('SKIP %s (summary exists)' % tag)
        return C.read_json(summary_path)
    C.require_space(LOG)
    tuning = C.TOOLS / 'arms' / (arm + '.json')
    if C.sha256_file(tuning) != ARMS[arm]['sha256']:
        raise SystemExit('arm tuning changed: ' + arm)
    if d.exists():
        moved = runs / ('%s_interrupted_%s' % (tag, time.strftime('%Y%m%d_%H%M%S')))
        d.rename(moved)
        LOG('MOVED_INTERRUPTED %s -> %s' % (d, moved.name))
    run = st['run']
    dec = run_dir_of(run) / ('decisions_' + run)
    env = C.child_env(NUMBA)
    summary = {'tag': tag, 'run': run, 'T': st['T'], 'kind': st['kind'], 'arm': arm, 'tuning_sha256': ARMS[arm]['sha256'],
               'tree': PROBE.name, 'vissim_count_pre': C.vissim_count(), 'free_gb_at_start': C.free_space_gb(),
               'started': time.strftime('%Y-%m-%dT%H:%M:%S')}
    rec_path = runs / (tag + '.prep.json')
    rc, sec, _ = C.run_capture([C.PY, '-B', str(C.GPREP), str(dec), str(st['T']), str(d), str(rec_path)],
                               runs / (tag + '.prepare.txt'), env)
    pr = C.read_json(rec_path) or {}
    summary['prepare'] = {'exit': rc, 'sec': round(sec, 1), 'all_copies': pr.get('all_copies'),
                          'bundle_dir': pr.get('state_obs150_directory_is_bundle'),
                          'history': [pr.get('history_count'), pr.get('history_expected')],
                          'previous_sec': pr.get('previous_sec')}
    if rc != 0 or not pr.get('all_copies') or not pr.get('state_obs150_directory_is_bundle') \
            or pr.get('history_count') != pr.get('history_expected'):
        summary.update(infra_failure='prepare_failed', finished=time.strftime('%Y-%m-%dT%H:%M:%S'))
        C.write_json(summary_path, summary)
        LOG('PREPARE_FAILED %s' % tag)
        return summary
    kr = PROBE / SA_REL / 'k92_replay.py'
    argv = [C.PY, '-B', str(kr), '--replay-dir', str(d), '--root', str(PROBE), '--tuning', str(tuning)]
    if st['kind'] == 'robs':
        argv += ['--controller', 'wu-link']
    summary['launcher_sha256'] = C.sha256_file(kr)
    progress = d / 'replay' / ('action_%06d.joint.progress.jsonl' % st['T'])
    LOG('START %s' % tag)
    rc, sec, pid, killed = run_watched(argv, runs / (tag + '.launch.txt'), env, progress)
    rd = d / 'replay'
    rr = C.read_json(rd / 'replay_run.json', {}) or {}
    summary['launch'] = {'exit': rc, 'sec': round(sec, 1), 'pid': pid, 'killed': killed}
    summary['replay_run'] = {'exit_code': rr.get('exit_code'), 'wall_sec': rr.get('wall_sec'),
                             'controller': rr.get('controller')}
    summary['standing'] = {'error_files': sorted(p.name for p in rd.glob('*.error.txt')) if rd.is_dir() else None,
                           'decision_failed': [C.text_count(rd / n, 'DECISION_FAILED')
                                               for n in ('adapter_stdout.txt', 'adapter_stderr.txt')]}
    if (d / 'replay_compare.json').is_file():
        summary['compare'] = blind_compare(C.read_json(d / 'replay_compare.json', {}) or {})
    for name in ('csv', 'json'):
        p = rd / ('action_%06d.%s' % (st['T'], name))
        summary['action_%s_sha256' % name] = C.sha256_file(p) if p.is_file() else None
    summary['vissim_count_post'] = C.vissim_count()
    summary['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    if killed:
        summary['infra_failure'] = 'stall_killed'
    C.write_json(summary_path, summary)
    LOG('DONE %s exit=%s adapter_exit=%s wall=%s err=%s df=%s killed=%s' % (
        tag, rc, rr.get('exit_code'), rr.get('wall_sec'), summary['standing']['error_files'],
        summary['standing']['decision_failed'], killed))
    return summary


def stage_decisions():
    if not PROBE.is_dir():
        raise SystemExit('probe tree missing: ' + str(PROBE))
    for arm in DEC_ARMS:
        for st in STATES['probe_decisions_T900']:
            if (OUTP / 'dec' / (dec_tag(st, arm) + '.summary.json')).is_file():
                continue
            C.lock_acquire('c1 probe decision %s' % dec_tag(st, arm), LOG)
            try:
                one_decision(st, arm)
            finally:
                C.lock_release(LOG)
    LOG('DECISIONS_DONE')


# ------------------------------------------------------------------------------------------------ plant
def plant_child(seed, T):
    """Inside a python whose sys.path[0] is the probe tree's sa folder (stage_plant starts it)."""
    import k8b_commit_gates as cg
    cg.setup(str(PROBE), str(OUTP / 'plant'))
    cg.free_space()
    cg.prep_states([(seed, T)])
    for arm in PLANT_ARMS:
        path = C.TOOLS / 'arms' / (arm + '.json')
        tun = cg.tuning_rec(path)
        if tun['sha256'] != ARMS[arm]['sha256']:
            raise SystemExit('arm tuning changed: ' + arm)
        cg.capture('c1p' + arm, 'tl3', 'SAF', seed, T, tun)
        cg.job('c1p' + arm, 'TL3', T, 'SAF', 'OBS', 3, seed=seed)
    cg.log('C1_PLANT_STATE_DONE s%d %d' % (seed, T))


def stage_plant():
    sa = PROBE / SA_REL
    for st in STATES['probe_plant_jobs']:
        seed = int(st['run'].rsplit('_s', 1)[1])
        C.blind_guard(st['run'])
        if int(st['H']) != 3:
            raise SystemExit('probe plant jobs are H3')
        if all((job_dir(a, seed, st['T']) / 'summary.json').is_file() for a in PLANT_ARMS):
            continue
        C.lock_acquire('c1 probe plant s%d T=%d (3 arms)' % (seed, st['T']), LOG)
        try:
            env = C.child_env(NUMBA)
            code = ('import sys; sys.path.insert(0, %r); sys.path.insert(0, %r); import c1_probe; '
                    'c1_probe.plant_child(%d, %d)' % (str(Path(__file__).resolve().parent), str(sa), seed, st['T']))
            rc, sec, _ = C.run_capture([C.PY, '-B', '-c', code], OUTP / 'logs' / ('plant_s%d_%06d.txt' % (seed, st['T'])),
                                       env, cwd=sa)
            LOG('PLANT_CHILD s%d T=%d exit=%s sec=%.0f' % (seed, st['T'], rc, sec))
        finally:
            C.lock_release(LOG)
    LOG('PLANT_DONE')


def plant_label(seed, T):
    return 'TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed)


def job_dir(arm, seed, T):
    return OUTP / 'plant' / 'sa' / 'jobs' / ('c1p' + arm) / plant_label(seed, T)


def cap_dir(arm, seed, T):
    return OUTP / 'plant' / 'sa' / 'cap' / ('c1p' + arm) / 'TL3' / ('%06d%s' % (T, '' if seed == 31 else '_s%d' % seed)) / 'SAF'


# ------------------------------------------------------------------------------------------------ report
def greens_of(action):
    diag = (action or {}).get('diagnostics') or {}
    b0 = {m: diag.get('rw_meter_green_' + m) for m in C.METERS}
    fut = ((diag.get('sdmpc_prediction_sequence') or {}).get('future')) or []
    blocks = [b0] + [{m: (f.get('diagnostics') or {}).get('rw_meter_green_' + m) for m in C.METERS} for f in fut]
    return blocks


def prev_greens(run, T):
    p = run_dir_of(run) / ('decisions_' + run) / ('action_%06d.csv' % (T - 150))
    rows = [r for r in csv.DictReader(p.read_text(encoding='utf-8-sig').splitlines()) if r['kind'] == 'ramp_meter']
    return {r['id']: float(r['green_sec']) for r in rows}


def sg_green(csv_path, prefix):
    rows = [r for r in csv.DictReader(Path(csv_path).read_text(encoding='utf-8-sig').splitlines())
            if r['kind'] == 'signal_sg' and r['id'].startswith(prefix)]
    if not rows:
        return None
    return math.fsum((150.0 / float(r['green_sec'])) * (float(r['p2_green']) - float(r['p1_green'])) for r in rows)


def series(job):
    import numpy as np
    p = job / 'k92_series.npz'
    if not p.is_file():
        return None
    z = np.load(p, allow_pickle=True)
    return {k: z[k] for k in z.files}


def same_series(a, b):
    import numpy as np
    if a is None or b is None:
        return None, 'series missing'
    if list(a['keys']) != list(b['keys']):
        ka, kb = set(a['keys']), set(b['keys'])
        return False, 'keys differ (only off %d, only arm %d)' % (len(ka - kb), len(kb - ka))
    if a['model'].shape != b['model'].shape or not np.array_equal(a['t_end'], b['t_end']) \
            or not np.array_equal(a['stage'], b['stage']):
        return False, 'rows / times / stages differ'
    ma, mb = a['model'], b['model']
    eq = (ma == mb) | (np.isnan(ma) & np.isnan(mb))
    if not eq.all():
        bad = np.argwhere(~eq)
        keys = sorted({str(a['keys'][j]) for _, j in bad[:2000]})
        return False, 'model_stock_veh differs in %d cells; first row %d; keys %s' % (len(bad), int(bad[0][0]), keys[:12])
    return True, 'equal'


def stage_report():
    values = C.read_json(C.C1D / 'C1_VALUES.json') or {}
    exp = values.get('p0_11') or {}
    res = {'schema': 'c1-probe-results/v1', 'head': '탐침, 판정 아님', 'tree': PROBE.name,
           'patch_sha256': MAN['patch_sha256'], 'decisions': {}, 'plant': {}, 'stop_rules': {}}
    problems, incomplete = [], []
    tighten_any = False
    walls_c1 = []
    for arm in DEC_ARMS:
        for st in STATES['probe_decisions_T900']:
            tag = dec_tag(st, arm)
            s = C.read_json(OUTP / 'dec' / (tag + '.summary.json'))
            if s is None:
                incomplete.append('decision ' + tag)
                continue
            rd = OUTP / 'dec' / tag / 'replay'
            act = C.read_json(rd / ('action_%06d.json' % st['T'])) or {}
            md = act.get('metadata') or {}
            js = md.get('joint_leader_selection') or {}
            ok = (s.get('replay_run') or {}).get('exit_code') == 0 and not (s.get('standing') or {}).get('error_files') \
                and not any((s.get('standing') or {}).get('decision_failed') or []) and not s.get('infra_failure') \
                and bool(act)
            if not ok:
                problems.append('decision %s exit=%s err=%s df=%s infra=%s' % (
                    tag, (s.get('replay_run') or {}).get('exit_code'), (s.get('standing') or {}).get('error_files'),
                    (s.get('standing') or {}).get('decision_failed'), s.get('infra_failure')))
            prev = prev_greens(st['run'], st['T'])
            blocks = greens_of(act)
            tighten = [m for m in C.METERS if isinstance(blocks[0].get(m), (int, float)) and blocks[0][m] < prev[m]]
            audit = js.get('meter_neighbor_audit') or {}
            per_inc = []
            for a in audit.get('budget_audits') or []:
                rows = a.get('candidates') or []
                per_inc.append({'np_cap': a.get('np_cap'), 'rows': len(rows),
                                'without_combined': sum(1 for r in rows if r.get('candidate') != 'combined_meter_owners'),
                                'selected': a.get('selected')})
            mob = js.get('meter_operating_bounds') or {}
            row = {'ok': ok, 'wall_sec': (s.get('replay_run') or {}).get('wall_sec'),
                   'vissim_pre_post': [s.get('vissim_count_pre'), s.get('vissim_count_post')],
                   'token': (md.get('sdmpc_state') or {}).get('policy_sha256'),
                   'metadata_c1_port_keys': sorted((md.get('c1_port') or {}).keys()),
                   'block_greens': blocks, 'previous_greens': prev, 'tighten_meters_block0': tighten,
                   'audit_selected': audit.get('selected'), 'audit_candidates': [
                       {k: r.get(k) for k in ('candidate', 'objective', 'feasible', 'delta_veh_h', 'np_cap')}
                       for r in audit.get('candidates') or []],
                   'audit_per_incumbent': per_inc, 'expected_tighten_count': (exp.get(scode_p0(st)) or {}).get('N_tighten'),
                   'floors': {m: (mob.get('ramps') or {}).get(m, {}).get('minimum_green_sec') for m in C.METERS} if mob else None,
                   'triggered': {m: (mob.get('ramps') or {}).get(m, {}).get('triggered') for m in C.METERS} if mob else None,
                   'cap_targets': len(js.get('candidates') or []),
                   'held_candidate': {k: (js.get('original_held_candidate') or {}).get(k)
                                      for k in ('evaluated', 'selected', 'feasible', 'reason')} if 'original_held_candidate' in js else None,
                   'selected_objective': js.get('selected_objective'), 'held_objective': js.get('held_objective'),
                   'omega_kind': 'Ω701' if 'omega701' in ARMS[arm]['keys'] else 'Ω635',
                   'sg2_block0': sg_green(rd / ('action_%06d.csv' % st['T']), 'SC1001_SG2_W') if (rd / ('action_%06d.csv' % st['T'])).is_file() else None,
                   'sg5_block0': sg_green(rd / ('action_%06d.csv' % st['T']), 'SC1001_SG5_W') if (rd / ('action_%06d.csv' % st['T'])).is_file() else None,
                   'rollouts': (js.get('surrogate_query') or {}).get('total_rollouts') if isinstance(js.get('surrogate_query'), dict) else None,
                   'compare': s.get('compare')}
            res['decisions'][tag] = row
            if arm in ('m', 'c1') and tighten:
                tighten_any = True
            if arm == 'c1' and isinstance(row['wall_sec'], (int, float)):
                walls_c1.append(row['wall_sec'])
    for st in STATES['probe_plant_jobs']:
        seed = int(st['run'].rsplit('_s', 1)[1])
        base = None
        for arm in PLANT_ARMS:
            j = job_dir(arm, seed, st['T'])
            s = C.read_json(j / 'summary.json')
            r = C.read_json(j / 'k92_record.json') or {}
            capf = (cap_dir(arm, seed, st['T']) / 'capture_failed.json').is_file()
            key = 's%d_T%06d_%s' % (seed, st['T'], arm)
            if s is None:
                incomplete.append('plant ' + key)
                res['plant'][key] = {'ok': None, 'capture_failed': capf}
                continue
            row = {'ok': s.get('ok'), 'error': (s.get('error') or '')[-200:], 'k92_errors': r.get('errors'),
                   'capture_failed': capf, 'outw_veh_h_450': (r.get('horizon') or {}).get('outw_veh_h_450')}
            if not s.get('ok') or r.get('errors') or capf:
                problems.append('plant %s ok=%s k92_errors=%s capture_failed=%s' % (key, s.get('ok'), r.get('errors'), capf))
            ser = series(j)
            if arm == 'off':
                base = ser
            else:
                same, why = same_series(base, ser)
                row['trajectory_equal_off'] = same
                row['trajectory_detail'] = why
            res['plant'][key] = row
    stop2 = [k for k, v in res['plant'].items() if v.get('trajectory_equal_off') is False]
    med = statistics.median(walls_c1) if walls_c1 else None
    res['stop_rules'] = {
        '1_exception_or_invariant': problems,
        '2_omega_h_trajectory_differs': stop2,
        '3_no_tightening_in_m_c1_5_states': not tighten_any,
        '4_c1_wall_median_gt_1500': (med is not None and med > WALL_LIMIT),
        'c1_wall_median_sec': med, 'c1_wall_max_sec': max(walls_c1) if walls_c1 else None,
        'incomplete': incomplete}
    fired = bool(problems) or bool(stop2) or (not tighten_any) or (med is not None and med > WALL_LIMIT) or bool(incomplete)
    res['any_stop_or_ask'] = fired
    path = C.C1D / 'C1_PROBE_RESULTS.json'
    C.write_json(path, res)
    LOG('PROBE_REPORT written sha256=%s fired=%s' % (C.sha256_file(path), fired))


def scode_p0(st):
    return '%s_t%06d' % (st['run'].replace('sdmpc31_', ''), st['T'])


if __name__ == '__main__':
    C.set_below_normal()
    stage = sys.argv[1] if len(sys.argv) > 1 else ''
    LOG('PROBE start %s' % stage)
    {'decisions': stage_decisions, 'plant': stage_plant, 'report': stage_report}[stage]()
    LOG('PROBE end %s' % stage)
