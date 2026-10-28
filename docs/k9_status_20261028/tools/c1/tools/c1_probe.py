"""C1 mini probe (K8 amendment C1 a98580dd..., section 5; report only, not a verdict).  Probe tree
TC1/trees/probe_<patch sha8> = git archive c20aff1d + C1D/tools/c1_probe.patch.  One heavy job at a time under the
shared LOCK (per decision / per plant state / the report read), BELOW_NORMAL, python -B, PYTHONHASHSEED=0, the K9-2
replay environment (c1common.child_env: OMP / MKL / OPENBLAS threads 1, NUMBA_NUM_THREADS removed as in
k92/bundle1/a25decl/tools/k92lib.py:99).

    python -B c1_probe.py plant       16 states (c1_states /probe_plant_jobs) x {off, omega, h}: the tree's SA harness
                                      captures + TL3 H3 OBS jobs (k8b_commit_gates capture / job; old k92_guard, all
                                      16 states are k92_common.F_SECOND).  Halts at the first state with a failure or
                                      an Omega / H trajectory difference (probe stop 1 / 2).
    python -B c1_probe.py decisions   5 states (/probe_decisions_T900) x 7 arms, arm order c1, m, omega, h, off,
                                      m_cap1, m_noheld: gprep copy + the tree's guard-free k92_replay.py --tuning <arm>
                                      (R-obs: --controller wu-link; compare with the record only for arm off).  Halts
                                      at the first decision that is not clean (probe stop 1).
    python -B c1_probe.py report      C1D/C1_PROBE_RESULTS.json; probe stop rules 1-4 (amendment C1 section 5.4)
A halt writes TC1/out/probe/HALT.json; a later call refuses to go on while it exists (user decision).
Seeds and labels come from c1_states.json /runs (seed_from_provenance; the run_provenance file sha256 is checked),
never from a folder or file name.  States come from the declared lists only.  Outputs TC1/out/probe/.
BLIND: v3c3-s47 never touched (c1common.blind_guard on every run name)."""
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
HALT = OUTP / 'HALT.json'
STATES = json.loads((C.DECL / 'c1_states.json').read_text(encoding='utf-8'))
RUNS = {r['name']: r for r in STATES['runs']}
ARMS = json.loads((C.TOOLS / 'arms' / 'ARMS.json').read_text(encoding='utf-8'))['arms']
DEC_ARMS = ('c1', 'm', 'omega', 'h', 'off', 'm_cap1', 'm_noheld')
PLANT_ARMS = ('off', 'omega', 'h')
COMPARE_ARMS = ('off',)
LOG = C.make_logger(OUTP / 'logs' / 'c1_probe.log')
STALL_SEC = 45 * 60
SA_REL = C.N31 + '/k8_gates/sa'
WALL_LIMIT = 1500.0          # probe stop 4 (amendment C1 section 5.4-4), median of the C1 arm


# ------------------------------------------------------------------------------------------------ states
def run_rec(run):
    C.blind_guard(run)
    r = RUNS.get(run)
    if r is None:
        raise SystemExit('run not in c1_states.json /runs: ' + run)
    return r


def seed_of(run):
    return int(run_rec(run)['seed_from_provenance'])


def label_of(run):
    return run_rec(run)['label']


def run_dir_of(run):
    r = run_rec(run)
    d = C.RUNS[r['kind']] / run
    if not d.is_dir():
        raise SystemExit('run folder not found: ' + run)
    prov = d / ('run_provenance_%s.json' % run)
    if C.sha256_file(prov) != r['provenance_sha256']:
        raise SystemExit('run_provenance sha256 differs from c1_states.json: ' + run)
    return d


def scode(st):
    return ('va' if st['kind'] == 'va' else 'robs') + 's%d' % seed_of(st['run'])


def dec_tag(st, arm):
    return 't%06d_%s_%s' % (st['T'], scode(st), arm)


def p0_key(st):
    return '%s_t%06d' % (st['run'].replace('sdmpc31_', ''), st['T'])     # the c1_p0.py state_tag (C1_VALUES keys)


def declared(st, listname):
    return any(x['run'] == st['run'] and int(x['T']) == int(st['T']) for x in STATES[listname])


# ------------------------------------------------------------------------------------------------ halt
def halt(reason, detail):
    C.write_json(HALT, {'reason': reason, 'detail': detail, 'at': time.strftime('%Y-%m-%dT%H:%M:%S')})
    LOG('HALT %s %s' % (reason, json.dumps(detail, default=str)[:600]))


def refuse_if_halted():
    if HALT.is_file():
        raise SystemExit('HALT.json exists (%s): user decision first' % HALT)


# ------------------------------------------------------------------------------------------------ children
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


# ------------------------------------------------------------------------------------------------ decisions
def decision_clean(s):
    st = s.get('standing') or {}
    return ((s.get('replay_run') or {}).get('exit_code') == 0 and not st.get('error_files')
            and all(x == 0 for x in (st.get('decision_failed') or [None])) and not s.get('infra_failure')
            and bool(s.get('action_json_sha256')))


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
    summary = {'tag': tag, 'run': run, 'label': label_of(run), 'T': st['T'], 'kind': st['kind'], 'arm': arm,
               'tuning_sha256': ARMS[arm]['sha256'], 'tree': PROBE.name, 'vissim_count_pre': C.vissim_count(),
               'free_gb_at_start': C.free_space_gb(), 'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
               'env_threads': {k: env.get(k) for k in ('OMP_NUM_THREADS', 'NUMBA_NUM_THREADS', 'PYTHONHASHSEED')}}
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
    if arm not in COMPARE_ARMS:
        argv += ['--no-compare']
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
    LOG('DONE %s exit=%s adapter_exit=%s wall=%s err=%s df=%s killed=%s vissim=%s/%s' % (
        tag, rc, rr.get('exit_code'), rr.get('wall_sec'), summary['standing']['error_files'],
        summary['standing']['decision_failed'], killed, summary['vissim_count_pre'], summary['vissim_count_post']))
    return summary


def stage_decisions():
    refuse_if_halted()
    if not PROBE.is_dir():
        raise SystemExit('probe tree missing: ' + str(PROBE))
    for arm in DEC_ARMS:
        for st in STATES['probe_decisions_T900']:
            if not declared(st, 'probe_decisions_T900'):
                raise SystemExit('state outside the declared probe list')
            if (OUTP / 'dec' / (dec_tag(st, arm) + '.summary.json')).is_file():
                s = C.read_json(OUTP / 'dec' / (dec_tag(st, arm) + '.summary.json')) or {}
            else:
                C.lock_acquire('c1 probe decision %s' % dec_tag(st, arm), LOG)
                try:
                    s = one_decision(st, arm)
                finally:
                    C.lock_release(LOG)
            if not decision_clean(s):
                halt('decision_not_clean (probe stop 1 / INCOMPLETE)', {'tag': dec_tag(st, arm),
                                                                      'replay_run': s.get('replay_run'),
                                                                      'standing': s.get('standing'),
                                                                      'infra_failure': s.get('infra_failure')})
                return
    LOG('DECISIONS_DONE')


# ------------------------------------------------------------------------------------------------ plant
def plant_child(seed, T, index_path):
    """Inside a python whose sys.path[0] is the probe tree's sa folder (stage_plant starts it)."""
    import k8b_commit_gates as cg
    cg.setup(str(PROBE), str(OUTP / 'plant'))
    cg.free_space()
    cg.prep_states([(seed, T)])
    idx = {'seed': seed, 'T': T, 'arms': {}}
    for arm in PLANT_ARMS:
        path = C.TOOLS / 'arms' / (arm + '.json')
        tun = cg.tuning_rec(path)
        if tun['sha256'] != ARMS[arm]['sha256']:
            raise SystemExit('arm tuning changed: ' + arm)
        tree = 'c1p' + arm
        cap = cg.capture(tree, 'tl3', 'SAF', seed, T, tun)
        jd = cg.job(tree, 'TL3', T, 'SAF', 'OBS', 3, seed=seed)
        idx['arms'][arm] = {'tree': tree, 'cap_dir': str(cap), 'job_dir': str(jd), 'tuning_sha256': tun['sha256']}
        C.write_json(index_path, idx)
    cg.log('C1_PLANT_STATE_DONE s%d %d' % (seed, T))


def plant_index_path(seed, T):
    return OUTP / 'plant' / 'index' / ('s%d_t%06d.json' % (seed, T))


def series(job):
    import numpy as np
    p = Path(job) / 'k92_series.npz'
    if not p.is_file():
        return None
    z = np.load(p, allow_pickle=True)
    return {k: z[k] for k in z.files}


def same_series(a, b):
    import numpy as np
    if a is None or b is None:
        return None, 'series missing'
    if list(a['keys']) != list(b['keys']):
        ka, kb = set(map(str, a['keys'])), set(map(str, b['keys']))
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
    return True, 'equal (%d rows x %d keys)' % ma.shape


def plant_state_rows(seed, T):
    """Per arm: ok / errors / trajectory vs off for one plant state (reads the child index)."""
    idx = C.read_json(plant_index_path(seed, T)) or {}
    rows, base = {}, None
    for arm in PLANT_ARMS:
        a = (idx.get('arms') or {}).get(arm)
        if not a:
            rows[arm] = {'ok': None, 'missing': True}
            continue
        j, cap = Path(a['job_dir']), Path(a['cap_dir'])
        s = C.read_json(j / 'summary.json')
        r = C.read_json(j / 'k92_record.json') or {}
        capf = (cap / 'capture_failed.json').is_file()
        row = {'ok': (s or {}).get('ok'), 'summary_present': s is not None, 'error': ((s or {}).get('error') or '')[-200:],
               'k92_errors': r.get('errors'), 'capture_failed': capf, 'series_file': (j / 'k92_series.npz').is_file(),
               'outw_veh_h_450': (r.get('horizon') or {}).get('outw_veh_h_450'), 'objective': (s or {}).get('objective')}
        ser = series(j)
        if arm == 'off':
            base = ser
        else:
            same, why = same_series(base, ser)
            row['trajectory_equal_off'] = same
            row['trajectory_detail'] = why
        rows[arm] = row
    return rows


def plant_problems(rows):
    probs = []
    for arm, r in rows.items():
        if r.get('missing') or not r.get('summary_present') or r.get('ok') is not True or r.get('k92_errors') \
                or r.get('capture_failed') or not r.get('series_file'):
            probs.append('%s ok=%s summary=%s k92_errors=%s capture_failed=%s series=%s' % (
                arm, r.get('ok'), r.get('summary_present'), r.get('k92_errors'), r.get('capture_failed'),
                r.get('series_file')))
        if arm != 'off' and r.get('trajectory_equal_off') is not True and not r.get('missing'):
            probs.append('%s trajectory %s: %s' % (arm, r.get('trajectory_equal_off'), r.get('trajectory_detail')))
    return probs


def stage_plant():
    refuse_if_halted()
    sa = PROBE / SA_REL
    for st in STATES['probe_plant_jobs']:
        if not declared(st, 'probe_plant_jobs') or int(st['H']) != 3:
            raise SystemExit('probe plant jobs are the declared H3 list')
        seed, T = seed_of(st['run']), int(st['T'])
        run_dir_of(st['run'])                                  # provenance sha check
        idx = C.read_json(plant_index_path(seed, T)) or {}
        done = all((Path(((idx.get('arms') or {}).get(a) or {}).get('job_dir', '-')) / 'summary.json').is_file()
                   for a in PLANT_ARMS)
        if not done:
            C.lock_acquire('c1 probe plant %s T=%d (3 arms)' % (label_of(st['run']), T), LOG)
            try:
                C.require_space(LOG)
                env = C.child_env(NUMBA)
                code = ('import sys; sys.path.insert(0, %r); sys.path.insert(0, %r); import c1_probe; '
                        'c1_probe.plant_child(%d, %d, %r)' % (str(Path(__file__).resolve().parent), str(sa), seed, T,
                                                              str(plant_index_path(seed, T))))
                rc, sec, _ = C.run_capture([C.PY, '-B', '-c', code],
                                           OUTP / 'logs' / ('plant_%s_t%06d.txt' % (scode(st), T)), env, cwd=sa)
                LOG('PLANT_CHILD %s T=%d exit=%s sec=%.0f vissim=%s' % (label_of(st['run']), T, rc, sec, C.vissim_count()))
            finally:
                C.lock_release(LOG)
        else:
            rc = 0
        rows = plant_state_rows(seed, T)
        probs = plant_problems(rows)
        if rc != 0:
            probs.insert(0, 'child exit %s' % rc)
        if probs:
            halt('plant_state_problem (probe stop 1 / 2 / INCOMPLETE)', {'state': [label_of(st['run']), T],
                                                                       'problems': probs})
            return
    LOG('PLANT_DONE')


# ------------------------------------------------------------------------------------------------ report
def greens_of(action):
    diag = (action or {}).get('diagnostics') or {}
    b0 = {m: diag.get('rw_meter_green_' + m) for m in C.METERS}
    fut = ((diag.get('sdmpc_prediction_sequence') or {}).get('future')) or []
    return [b0] + [{m: (f.get('diagnostics') or {}).get('rw_meter_green_' + m) for m in C.METERS} for f in fut]


def prev_greens(run, T):
    """S-C1-7 / RV-13b: the executed command of the run's action_<T-150> = its diagnostics.rw_meter_green_<meter>
    (the action CSV ramp_meter green_sec is kept as a cross-check)."""
    dec = run_dir_of(run) / ('decisions_' + run)
    j = C.read_json(dec / ('action_%06d.json' % (T - 150))) or {}
    diag = j.get('diagnostics') or {}
    js = {m: diag.get('rw_meter_green_' + m) for m in C.METERS}
    rows = [r for r in csv.DictReader((dec / ('action_%06d.csv' % (T - 150))).read_text(encoding='utf-8-sig').splitlines())
            if r['kind'] == 'ramp_meter']
    cs = {r['id']: float(r['green_sec']) for r in rows}
    return js, cs, ('sdmpc_state' in (j.get('metadata') or {}))


def sg_green(csv_path, prefix):
    rows = [r for r in csv.DictReader(Path(csv_path).read_text(encoding='utf-8-sig').splitlines())
            if r['kind'] == 'signal_sg' and r['id'].startswith(prefix)]
    if not rows:
        return None
    return math.fsum((150.0 / float(r['green_sec'])) * (float(r['p2_green']) - float(r['p1_green'])) for r in rows)


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def decision_row(st, arm, s, exp, rd=None):
    rd = Path(rd) if rd is not None else OUTP / 'dec' / dec_tag(st, arm) / 'replay'
    act = C.read_json(rd / ('action_%06d.json' % st['T'])) or {}
    md = act.get('metadata') or {}
    js = md.get('joint_leader_selection') or {}
    prev_js, prev_csv, prev_has_state = prev_greens(st['run'], st['T'])
    blocks = greens_of(act)
    tighten = [m for m in C.METERS if num(blocks[0].get(m)) is not None and num(prev_js.get(m)) is not None
               and blocks[0][m] < prev_js[m]]
    audit = js.get('meter_neighbor_audit') or {}
    per_inc = []
    for a in audit.get('budget_audits') or []:
        rows = a.get('candidates') or []
        per_inc.append({'np_cap': a.get('np_cap'), 'nuf_target': a.get('nuf_target'), 'rows': len(rows),
                        'without_combined': sum(1 for r in rows if r.get('candidate') != 'combined_meter_owners'),
                        'tighten_rows': sum(1 for r in rows if str(r.get('candidate', '')).endswith(':tighten')),
                        'release_rows': sum(1 for r in rows if str(r.get('candidate', '')).endswith(':release')),
                        'combined_rows': sum(1 for r in rows if r.get('candidate') == 'combined_meter_owners'),
                        'selected': a.get('selected'),
                        'candidates': [{k: r.get(k) for k in ('candidate', 'delta_veh_h', 'feasible', 'objective')}
                                       for r in rows]})
    mob = js.get('meter_operating_bounds') or {}
    ramps = mob.get('ramps') or {}
    held = js.get('original_held_candidate')
    e = exp.get(p0_key(st)) or {}
    return {
        'ok': decision_clean(s), 'wall_sec': (s.get('replay_run') or {}).get('wall_sec'),
        'vissim_pre_post': [s.get('vissim_count_pre'), s.get('vissim_count_post')],
        'token_sdmpc_state': (md.get('sdmpc_state') or {}).get('policy_sha256'),
        'token_price_state': (js.get('price_state') or {}).get('policy_sha256'),
        'policy_has_meter_neighbor_audit': 'meter_neighbor_audit' in (js.get('policy') or {}),
        'finite_neighbor_audit_performed': js.get('finite_neighbor_audit_performed'),
        'metadata_c1_port_keys': (md.get('c1_port') or {}).get('keys'),
        'lane_plant_manifest_sha256': md.get('lane_plant_manifest_sha256'),
        'head_normalisation_dropped': (md.get('lane_ramp_head_service_normalisation') or {}).get('dropped'),
        'block_greens': blocks, 'previous_greens_json': prev_js, 'previous_greens_csv': prev_csv,
        'previous_has_sdmpc_state': prev_has_state, 'tighten_meters_block0': tighten,
        'audit_selected': audit.get('selected'), 'audit_distinct_budget_incumbents': audit.get('distinct_budget_incumbents'),
        'audit_per_incumbent': per_inc, 'expected_from_p0_11': e,
        'floors': {m: (ramps.get(m) or {}).get('minimum_green_sec') for m in C.METERS} if ramps else None,
        'triggered': {m: (ramps.get(m) or {}).get('triggered') for m in C.METERS} if ramps else None,
        'fill_fraction': {m: [l.get('fill_fraction') for l in (ramps.get(m) or {}).get('lanes') or []] for m in C.METERS}
        if ramps else None,
        'cap_targets': [{k: c.get(k) for k in ('np_cap', 'nuf_target', 'status', 'feasible', 'objective')}
                        for c in (js.get('candidates') or []) if isinstance(c, dict)],
        'held': ({k: held.get(k) for k in ('evaluated', 'selected', 'budget_source', 'reference_source',
                                           'original_held_objective', 'additional_predictions')}
                 if isinstance(held, dict) else None),
        'held_objective': js.get('held_objective'), 'selected_objective': js.get('selected_objective'),
        'selection_status': js.get('selection_status'),
        'omega_model_veh_h': (js.get('omega_partition') or {}).get('total_veh_h'),
        'omega_kind': 'Omega701' if 'omega701' in ARMS[arm]['keys'] else 'Omega635',
        'leader_objective': md.get('leader_objective'), 'prediction_ttt_reduction': js.get('prediction_ttt_reduction'),
        'outw_veh_h_450': None,          # not in the decision JSON; OUTW is reported from the plant jobs (k92_record)
        'sg2_block0': sg_green(rd / ('action_%06d.csv' % st['T']), 'SC1001_SG2_W') if (rd / ('action_%06d.csv' % st['T'])).is_file() else None,
        'sg5_block0': sg_green(rd / ('action_%06d.csv' % st['T']), 'SC1001_SG5_W') if (rd / ('action_%06d.csv' % st['T'])).is_file() else None,
        'rollouts_total': (js.get('surrogate_query') or {}).get('total_rollouts') if isinstance(js.get('surrogate_query'), dict) else None,
        'compare': s.get('compare')}


def stage_report():
    C.lock_acquire('c1 probe report read', LOG)
    try:
        values = C.read_json(C.C1D / 'C1_VALUES.json') or {}
        exp = values.get('p0_11') or {}
        res = {'schema': 'c1-probe-results/v2', 'head': '탐침, 판정 아님', 'tree': PROBE.name,
               'patch_sha256': MAN['patch_sha256'], 'c1_values_sha256': C.sha256_file(C.C1D / 'C1_VALUES.json'),
               'halt': C.read_json(HALT), 'decisions': {}, 'plant': {}, 'stop_rules': {}}
        problems, incomplete = [], []
        tighten_any, walls_c1 = False, []
        for arm in DEC_ARMS:
            for st in STATES['probe_decisions_T900']:
                tag = dec_tag(st, arm)
                s = C.read_json(OUTP / 'dec' / (tag + '.summary.json'))
                if s is None:
                    incomplete.append('decision ' + tag)
                    continue
                row = decision_row(st, arm, s, exp)
                row.update(arm=arm, label=label_of(st['run']), kind=st['kind'], T=st['T'])
                res['decisions'][tag] = row
                if not row['ok']:
                    problems.append('decision %s replay_run=%s standing=%s infra=%s' % (
                        tag, s.get('replay_run'), s.get('standing'), s.get('infra_failure')))
                if arm in ('m', 'c1') and row['tighten_meters_block0']:
                    tighten_any = True
                if arm == 'c1' and isinstance(row['wall_sec'], (int, float)):
                    walls_c1.append(row['wall_sec'])
        stop2 = []
        for st in STATES['probe_plant_jobs']:
            seed, T = seed_of(st['run']), int(st['T'])
            rows = plant_state_rows(seed, T)
            key = '%s_t%06d' % (scode(st), T)
            res['plant'][key] = rows
            if all(r.get('missing') for r in rows.values()):
                incomplete.append('plant ' + key)
                continue
            for arm, r in rows.items():
                if r.get('missing') or not r.get('summary_present'):
                    incomplete.append('plant %s %s' % (key, arm))
                elif r.get('ok') is not True or r.get('k92_errors') or r.get('capture_failed') or not r.get('series_file'):
                    problems.append('plant %s %s ok=%s k92_errors=%s capture_failed=%s series=%s' % (
                        key, arm, r.get('ok'), r.get('k92_errors'), r.get('capture_failed'), r.get('series_file')))
                if arm != 'off' and r.get('trajectory_equal_off') is False:
                    stop2.append('%s %s: %s' % (key, arm, r.get('trajectory_detail')))
        med = statistics.median(walls_c1) if walls_c1 else None
        res['stop_rules'] = {
            '1_exception_or_invariant': problems,
            '2_omega_h_trajectory_differs': stop2,
            '3_no_tightening_in_m_c1_5_states': (not tighten_any) if not incomplete else None,
            '4_c1_wall_median_gt_1500': (med is not None and med > WALL_LIMIT) if len(walls_c1) == 5 else None,
            'c1_wall_median_sec': med, 'c1_wall_max_sec': max(walls_c1) if walls_c1 else None,
            'c1_walls_sec': walls_c1, 'incomplete': incomplete}
        fired = bool(problems) or bool(stop2) or bool(incomplete) or (not tighten_any) \
            or (med is not None and med > WALL_LIMIT) or bool(res['halt'])
        res['any_stop_or_ask'] = fired
        path = C.C1D / 'C1_PROBE_RESULTS.json'
        C.write_json(path, res)
        LOG('PROBE_REPORT written sha256=%s fired=%s' % (C.sha256_file(path), fired))
    finally:
        C.lock_release(LOG)


if __name__ == '__main__':
    C.set_below_normal()
    stage = sys.argv[1] if len(sys.argv) > 1 else ''
    LOG('PROBE start %s' % stage)
    {'decisions': stage_decisions, 'plant': stage_plant, 'report': stage_report}[stage]()
    LOG('PROBE end %s' % stage)
