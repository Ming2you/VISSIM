"""VerifyGates: reproduce the k92t f_persist failure mechanism without v3c3-s47: the same VR (TREE k92_vissim_ref.py,
f3fcc574) on v3c3-s43 state T=600 (window 600.1-750.1 s, below the U4 measurer T_FROM) and, as a control, T=1050.
Two separate VR calls (the VR exits at the first failing state).  Output root OK2/vg2t/vr600_* (new).  No VISSIM.
Prints rc and the last line of each call (s43 only, no s47 data).

    python -B vg_vr600.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
BELOW_NORMAL = 0x00004000
TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
SA = TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
VG = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vg2t')
A24 = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'


def run(tag, states):
    out = VG / ('vr600_%s' % tag)
    if out.exists():
        raise SystemExit('%s exists' % out)
    logp = VG / 'logs' / ('vr600_%s.log' % tag)
    logp.parent.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(TREE), K8G_OUT=str(out))
    t0 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([PY, '-B', str(SA / 'k92_vissim_ref.py'), '--root', str(TREE), '--out', str(out),
                             '--states', states, '--gates-stage', 'k92t', '--declaration-sha', A24],
                            cwd=str(SA), env=env, stdout=f, stderr=subprocess.STDOUT,
                            creationflags=BELOW_NORMAL).returncode
    lines = [x for x in open(logp, encoding='utf-8', errors='replace').read().splitlines() if x.strip()]
    rec = {'tag': tag, 'states': states, 'rc': rc, 'sec': round(time.time() - t0, 1), 'last_line': lines[-1] if lines else None,
           'output_file': (out / 'sa' / 'k92_vissim_ref.json').is_file()}
    print(json.dumps(rec), flush=True)
    with open(VG / 'vr600.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    return rec


def main():
    if not VG.is_dir():
        raise SystemExit('run vg_rerun.py first (%s)' % VG)
    run('s43_600', '43:600')
    run('s43_1050', '43:1050')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
