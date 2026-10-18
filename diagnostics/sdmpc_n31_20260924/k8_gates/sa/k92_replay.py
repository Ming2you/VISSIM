"""K9-2 bundle 1 decision replay launcher with an explicit tuning file (K8_PREDECLARATION_AMENDMENT_24 sections 2.0-6,
4.3 G-K0 D-d / G-K1).  Diagnostics only; no VISSIM.  It does what tools/replay_decision_n31.ps1 (5d34109f...) does --
the same adapter argument list (VBS:1114-1135), the run's provenance env with RW_* cleared, PYTHONPATH
[ExtraPythonPath;]DepRoot\\sdmpc;DepRoot\\sdmpc-numba, OMP / OPENBLAS / MKL threads 1, PYTHONUTF8 1, cwd = Root,
python -B, then make_replay_state_v2.py compare --tuning -- with one difference: --tuning-json is the given file
instead of the rebased run tuning, so a code root (GWT8 at a commit) replays a state with that state's own run tuning
bytes (section 2.0-6) or an arm tuning without a per-arm tree copy.

    python -B k92_replay.py --replay-dir D --root R --tuning T [--controller C] [--extra-pythonpath P]
                            [--dep-root X] [--no-compare]
Writes D/replay/{action_<T>.json, .csv, adapter_stdout.txt, adapter_stderr.txt, replay_run.json} like the ps1 and prints
REPLAY_<T> exit=<rc> wall_sec=<s>, REPLAY_CHECK lines of the compare (no value).  Exit 0 identical, 1 adapter failed,
2 differs, 3 refused (the ps1 codes)."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DEP_ROOT = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'


def refuse(why):
    print('REPLAY_REFUSED ' + why, flush=True)
    sys.exit(3)


def rebase(p, run_root, root):
    if not p:
        return p
    full = os.path.abspath(p)
    base = os.path.abspath(run_root).rstrip('\\') + '\\'
    if full.lower().startswith(base.lower()):
        return os.path.join(str(root), full[len(base):])
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--replay-dir', required=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--tuning', required=True)
    ap.add_argument('--controller', default='')
    ap.add_argument('--extra-pythonpath', default='')
    ap.add_argument('--dep-root', default=DEP_ROOT)
    ap.add_argument('--no-compare', action='store_true')
    args = ap.parse_args()
    rd = Path(os.path.abspath(args.replay_dir))
    root = Path(os.path.abspath(args.root))
    m = json.loads((rd / 'replay_manifest.json').read_text(encoding='utf-8-sig'))
    if m.get('schema') != 'sdmpc31-replay-state/v1':
        refuse('unsupported replay manifest schema %s' % m.get('schema'))
    sec = int(m['sim_sec'])
    s6 = '%06d' % sec
    dec = Path(m['source_decisions'])
    run_dir = dec.parent
    run_name = re.sub(r'^decisions_', '', dec.name)
    prov = json.loads((run_dir / ('run_provenance_%s.json' % run_name)).read_text(encoding='utf-8-sig'))
    run_root = prov['workspace_root']
    prev = None
    if m.get('previous_sec') is not None:
        prev = str(dec / ('action_%06d.json' % int(m['previous_sec'])))
        for _k, v in (m.get('evidence', {}).get('previous') or {}).items():
            import hashlib
            src = v['source']
            if not Path(src).is_file():
                refuse('previous action file vanished: ' + src)
            if hashlib.sha256(Path(src).read_bytes()).hexdigest() != v['sha256']:
                refuse('previous action file changed since prepare: ' + src)
        if not Path(prev).is_file():
            refuse('previous action missing: ' + prev)
    controller = args.controller
    if not controller:
        plan = json.loads((run_dir / 'launch_plan.json').read_text(encoding='utf-8-sig'))
        controller = plan['warmup_controller'] if sec < int(plan['control_start_sec']) else plan['controller']
    files = prov['files']
    mapping = rebase(files['control_mapping']['path'], run_root, root)
    calibration = rebase(files['calibration']['path'], run_root, root)
    runner_config = rebase(files['generated_vbs_config']['path'], run_root, root)
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    adapter = str(root / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    tuning = os.path.abspath(args.tuning)
    for f in (tuning, mapping, calibration, adapter):
        if not Path(f).is_file():
            refuse('missing input: ' + f)
    out = rd / 'replay'
    if (out / ('action_%s.json' % s6)).exists():
        refuse('replay output already exists in %s (prepare a new ReplayDir)' % out)
    out.mkdir(parents=True, exist_ok=True)
    a = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(out / ('action_%s.json' % s6)),
         '--out-action-csv', str(out / ('action_%s.csv' % s6)), '--mapping-json', mapping, '--controller', controller]
    if det:
        a += ['--detector-mapping-json', det]
    a += ['--calibration-json', calibration, '--tuning-json', tuning]
    if prev:
        a += ['--previous-action-json', prev]
    mode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if mode:
        a += ['--mode', mode]
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_')}
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = args.dep_root + r'\sdmpc;' + args.dep_root + r'\sdmpc-numba'
    if args.extra_pythonpath:
        env['PYTHONPATH'] = args.extra_pythonpath + ';' + env['PYTHONPATH']
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
    python = str(prov['env'].get('RW_PYTHON') or '')
    if not python:
        refuse('provenance env lacks RW_PYTHON')
    print('REPLAY_START sim_sec=%d controller=%s root=%s previous=%s tuning=%s' % (sec, controller, root, prev or '-',
                                                                                  tuning), flush=True)
    t0 = time.time()
    with open(out / 'adapter_stdout.txt', 'w', encoding='utf-8', errors='replace') as so, \
            open(out / 'adapter_stderr.txt', 'w', encoding='utf-8', errors='replace') as se:
        rc = subprocess.run([python, '-B'] + a, cwd=str(root), env=env, stdout=so, stderr=se).returncode
    wall = round(time.time() - t0, 1)
    rec = {'schema': 'sdmpc31-replay-run/v1', 'sim_sec': sec, 'controller': controller, 'root': str(root),
           'run_root': run_root, 'rebased': os.path.abspath(run_root).lower() != str(root).lower(), 'python': python,
           'arguments': a, 'env': prov['env'], 'exit_code': rc, 'wall_sec': wall, 'launcher': 'k92_replay.py',
           'tuning_override': tuning}
    (out / 'replay_run.json').write_text(json.dumps(rec, indent=2), encoding='utf-8')
    print('REPLAY_%s exit=%d wall_sec=%s' % (s6, rc, wall), flush=True)
    if rc != 0:
        sys.exit(1)
    if args.no_compare:
        sys.exit(0)
    comp = subprocess.run([python, '-B', str(Path(__file__).resolve().parents[2] / 'tools' / 'make_replay_state_v2.py'),
                           'compare', str(rd), '--tuning', tuning], capture_output=True, text=True, env=env,
                          encoding='utf-8', errors='replace')
    for line in comp.stdout.splitlines():
        print(line, flush=True)
    sys.exit(0 if comp.returncode == 0 else 2)


if __name__ == '__main__':
    main()
