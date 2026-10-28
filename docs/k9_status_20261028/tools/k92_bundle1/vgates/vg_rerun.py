"""VerifyGates rerun of two representative k92t jobs from scratch in new output roots (OK2/vg2t/<arm root>):
  J  = jb (SAF-K92b1) TL3_900_SAF_OBS_H3 (s31, T=900): the J-pair B job = the TL3 SAF job J-b would judge.
  F  = f_b1 (B1 arm) TL3_1050_s43_SAF_OBS_H3 (v3c3-s43, second sample; s47 primary states are not rerun - blind).
Each: inputs (byte copies of the V4 K9-1 inputs, as k92t.py prep_root), prep, arms, capture, job - the same harness
commands and env as KB/k92t/k92t.py (b07ffb56), one child at a time, BELOW_NORMAL, PYTHONHASHSEED=0, python -B.
The job runs through `k92t.py child <spec>` (the same library call base_job + run_job the k92t driver used).
The root name 'vg2t' has the length of 'k92t' so path strings stay the same length (vg_cmp.py substitutes it).
No VISSIM, no COM.  Writes only under OK2/vg2t.  Prints no value.

    python -B vg_rerun.py            (launched detached by vglaunch.ps1)
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BELOW_NORMAL = 0x00004000
HERE = Path(__file__).resolve().parent
KB = HERE.parent
TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
SA = TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
VG = OK2 / 'vg2t'
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
DRIVER = KB / 'k92t' / 'k92t.py'
DRIVER_SHA = 'b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec'
A24 = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
STAGE = ['--gates-stage', 'k92t', '--declaration-sha', A24]
VREF_V4_SHA = 'e5e3466f960a88eef7a0f6f7f2379a89b61627ed366e165103025ae52ccffab0'
BASE_COPY = OUTK / 'inputs' / 'config_n31_v2_k91base.json'
BASE_SHA = '319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8'
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    line = '%s %s' % (now(), msg)
    print(line, flush=True)
    with open(VG / 'vg_rerun.log', 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def vissim_count():
    try:
        out = subprocess.run([PS, '-NoProfile', '-Command',
                              '@(Get-Process -Name VISSIM* -ErrorAction SilentlyContinue).Count'],
                             capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


def env_for(root):
    """= k92t.py env_for: K8G_OUT only when the step has a root (the driver's child steps had root None)."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(TREE))
    if root is not None:
        env['K8G_OUT'] = str(root)
    return env


def step(name, argv, root, cwd=None, env_root='same'):
    logp = VG / 'logs' / ('%s.log' % name)
    if logp.exists():
        raise SystemExit('log exists: %s' % logp)
    logp.parent.mkdir(parents=True, exist_ok=True)
    pre = vissim_count()
    t0 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([str(a) for a in argv], cwd=str(cwd or SA), env=env_for(root if env_root == 'same' else None),
                            stdout=f,
                            stderr=subprocess.STDOUT, creationflags=BELOW_NORMAL).returncode
    rec = {'name': name, 'rc': rc, 'start': t0, 'sec': round(time.time() - t0, 1), 'vissim_pre': pre,
           'vissim_post': vissim_count(), 'root': str(root), 'argv': [str(a) for a in argv]}
    with open(VG / 'steps.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    log('STEP %s rc=%s sec=%s vissim=%s/%s' % (name, rc, rec['sec'], pre, rec['vissim_post']))
    if rc != 0:
        raise SystemExit('step %s rc=%s' % (name, rc))
    return rc


def copy(src, dst, want=None):
    if want and V.sha_file(src) != want:
        raise SystemExit('source sha differs %s' % src)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(V.lp(src), V.lp(dst))
    if V.sha_file(dst) != V.sha_file(src):
        raise SystemExit('copy differs %s' % dst)


def inputs(root, vref):
    root.mkdir(parents=True, exist_ok=False)
    for s in (31, 43, 47):
        src = V4 / 'sa' / 'tl3m' / ('robs_validity_s%d.json' % s)
        copy(src, root / 'sa' / 'tl3m' / src.name)
    if vref:
        copy(V4 / 'sa' / 'vissim_ref.json', root / 'sa' / 'vissim_ref.json', VREF_V4_SHA)


def tool(root, name, *args, stage=True, tree=True):
    argv = [PY, '-B', str(SA / name), '--root', str(TREE), '--out', str(root)]
    if tree:
        argv += ['--tree', 'k92t']
    if stage:
        argv += STAGE
    return argv + [str(a) for a in args]


def child(name, root, item):
    spec = VG / 'specs' / ('%s.json' % name)
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(json.dumps({'kind': 'jobs', 'items': [item]}, indent=1), encoding='utf-8')
    return step(name, [PY, '-B', str(DRIVER), 'child', str(spec)], root, env_root=None)   # k92t run_child: root None


def main():
    if V.sha_file(DRIVER) != DRIVER_SHA:
        raise SystemExit('driver sha differs')
    if V.sha_file(BASE_COPY) != BASE_SHA:
        raise SystemExit('BASE copy sha differs')
    if VG.exists():
        raise SystemExit('%s exists' % VG)
    VG.mkdir(parents=True)
    log('VG_RERUN start tree=%s' % TREE)
    # ---------------- J: jb TL3_900_SAF_OBS_H3
    rj = VG / 'jb'
    inputs(rj, vref=True)
    step('j_prep_s31', [PY, '-B', str(TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/prep.py'), '--root', str(TREE),
                        '--out', str(rj), '900'], rj)
    step('j_arms', tool(rj, 'sa_arms.py', '--k92b1', '--base-file', BASE_COPY, stage=False, tree=False), rj)
    step('j_cap', tool(rj, 'sa_capture.py', 'tl3', 'SAF', 900), rj)
    child('j_job', rj, {'root': str(rj), 'T': 900, 'arm': 'SAF', 'entry': 'OBS', 'H': 3, 'seed': 31,
                        'variant': 'REF', 'mode': 'scalar', 'label': 'TL3_900_SAF_OBS_H3'})
    # ---------------- F: f_b1 TL3_1050_s43_SAF_OBS_H3
    rf = VG / 'f_b1'
    inputs(rf, vref=False)
    step('f_prep_s43', tool(rf, 'sa_tl3m.py', 'prep', '--seed', 43, 1050, stage=False, tree=False), rf)
    step('f_arms', tool(rf, 'sa_arms.py', '--k92b1', stage=False, tree=False), rf)
    step('f_cap', tool(rf, 'sa_capture.py', '--robs-seed', 43, 'tl3', 'SAF', 1050), rf)
    child('f_job', rf, {'root': str(rf), 'T': 1050, 'arm': 'SAF', 'entry': 'OBS', 'H': 3, 'seed': 43,
                        'variant': 'REF', 'mode': 'scalar', 'label': 'TL3_1050_s43_SAF_OBS_H3'})
    log('VG_RERUN done')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
