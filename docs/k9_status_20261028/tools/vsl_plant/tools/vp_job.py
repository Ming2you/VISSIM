"""One plant-probe job = one recorded V-A decision state (PRE_VP sections 3-5).  The caller (vp_queue.py) holds the
shared LOCK.  No VISSIM, no COM.

    python -B vp_job.py <mode A|P|S> <run name> <T> <spec.json> <job_dir>

1. The (run, T) pair must be in decl/VP_STATES.json (mode A: probe_A, P: p1, S: smoke).  Seed = run provenance.
2. Code root = GT/code_va (vp_tree.py verify record ok); tuning sha = the V-A tuning sha.
3. Replay bundle = gprep.py (sha pinned) copy of the decision state (state JSON, obs150 window + history, previous
   action + receipt) into <job_dir>/bundle; reused when its record is complete.
4. The adapter argument list and environment are those of k92_replay.py (FRZ_K92 k8_gates/sa, D-K9-99 form):
   provenance env (RW_*), PYTHONPATH = vp_hooks;<deps>\\sdmpc;<deps>\\sdmpc-numba, BLAS threads 1, PYTHONUTF8 1,
   PYTHONHASHSEED 0, NUMBA_NUM_THREADS removed, cwd = code root, python -B; the adapter is started through
   vp_probe.py (sdmpc.solve replaced), so no action file is written.
5. Watchdog: no change of the probe output / progress file for 45 min -> kill this job's own process tree only.
Writes <job_dir>/job_summary.json (exit codes, shas, check booleans; no plant value is printed)."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

STALL_SEC = 45 * 60


def rebase(p, run_root, root):
    if not p:
        return p
    full = os.path.abspath(p)
    base = os.path.abspath(run_root).rstrip('\\') + '\\'
    if full.lower().startswith(base.lower()):
        return os.path.join(str(root), full[len(base):])
    return p


def main():
    mode, run, T, spec_path, job_dir = sys.argv[1], sys.argv[2], int(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    C.blind_guard(run, job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    log = C.make_logger(job_dir / 'job.log')
    summary_path = job_dir / 'job_summary.json'
    states = C.read_json(C.DECL / 'VP_STATES.json')
    lists = {'A': states['probe_A'], 'P': states['p1'], 'S': [states['smoke']]}[mode]
    if not any(r['run'] == run and int(r['T']) == T for r in lists):
        raise SystemExit('state not declared for mode %s: %s T=%d' % (mode, run, T))
    run_dir = C.RUN_ROOTS['va'] / run
    seed, prov_path, prov_sha = C.provenance_seed(run_dir)
    want = [r for r in states['runs'] if r['run'] == run][0]
    if prov_sha != want['provenance_sha256'] or seed != want['seed_from_provenance']:
        raise SystemExit('run provenance differs from VP_STATES.json')
    tree = C.read_json(str(C.CODE) + '.tree.json') or {}
    if not tree.get('ok'):
        raise SystemExit('code copy not verified (vp_tree.py)')
    tuning = C.CODE / C.TUNING_REL
    if C.sha256_file(tuning) != C.TUNING_SHA:
        raise SystemExit('tuning sha differs')
    if C.sha256_file(C.GPREP) != C.GPREP_SHA:
        raise SystemExit('gprep.py sha differs')
    C.require_space(log)
    dec = run_dir / ('decisions_' + run)
    summary = {'schema': 'vp-job/1', 'mode': mode, 'run': run, 'label': 'v3c3-s%d' % seed, 'seed': seed, 'T': T,
               'spec_sha256': C.sha256_file(spec_path), 'started_kst': C.kst(), 'tree_freeze_sha': tree.get('freeze_sha256'),
               'probe_sha256': C.sha256_file(C.TOOLS / 'vp_probe.py'),
               'hook_sha256': C.sha256_file(C.TOOLS / 'vp_hooks' / 'sitecustomize.py')}
    numba = C.GT / 'numba_cache'
    env0 = C.child_env(numba)
    # ---- 3. bundle
    bundle = job_dir / 'bundle'
    rec_path = job_dir / 'bundle_record.json'
    rec = C.read_json(rec_path) or {}
    if not (rec.get('all_copies') and rec.get('state_obs150_directory_is_bundle')
            and rec.get('history_count') == rec.get('history_expected')):
        if bundle.exists():
            moved = job_dir / ('bundle_interrupted_%s' % time.strftime('%Y%m%d_%H%M%S'))
            bundle.rename(moved)
            log('MOVED_INTERRUPTED_BUNDLE ' + moved.name)
        rc, sec = C.run_capture([C.PY, '-B', str(C.GPREP), str(dec), str(T), str(bundle), str(rec_path)],
                                job_dir / 'gprep.txt', env0)
        rec = C.read_json(rec_path) or {}
        log('GPREP exit=%d sec=%.0f all_copies=%s bundle=%s history=%s/%s' % (
            rc, sec, rec.get('all_copies'), rec.get('state_obs150_directory_is_bundle'), rec.get('history_count'),
            rec.get('history_expected')))
        if rc != 0 or not rec.get('all_copies') or not rec.get('state_obs150_directory_is_bundle') \
                or rec.get('history_count') != rec.get('history_expected'):
            summary.update(infra_failure='bundle_failed', finished_kst=C.kst())
            C.write_json(summary_path, summary)
            return 6
    summary['bundle_manifest_sha256'] = rec.get('manifest_sha256')
    # ---- 4. adapter arguments (k92_replay.py form)
    m = C.read_json(bundle / 'replay_manifest.json')
    if m.get('schema') != 'sdmpc31-replay-state/v1' or int(m['sim_sec']) != T:
        raise SystemExit('bad replay manifest')
    prov = C.read_json(prov_path)
    run_root = prov['workspace_root']
    files = prov['files']
    mapping = rebase(files['control_mapping']['path'], run_root, C.CODE)
    calibration = rebase(files['calibration']['path'], run_root, C.CODE)
    runner_config = rebase(files['generated_vbs_config']['path'], run_root, C.CODE)
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    plan = C.read_json(run_dir / 'launch_plan.json')
    controller = plan['warmup_controller'] if T < int(plan['control_start_sec']) else plan['controller']
    prev = str(dec / ('action_%06d.json' % int(m['previous_sec'])))
    adapter = str(C.CODE / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    outd = job_dir / 'replay'
    outd.mkdir(parents=True, exist_ok=True)
    s6 = '%06d' % T
    a = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(outd / ('action_%s.json' % s6)),
         '--out-action-csv', str(outd / ('action_%s.csv' % s6)), '--mapping-json', mapping, '--controller', controller]
    if det:
        a += ['--detector-mapping-json', det]
    a += ['--calibration-json', calibration, '--tuning-json', str(tuning), '--previous-action-json', prev]
    amode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if amode:
        a += ['--mode', amode]
    hook_dir = job_dir / 'hooks'
    hook_dir.mkdir(parents=True, exist_ok=True)
    env = C.child_env(numba, hook_dir=hook_dir)
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = str(C.TOOLS / 'vp_hooks') + ';' + C.DEPROOT + r'\sdmpc;' + C.DEPROOT + r'\sdmpc-numba'
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1', PYTHONHASHSEED='0')
    env.pop('NUMBA_NUM_THREADS', None)
    probe_out = job_dir / 'probe.json'
    env.update(VP_SPEC=str(spec_path), VP_OUT=str(probe_out), VP_DEC=str(dec))
    summary.update(controller=controller, previous=prev, adapter_mode=amode, python=prov['env'].get('RW_PYTHON'))
    if probe_out.exists():
        moved = job_dir / ('probe_interrupted_%s.json' % time.strftime('%Y%m%d_%H%M%S'))
        probe_out.rename(moved)
        log('MOVED_INTERRUPTED_OUTPUT ' + moved.name)
    progress = probe_out.with_suffix('.progress.txt')
    log('PROBE_START mode=%s %s T=%d controller=%s' % (mode, summary['label'], T, controller))
    t0 = time.time()
    with open(job_dir / 'probe_stdout.txt', 'w', encoding='utf-8', errors='replace') as so, \
            open(job_dir / 'probe_stderr.txt', 'w', encoding='utf-8', errors='replace') as se:
        proc = subprocess.Popen([C.PY, '-B', str(C.TOOLS / 'vp_probe.py')] + a, cwd=str(C.CODE), env=env,
                                stdout=so, stderr=se, creationflags=C.BELOW_NORMAL)
        last, killed = time.time(), False
        while proc.poll() is None:
            time.sleep(20)
            for p in (probe_out, progress):
                try:
                    last = max(last, os.path.getmtime(p))
                except OSError:
                    pass
            if time.time() - last > STALL_SEC:
                log('STALL no progress for %ds: killing own PID tree %d' % (STALL_SEC, proc.pid))
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
                killed = True
                break
        rc = proc.wait()
    out = C.read_json(probe_out) or {}
    hooks = sorted(p.name for p in hook_dir.glob('vphook_*.json'))
    summary.update(exit_code=rc, wall_sec=round(time.time() - t0, 1), killed=killed,
                   probe_out_sha256=C.sha256_file(probe_out) if probe_out.is_file() else None,
                   probe_errors=out.get('errors'), stop=out.get('stop'),
                   checks={k: v for k, v in (out.get('checks') or {}).items() if isinstance(v, bool)},
                   hook_files=len(hooks), action_written=(outd / ('action_%s.json' % s6)).exists(),
                   finished_kst=C.kst())
    C.write_json(summary_path, summary)
    log('PROBE_END exit=%s wall=%.0f killed=%s errors=%s stop=%s checks=%s hooks=%d action_written=%s' % (
        rc, summary['wall_sec'], killed, out.get('errors'), out.get('stop'), summary['checks'], len(hooks),
        summary['action_written']))
    return rc


if __name__ == '__main__':
    sys.exit(main())
