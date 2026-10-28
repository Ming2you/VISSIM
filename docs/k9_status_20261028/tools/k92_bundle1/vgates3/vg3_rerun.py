"""VerifyGates 2 — rerun of two representative k92t jobs in new output roots OK2/vg3t/<root> (the root name has the
length of 'k92t', so path strings keep their length).  Re-execution with the TREE's own harness (no judge):
  J  jb (SAF-K92b1) TL3_2250_SAF_OBS_H3 (v3c3-s31, T=2250; the J pair B job that J-b also reads)
  F  f_b1 (B1 arm)  TL3_3300_s43_SAF_OBS_H3 (v3c3-s43, F second sample; no v3c3-s47 job is rerun)
Each: inputs (byte copies as k92t prep_root: the three R-obs validity records of V4, J also V4 vissim_ref.json
e5e3466f), prep (prep.py for s31, sa_tl3m.py prep for s43), arms (sa_arms.py --k92b1 [--base-file the k92t BASE copy]),
capture (sa_capture.py tl3 SAF with the k92t stage token), job (this file's child: sa_jobs.base_job + run_job, the
same library call and env as the k92t driver child; the k92t driver itself is not run).  One child at a time,
BELOW_NORMAL, PYTHONHASHSEED=0, python -B.  No VISSIM / COM.  Writes only under OK2/vg3t.  Prints no value.

    python -B vg3_rerun.py run            (detached by vg3launch.ps1)
    python -B vg3_rerun.py child <spec>   (internal)"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vg3lib as V  # noqa: E402

PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
BELOW_NORMAL = 0x00004000
SA = V.TREE / V.SA_REL
VG = V.OK2 / 'vg3t'
A24 = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
STAGE = ['--gates-stage', 'k92t', '--declaration-sha', A24]
VREF_V4_SHA = 'e5e3466f960a88eef7a0f6f7f2379a89b61627ed366e165103025ae52ccffab0'
BASE_COPY = V.OUTK / 'inputs' / 'config_n31_v2_k91base.json'
BASE_SHA = '319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8'


def log(msg):
    line = '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line, flush=True)
    with open(VG / 'vg3_rerun.log', 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def vissim_count():
    try:
        r = subprocess.run([PS, '-NoProfile', '-Command', '@(Get-Process -Name VISSIM* -ErrorAction SilentlyContinue).Count'],
                           capture_output=True, text=True, timeout=120)
        return int(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


def env_for(root):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(V.TREE))
    if root is not None:
        env['K8G_OUT'] = str(root)
    return env


def step(name, argv, root, env_root=True):
    logp = VG / 'logs' / ('%s.log' % name)
    if logp.exists():
        raise SystemExit('log exists: %s' % logp)
    logp.parent.mkdir(parents=True, exist_ok=True)
    pre = vissim_count()
    t0 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([str(a) for a in argv], cwd=str(SA), env=env_for(root if env_root else None), stdout=f,
                            stderr=subprocess.STDOUT, creationflags=BELOW_NORMAL).returncode
    rec = {'name': name, 'rc': rc, 'start': t0, 'sec': round(time.time() - t0, 1), 'vissim_pre': pre,
           'vissim_post': vissim_count(), 'root': str(root), 'argv': [str(a) for a in argv]}
    with open(VG / 'steps.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    log('STEP %s rc=%s sec=%s vissim=%s/%s' % (name, rc, rec['sec'], pre, rec['vissim_post']))
    if rc != 0:
        raise SystemExit('step %s rc=%s' % (name, rc))


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
        src = V.V4 / 'sa' / 'tl3m' / ('robs_validity_s%d.json' % s)
        copy(src, root / 'sa' / 'tl3m' / src.name)
    if vref:
        copy(V.V4 / 'sa' / 'vissim_ref.json', root / 'sa' / 'vissim_ref.json', VREF_V4_SHA)


def tool(root, name, *args, stage=True, tree=True):
    argv = [V.PY, '-B', str(SA / name), '--root', str(V.TREE), '--out', str(root)]
    if tree:
        argv += ['--tree', V.LABEL]
    if stage:
        argv += STAGE
    return argv + [str(a) for a in args]


def child_step(name, root, item):
    spec = VG / 'specs' / ('%s.json' % name)
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(json.dumps({'items': [item]}, indent=1), encoding='utf-8')
    step(name, [V.PY, '-B', str(Path(__file__).resolve()), 'child', str(spec)], root, env_root=False)


def child(spec_path):
    """sa_jobs.base_job + run_job for each item (cwd = the TREE's sa folder)."""
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8'))
    sys.path.insert(0, str(SA))
    import sa_common as sc
    import sa_jobs
    c = sc.c
    for it in spec['items']:
        root, seed = Path(it['root']), int(it['seed'])
        robs = c.DEFAULT_ROBS if seed == 31 else c.DEFAULT_ROBS.parent / sc.ROBS_NAME.format(seed=seed)
        c.configure(root=str(V.TREE), out=str(root), robs=robs, nc3=c.NC3)
        args = SimpleNamespace(tree=V.LABEL, hooks=False, eo_root=str(sa_jobs.DEFAULT_EO), labels_only=False,
                               dry_run=False, plan_only=False, gates_stage='k92t', declaration_sha=A24, chain='site',
                               s3_table=None)
        job = sa_jobs.base_job(args, 'TL3', int(it['T']), it['arm'], it['entry'], int(it['H']), seed=seed,
                               variant='REF', mode='scalar')
        if job['label'] != it['label']:
            raise SystemExit('label %s != planned %s' % (job['label'], it['label']))
        sa_jobs.run_job(args, job)
        s = sc.read_json(sc.job_dir(V.LABEL, job['label']) / 'summary.json', {}) or {}
        print('VG3_JOB %s %s ok=%s' % (root.name, job['label'], s.get('ok')), flush=True)
    return 0


def run():
    if V.sha_file(BASE_COPY) != BASE_SHA:
        raise SystemExit('BASE copy sha differs')
    if VG.exists():
        raise SystemExit('%s exists' % VG)
    VG.mkdir(parents=True)
    log('VG3_RERUN start tree=%s' % V.TREE)
    rj = VG / 'jb'
    inputs(rj, vref=True)
    step('j_prep_s31', [V.PY, '-B', str(V.TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/prep.py'), '--root',
                        str(V.TREE), '--out', str(rj), '2250'], rj)
    step('j_arms', tool(rj, 'sa_arms.py', '--k92b1', '--base-file', BASE_COPY, stage=False, tree=False), rj)
    step('j_cap', tool(rj, 'sa_capture.py', 'tl3', 'SAF', 2250), rj)
    child_step('j_job', rj, {'root': str(rj), 'T': 2250, 'arm': 'SAF', 'entry': 'OBS', 'H': 3, 'seed': 31,
                             'label': 'TL3_2250_SAF_OBS_H3'})
    rf = VG / 'f_b1'
    inputs(rf, vref=False)
    step('f_prep_s43', tool(rf, 'sa_tl3m.py', 'prep', '--seed', 43, 3300, stage=False, tree=False), rf)
    step('f_arms', tool(rf, 'sa_arms.py', '--k92b1', stage=False, tree=False), rf)
    step('f_cap', tool(rf, 'sa_capture.py', '--robs-seed', 43, 'tl3', 'SAF', 3300), rf)
    child_step('f_job', rf, {'root': str(rf), 'T': 3300, 'arm': 'SAF', 'entry': 'OBS', 'H': 3, 'seed': 43,
                             'label': 'TL3_3300_s43_SAF_OBS_H3'})
    log('VG3_RERUN done')
    return 0


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'child':
        raise SystemExit(child(sys.argv[2]))
    if len(sys.argv) >= 2 and sys.argv[1] == 'run':
        raise SystemExit(run())
    print(__doc__)
    raise SystemExit(2)
