"""K8 gate tools: shared roots, paths and child-process environment (diagnostics only; no runtime code).

Ported from the K8 scratch harness (scratchpad k8/tools/k8common.py, 2026-10-04). The scratch copy hard-coded its
code root (k8/r, a byte copy of FRZ_K7) and its output folder. Here both are arguments:

  code root    --root DIR / env K8G_ROOT   default: this worktree (k8_gates -> sdmpc_n31_20260924 -> diagnostics -> root)
  output root  --out DIR  / env K8G_OUT    default: DEFAULT_OUT; must lie outside the code root and outside this worktree
  R-obs run    --robs DIR / env K8G_ROBS   default: DEFAULT_ROBS (read only)
  NC runs      --nc3 DIR  / env K8G_NC3    default: DEFAULT_NC3 (read only; opt1v2 FZP/INPX inputs)
  python       env K8G_PY                  default: the interpreter running the tool
  sdmpc deps   env K8G_DEPS                default: DEFAULT_DEPS (PYTHONPATH of child processes)

The output layout mirrors the scratch folder, so `--root <k8>/r --out <k8>` addresses the scratch harness exactly:
  replays/<T>/          replay states (prep.py)
  out/<T>/...           captures, rollouts, full decisions, per-state analyses; out/an_*.json
  opt1v2/{data,out}/    FZP extracts and SC1001 EB recounts (opt1v2/*.py)
  tuning/               generated tuning variants (capture.py lgk)
  tmp/                  TEMP/TMP of child processes

    python -B k8common.py [--root R] [--out O] [--robs D] [--nc3 D] --print-config   (light: resolve and check paths)
    python -B k8common.py --print-out                                               (output root, for the chain*.sh)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

GATES = Path(__file__).resolve().parent
WORKTREE = GATES.parents[2]
TOOLS = GATES
SITE = GATES / 'site'
# Session default output folder (outside the repo). Override with --out or K8G_OUT.
DEFAULT_OUT = Path(r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----'
                   r'\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\gates_out')
DEFAULT_ROBS = Path(r'D:\VISSIM_runs\20261001_sdmpc31_v3c3\sdmpc31_v3c3_nc_s31')
DEFAULT_NC3 = Path(r'D:\VISSIM_runs\20261001_v3c3')
DEFAULT_DEPS = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
TUNING_REL = Path('diagnostics') / 'sdmpc_n31_20260924' / 'config_n31_v2.json'
ADAPTER_REL = Path('evaluation') / 'controllers' / 'vissim_stackelberg_adapter.py'
BELOW_NORMAL = 0x00004000

# set by configure()
R = OUT = RESULTS = REPLAYS = TMP = ROBS = DEC = NC3 = TUNING = ADAPTER = None
PY = DEPS = None


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def configure(root=None, out=None, robs=None, nc3=None):
    """Resolve the roots (argument > env > default), check them, export K8G_* for child processes."""
    global R, OUT, RESULTS, REPLAYS, TMP, ROBS, DEC, NC3, TUNING, ADAPTER, PY, DEPS
    R = Path(root or os.environ.get('K8G_ROOT') or WORKTREE).resolve()
    OUT = Path(out or os.environ.get('K8G_OUT') or DEFAULT_OUT).resolve()
    ROBS = Path(robs or os.environ.get('K8G_ROBS') or DEFAULT_ROBS)
    NC3 = Path(nc3 or os.environ.get('K8G_NC3') or DEFAULT_NC3)
    for repo in {R, WORKTREE.resolve()}:
        if _inside(OUT, repo):
            raise SystemExit(f'K8G output root {OUT} lies inside {repo}; keep gate outputs outside the repo (--out / K8G_OUT)')
    RESULTS = OUT / 'out'
    REPLAYS = OUT / 'replays'
    TMP = OUT / 'tmp'
    DEC = ROBS / f'decisions_{ROBS.name}'
    TUNING = R / TUNING_REL
    ADAPTER = R / ADAPTER_REL
    PY = os.environ.get('K8G_PY') or sys.executable
    DEPS = os.environ.get('K8G_DEPS') or DEFAULT_DEPS
    os.environ.update(K8G_ROOT=str(R), K8G_OUT=str(OUT), K8G_ROBS=str(ROBS), K8G_NC3=str(NC3))


def add_common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    g = parser.add_argument_group('K8 roots')
    g.add_argument('--root', help='code root (default: env K8G_ROOT, else this worktree)')
    g.add_argument('--out', help='output root outside the repo (default: env K8G_OUT, else %s)' % DEFAULT_OUT)
    g.add_argument('--robs', help='R-obs run folder, read only (default: env K8G_ROBS, else %s)' % DEFAULT_ROBS)
    return parser


def add_nc3(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument('--nc3', help='NC run root with s<seed>_v3c3nc folders, read only (default: env K8G_NC3, else %s)'
                        % DEFAULT_NC3)
    return parser


def parser(doc: str) -> argparse.ArgumentParser:
    return add_common(argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter))


def apply(args) -> None:
    configure(root=getattr(args, 'root', None), out=getattr(args, 'out', None), robs=getattr(args, 'robs', None),
              nc3=getattr(args, 'nc3', None))


def lower_priority():
    try:
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), BELOW_NORMAL)
    except Exception:
        pass


def provenance():
    return json.loads((ROBS / f'run_provenance_{ROBS.name}.json').read_text(encoding='utf-8-sig'))


def rebase(p):
    run_root = Path(provenance()['workspace_root'])
    try:
        return str(R / Path(p).relative_to(run_root))
    except ValueError:
        return str(p)


def base_env(extra=None, hook_dir=None):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_') and not k.upper().startswith('K8_')}
    env.pop('NUMBA_CACHE_DIR', None)     # numba cache next to the sources under the code root (gitignored __pycache__)
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', PYTHONUTF8='1', TMP=str(TMP), TEMP=str(TMP), K8_LONGPATH='1',
               PYTHONPATH=str(SITE) + ';' + DEPS + r'\sdmpc;' + DEPS + r'\sdmpc-numba',
               K8G_ROOT=str(R), K8G_OUT=str(OUT), K8G_ROBS=str(ROBS), K8G_NC3=str(NC3))
    env.update({k: str(v) for k, v in provenance()['env'].items()})
    if hook_dir:
        env['K8_HOOK_DIR'] = str(hook_dir)
    env.update(extra or {})
    return env


def adapter_args(replay_dir: Path, out_dir: Path, controller='wu-link', tuning=None):
    """replay_decision_n31.ps1 argument list (VBS:1114-1135), rebased onto the code root."""
    tuning = TUNING if tuning is None else tuning
    manifest = json.loads((replay_dir / 'replay_manifest.json').read_text(encoding='utf-8'))
    sec = int(manifest['sim_sec'])
    files = provenance()['files']
    runner_config = rebase(files['generated_vbs_config']['path'])
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if m:
            det = m.group(1)
    previous = None
    if manifest.get('previous_sec') is not None:
        previous = str(DEC / f'action_{int(manifest["previous_sec"]):06d}.json')
    args = ['--state-json', manifest['state']['replay'],
            '--out-action-json', str(out_dir / f'action_{sec:06d}.json'),
            '--out-action-csv', str(out_dir / f'action_{sec:06d}.csv'),
            '--mapping-json', rebase(files['control_mapping']['path']), '--controller', controller]
    if det:
        args += ['--detector-mapping-json', det]
    args += ['--calibration-json', rebase(files['calibration']['path']), '--tuning-json', str(tuning)]
    if previous:
        args += ['--previous-action-json', previous]
    return sec, args


def run(cmd, log, env, cwd=None):
    TMP.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log, 'w', encoding='utf-8') as out:
        proc = subprocess.run(cmd, cwd=str(cwd or R), env=env, stdout=out, stderr=subprocess.STDOUT,
                              creationflags=BELOW_NORMAL)
    return proc.returncode, round(time.time() - t0, 1)


def _sha16(p: Path):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def print_config():
    """Light self-check: resolved roots and existence of the inputs the tools read. Writes nothing."""
    rows = {'code_root': R, 'output_root': OUT, 'robs': ROBS, 'decisions': DEC, 'nc3': NC3, 'site': SITE,
            'python': PY, 'deps': DEPS, 'worktree_of_tools': WORKTREE}
    for k, v in rows.items():
        print(f'{k:18s} {v}')
    checks = {'adapter': ADAPTER, 'tuning': TUNING,
              'tangent_worker': R / 'evaluation' / 'controllers' / 'sdmpc_tangent_worker.py',
              'numsim_vendor': R / 'vendor' / 'NumSim-mine' / 'src',
              'make_replay_state_v2': R / 'diagnostics' / 'sdmpc_n31_20260924' / 'tools' / 'make_replay_state_v2.py',
              'provenance': ROBS / f'run_provenance_{ROBS.name}.json', 'decisions_dir': DEC,
              'deps_sdmpc': Path(DEPS) / 'sdmpc', 'deps_sdmpc_numba': Path(DEPS) / 'sdmpc-numba',
              'sitecustomize': SITE / 'sitecustomize.py'}
    bad = 0
    for k, p in checks.items():
        ok = Path(p).exists()
        bad += not ok
        print(f'{"ok " if ok else "MISSING"} {k:22s} {p}')
    if TUNING.is_file():
        print(f'tuning sha16 {_sha16(TUNING)}')
    try:
        files = provenance()['files']
        for key in ('generated_vbs_config', 'control_mapping', 'calibration'):
            p = Path(rebase(files[key]['path']))
            ok = p.is_file()
            bad += not ok
            print(f'{"ok " if ok else "MISSING"} rebased:{key:15s} {p}')
    except Exception as exc:
        bad += 1
        print('provenance error', repr(exc))
    print('CONFIG_OK' if bad == 0 else f'CONFIG_MISSING {bad}')
    return 0 if bad == 0 else 1


configure()

if __name__ == '__main__':
    ap = add_nc3(parser(__doc__))
    ap.add_argument('--print-config', action='store_true', help='print resolved roots and check inputs (writes nothing)')
    ap.add_argument('--print-out', action='store_true', help='print the output root (forward slashes) and exit')
    a = ap.parse_args()
    apply(a)
    if a.print_out:
        print(OUT.as_posix())
        raise SystemExit(0)
    raise SystemExit(print_config())
