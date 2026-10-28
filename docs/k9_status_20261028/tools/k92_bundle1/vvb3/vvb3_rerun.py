"""VerifyVB 3 -- re-run of one short V-B chain segment (2 decisions) in a separate scratch place, then a bit-identity
check against the V-B outputs.  Verification scratch tool, never committed.  One detached run (vvb3_launch.ps1).

Declared BEFORE any V-B output is read (pinned in KB/LOG.md):
  segment  = chain VB-41, arm B1 (tuning VBR/arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json,
             read only), T1 = 3,300 with previous action = the V-B output VBR/chain/vb41_b1/dec/action_003150.json
             (read only, the same file the V-B decision read), then T2 = 3,450 with previous action = the T1 output of
             this rerun (+ its runner receipt written by the amendment-32 rule: only when .sdmpc_pending exists,
             UTF-16 LE + BOM, CRLF, lines T / CSV path / CSV size).  Hook ON (AD33/vbhook, read only), as in V-B.
  tree     = TK/vvb3_e27ceac8 = git archive e27ceac8 (GWT8, read only) + CR fix (FRZ_K8b bytes of the files in
             TK/cr_only_files.json, only where the blob at e27ceac8 = the blob at b9734abe); it must equal the V-B
             tree TK/vb2_e27ceac8 file by file outside cache folders (__pycache__, __tangentcache__, .pytest_cache).
  outputs  = OK2/vvb3/chain/vb41_b1/{prep,dec,hook,rec}/... (the V-B layout under OK2/vvb3 instead of OK2/vb2).
  launch   = the amendment-32 section 4.3 rule (k92_replay.py 822dd78f form) rebuilt here; the argv must equal the
             V-B run record's argv after the two place substitutions (tree root, OK2/vb2 -> OK2/vvb3).
  identity rule (R-ID):
    T1  CSV bytes equal AND vvb3_recalc.compare_dec(V-B dec, rerun dec, 3300, new_root = rerun tree, old_root = VBT)
        verdict = PASS (amendment 21 section 6 rules, the VB-I1 rules; differences allowed only as V / R3 / F1-F3).
    T2  CSV bytes equal AND the same comparison with the rerun side's 'k92_b1/vvb3/' text read as 'k92_b1/vb2/'
        (after N) gives HARD H1-H5 equal and 0 unclassified, where only these leaves may differ beyond V / R3 / F:
          (a) /metadata/sdmpc_state/previous_application/receipt_sha256 and
              /metadata/joint_leader_selection/price_state/previous_application/receipt_sha256:
              old value = sha256 of V-B T1 receipt, new value = sha256 of the rerun T1 receipt;
          (b) /metadata/n31_binding/vsl_cohort_initialization/sha256: old = sha256 of V-B T1 JSON, new = sha256 of
              the rerun T1 JSON;
          (c) any leaf whose last name ends with action_token (D1; pickled action objects holding the previous
              action's paths -- amendment 33 section 9).
    Anything else -> "not identical" (reported, STOP for the user).
  report only: hook selection status / candidate count / match count vs V-B; the chosen record vs V-B record.
  guards: free space >= 8 GB on C: and D:, no VISSIM; the V-B files read (T=3,150 previous trio, the V-B
  vb41_b1 dec / hook / rec listings) and the RR s41 decisions listing must be unchanged afterwards.

    python -B vvb3_rerun.py run      (detached)
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vvb3_recalc as R  # noqa: E402  (own pinned tool)

GWT8 = Path(r'D:/VISSIM-merge/sim3-n31-k8')
REV = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
K8REV = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
TK = R.TK
VBT = R.VBT
MYT = TK / 'vvb3_e27ceac8'
MYT_BUILD = TK / 'vvb3_e27ceac8.build.json'
CR_LIST = TK / 'cr_only_files.json'
FRZ8B = R.FRZ8B
OK2 = R.OK2
VBR = R.VBR
MYR = OK2 / 'vvb3'
RUN = 'sdmpc31_v3c3_k8j1_s41'
RRD = R.RR / RUN / ('decisions_' + RUN)
VCD = VBR / 'chain' / 'vb41_b1'
MCD = MYR / 'chain' / 'vb41_b1'
TUNING = VBR / 'arms' / 'sa' / 'tuning' / 'config_n31_v2_stopline_observed_full_k91_k92b1.json'
TUNING_SHA = R.SAF_B1_SHA
T1, T2, TPREV = 3300, 3450, 3150
SEED = 41
SPK = R.SPK
HOOKDIR = SPK / 'k92' / 'bundle1' / 'a33decl' / 'vbhook'
HOOK_SHA = '691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c'
REC_REL = R.N31 + '/k8_gates/sa/k92_record.py'
REC_SHA = '1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90'
GPREP = SPK / 'j1' / 'fix' / 'gates' / 'gprep.py'
GPREP_SHA = '0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
DEP = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
BELOW_NORMAL = 0x00004000
STALL = 30 * 60
CACHE = ('__pycache__', '__tangentcache__', '.pytest_cache')
SUB_TREE = ('d:/vissim-merge/k8_gate_trees/k92b1/vvb3_e27ceac8', 'd:/vissim-merge/k8_gate_trees/k92b1/vb2_e27ceac8')
SUB_OUT = ('/k92_b1/vvb3/', '/k92_b1/vb2/')
LOG = []


def log(msg):
    line = '%s %s' % (time.strftime('%Y-%m-%dT%H:%M:%S'), msg)
    LOG.append(line)
    print(line, flush=True)
    MYR.mkdir(parents=True, exist_ok=True)
    with open(MYR / 'rerun_log.txt', 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def set_below_normal():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, BELOW_NORMAL)
    return k.GetPriorityClass(h) == BELOW_NORMAL


def free_gb():
    return {d[0]: round(shutil.disk_usage(d).free / 1e9, 2) for d in ('C:\\', 'D:\\')}


def vissim_n():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout
    return sum(1 for line in out.splitlines() if line.lower().startswith('vissim'))


def lst(root):
    rows = []
    base = R.lp(root)
    for d, dirs, names in os.walk(base):
        dirs.sort()
        rel = os.path.relpath(d, base).replace('\\', '/')
        for n in sorted(names):
            st = os.stat(os.path.join(d, n))
            rows.append([rel + '/' + n, st.st_size, round(st.st_mtime, 6)])
    return {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest()}


def git(*a):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(GWT8)] + list(a), capture_output=True, text=True,
                          check=True).stdout


# ------------------------------------------------------------------------------------------------ tree
def tree_files(root):
    out = {}
    base = R.lp(root)
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x not in CACHE)
        for n in names:
            p = os.path.join(d, n)
            out[os.path.relpath(p, base).replace('\\', '/')] = p
    return out


def build_tree():
    if MYT.exists() or MYT_BUILD.exists():
        raise SystemExit('rerun tree exists (never reused): %s' % MYT)
    t0 = time.time()
    p = subprocess.Popen(['git', '--no-optional-locks', '-C', str(GWT8), 'archive', '--format=tar', REV],
                         stdout=subprocess.PIPE)
    n = 0
    with tarfile.open(fileobj=p.stdout, mode='r|') as tf:
        for m in tf:
            target = R.lp(os.path.join(str(MYT), m.name.replace('/', os.sep)))
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            if m.issym():
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as out:
                out.write(tf.extractfile(m).read())
            n += 1
    if p.wait() != 0:
        raise SystemExit('git archive failed')
    cr = json.loads(CR_LIST.read_text(encoding='utf-8'))['files']
    cr_done = []
    for rel in cr:
        a = git('rev-parse', '%s:%s' % (REV, rel)).strip()
        b = git('rev-parse', '%s:%s' % (K8REV, rel)).strip()
        if a != b:
            raise SystemExit('CR rule does not apply to %s' % rel)
        (MYT / rel).write_bytes((FRZ8B / rel).read_bytes())
        cr_done.append([rel, R.fsha(MYT / rel)])
    mine, theirs = tree_files(MYT), tree_files(VBT)
    only_mine = sorted(set(mine) - set(theirs))
    only_vbt = sorted(set(theirs) - set(mine))
    differ = [rel for rel in sorted(set(mine) & set(theirs)) if R.fsha(mine[rel]) != R.fsha(theirs[rel])]
    rec = {'tree': str(MYT), 'rev': REV, 'archive_files': n, 'cr_fix': cr_done, 'files_mine': len(mine),
           'files_vbt_outside_cache': len(theirs), 'only_mine': only_mine[:50], 'only_vbt': only_vbt[:50],
           'differ': differ[:50], 'equal_to_vbt': not only_mine and not only_vbt and not differ,
           'rs_sha256': R.fsha(MYT / R.RS_REL), 'rec_sha256': R.fsha(MYT / REC_REL), 'sec': round(time.time() - t0, 1),
           'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    MYT_BUILD.write_text(json.dumps(rec, indent=1), encoding='utf-8')
    log('TREE files=%d equal_to_vbt=%s only_mine=%d only_vbt=%d differ=%d sec=%s' % (
        n, rec['equal_to_vbt'], len(only_mine), len(only_vbt), len(differ), rec['sec']))
    return rec


# ------------------------------------------------------------------------------------------------ launch (32 4.3)
def rebase(p, run_root, root):
    if not p:
        return p
    full = os.path.abspath(p)
    base = os.path.abspath(run_root).rstrip('\\') + '\\'
    if full.lower().startswith(base.lower()):
        return os.path.join(str(root), full[len(base):])
    return p


def launch_spec(prep, out_json, out_csv, prev, hook_dir, T, label):
    prep = Path(os.path.abspath(prep))
    m = json.loads((prep / 'replay_manifest.json').read_text(encoding='utf-8-sig'))
    if m.get('schema') != 'sdmpc31-replay-state/v1':
        raise SystemExit('manifest schema')
    sec = int(m['sim_sec'])
    dec = Path(m['source_decisions'])
    run_dir = dec.parent
    run_name = re.sub(r'^decisions_', '', dec.name)
    prov = json.loads((run_dir / ('run_provenance_%s.json' % run_name)).read_text(encoding='utf-8-sig'))
    for _k, v in (m.get('evidence', {}).get('previous') or {}).items():
        if R.fsha(v['source']) != v['sha256']:
            raise SystemExit('record previous changed since prepare')
    if m.get('previous_sec') is None or not Path(prev).is_file():
        raise SystemExit('previous action missing')
    plan = json.loads((run_dir / 'launch_plan.json').read_text(encoding='utf-8-sig'))
    controller = plan['warmup_controller'] if sec < int(plan['control_start_sec']) else plan['controller']
    files, run_root = prov['files'], prov['workspace_root']
    mapping = rebase(files['control_mapping']['path'], run_root, MYT)
    calibration = rebase(files['calibration']['path'], run_root, MYT)
    runner_cfg = rebase(files['generated_vbs_config']['path'], run_root, MYT)
    det = ''
    for line in Path(runner_cfg).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    adapter = str(MYT / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    argv_tail = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(out_json),
                 '--out-action-csv', str(out_csv), '--mapping-json', mapping, '--controller', controller]
    if det:
        argv_tail += ['--detector-mapping-json', det]
    argv_tail += ['--calibration-json', calibration, '--tuning-json', os.path.abspath(str(TUNING)),
                  '--previous-action-json', str(prev)]
    mode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if mode:
        argv_tail += ['--mode', mode]
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'S31F_', 'GH1_', 'K92A_', 'K92VB_'))}
    env.update({'NUMBA_CACHE_DIR': str(MYR / 'numba_cache'), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'})
    env.pop('NUMBA_NUM_THREADS', None)
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = str(HOOKDIR) + ';' + DEP + r'\sdmpc;' + DEP + r'\sdmpc-numba'
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
    env.update({'K92VB_HOOK_DIR': str(hook_dir), 'K92VB_RECORDER': str(MYT / REC_REL), 'K92VB_RECORDER_SHA256': REC_SHA,
                'K92VB_T': str(int(T)), 'K92VB_SEED': str(SEED), 'K92VB_LABEL': label})
    python = str(prov['env'].get('RW_PYTHON') or '')
    return {'argv': [python, '-B'] + argv_tail, 'cwd': str(MYT), 'env': env, 'controller': controller}


def canon(s):
    s = str(s).replace('\\', '/').lower()
    s = s.replace(SUB_TREE[0], SUB_TREE[1])
    return s.replace(SUB_OUT[0], SUB_OUT[1])


def run_one(T, prev, label):
    s = R.t6(T)
    P = {'prep': MCD / 'prep' / ('t' + s), 'prep_rec': MCD / 'prep' / ('t%s.prep.json' % s),
         'dec': MCD / 'dec', 'hook': MCD / 'hook' / ('t' + s), 'rec': MCD / 'rec' / ('t' + s)}
    for k in ('prep', 'hook', 'rec'):
        if P[k].exists():
            raise SystemExit('exists (never reused): %s' % P[k])
    oj, oc = P['dec'] / ('action_%s.json' % s), P['dec'] / ('action_%s.csv' % s)
    if oj.exists() or oc.exists():
        raise SystemExit('output exists: %s' % oj)
    fg = free_gb()
    if any(v < 8.0 for v in fg.values()) or vissim_n() != 0:
        raise SystemExit('guard: free %s vissim %s' % (fg, vissim_n()))
    P['prep'].parent.mkdir(parents=True, exist_ok=True)
    if R.fsha(GPREP) != GPREP_SHA:
        raise SystemExit('gprep differs')
    env0 = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_', 'K92VB_'))}
    env0.pop('PYTHONPATH', None)
    env0.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    with open(MCD / 'prep' / ('t%s.prepare.txt' % s), 'w', encoding='utf-8') as fo:
        rc = subprocess.run([PY, '-B', str(GPREP), str(RRD), str(T), str(P['prep']), str(P['prep_rec'])],
                            cwd=str(GPREP.parent), env=env0, stdout=fo, stderr=subprocess.STDOUT,
                            creationflags=BELOW_NORMAL).returncode
    pr = R.jload(P['prep_rec']) or {}
    prep_ok = rc == 0 and pr.get('all_copies') and pr.get('state_obs150_directory_is_bundle') and \
        pr.get('history_count') == pr.get('history_expected')
    log('PREP T=%d rc=%s ok=%s' % (T, rc, prep_ok))
    if not prep_ok:
        raise SystemExit('prepare failed T=%d' % T)
    P['hook'].parent.mkdir(parents=True, exist_ok=True)
    P['hook'].mkdir()
    P['dec'].mkdir(parents=True, exist_ok=True)
    spec = launch_spec(P['prep'], oj, oc, prev, P['hook'], T, label)
    vrun = R.jload(VCD / 'dec' / ('run_t%s.json' % s)) or {}
    argv_same = [canon(x) for x in spec['argv']] == [canon(x) for x in (vrun.get('argv') or [])]
    vset = ((vrun.get('env') or {}).get('set') or {})
    set_keys = sorted(vset)
    set_same = {k: canon(spec['env'].get(k)) == canon(vset.get(k)) for k in set_keys}
    names_mine, names_v = sorted(spec['env']), sorted((vrun.get('env') or {}).get('names') or [])
    launch_check = {'argv_same_after_subst': argv_same, 'env_set_same': set_same,
                    'env_names_only_mine': sorted(set(names_mine) - set(names_v)),
                    'env_names_only_vb': sorted(set(names_v) - set(names_mine)),
                    'controller': spec['controller'], 'vb_controller': vrun.get('controller')}
    log('LAUNCH T=%d argv_same=%s env_set_same=%s names_only_mine=%d names_only_vb=%d' % (
        T, argv_same, all(set_same.values()), len(launch_check['env_names_only_mine']),
        len(launch_check['env_names_only_vb'])))
    if not argv_same or not all(set_same.values()):
        raise SystemExit('launch differs from the V-B run record (T=%d): %s' % (T, launch_check))
    stem = 'action_%s' % s
    prog = P['dec'] / (stem + '.joint.progress.jsonl')
    t0 = time.perf_counter()
    killed = None
    with open(P['dec'] / (stem + '.stdout.txt'), 'w', encoding='utf-8') as so, \
            open(P['dec'] / (stem + '.stderr.txt'), 'w', encoding='utf-8') as se:
        proc = subprocess.Popen(spec['argv'], cwd=spec['cwd'], env=spec['env'], stdout=so, stderr=se,
                                creationflags=BELOW_NORMAL)
        last, changed = -1, time.perf_counter()
        while True:
            try:
                rc = proc.wait(timeout=30)
                break
            except subprocess.TimeoutExpired:
                pass
            sz = prog.stat().st_size if prog.is_file() else -1
            if sz != last:
                last, changed = sz, time.perf_counter()
            if time.perf_counter() - changed > STALL:
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], capture_output=True)
                killed = proc.pid
                rc = proc.wait()
                break
    wall = round(time.perf_counter() - t0, 1)
    log('RUN T=%d exit=%s wall=%s killed=%s pid=%s' % (T, rc, wall, killed, proc.pid))
    if rc != 0 or killed:
        raise SystemExit('adapter failed T=%d rc=%s killed=%s' % (T, rc, killed))
    receipt = None
    if Path(str(oj) + '.sdmpc_pending').is_file():
        data = b'\xff\xfe' + ('%d\r\n%s\r\n%d\r\n' % (T, str(oc), oc.stat().st_size)).encode('utf-16-le')
        tgt = Path(str(oj) + '.applied')
        if tgt.exists():
            raise SystemExit('receipt exists')
        tgt.write_bytes(data)
        receipt = {'path': str(tgt), 'sha256': hashlib.sha256(data).hexdigest()}
    doc = R.jload(oj) or {}
    sel = R.reselect(P['hook'], doc, T)
    del doc
    P['rec'].mkdir(parents=True)
    (P['rec'] / 'vvb3_select.json').write_text(json.dumps(sel, indent=1, default=str), encoding='utf-8')
    rec = {'T': T, 'prev': str(prev), 'exit': rc, 'wall_sec': wall, 'receipt': receipt, 'launch_check': launch_check,
           'json_sha256': R.fsha(oj), 'csv_sha256': R.fsha(oc), 'select': {k: sel[k] for k in (
               'status', 'n_candidates', 'n_match')}, 'chosen': sel['chosen']}
    (P['dec'] / ('vvb3_run_t%s.json' % s)).write_text(json.dumps(rec, indent=1, default=str), encoding='utf-8')
    return rec, P


def identity(T, Pm, post, extra):
    s = R.t6(T)
    rep = R.compare_dec(VCD / 'dec', Pm['dec'], T, MYT, VBT, post_new=post, extra_allow=extra)
    vsel = R.jload(VCD / 'rec' / ('t' + s) / 'k92_select.json') or {}
    msel = R.jload(Pm['rec'] / 'vvb3_select.json') or {}
    out = {'T': T, 'verdict': rep['verdict'], 'csv_same': rep.get('csv_same'), 'hard': rep.get('hard'),
           'unclassified_n': rep.get('unclassified_n'), 'unclassified': rep.get('unclassified'),
           'allowed': rep.get('allowed'), 'extra_allowed': rep.get('extra_allowed'), 'n_diff_total': rep.get(
               'n_diff_total'), 'n_wallclock': rep.get('n_wallclock'),
           'select_vb': {k: vsel.get(k) for k in ('status', 'n_candidates', 'n_match')},
           'select_rerun': {k: msel.get(k) for k in ('status', 'n_candidates', 'n_match')}}
    if vsel.get('status') == 'selected' and msel.get('status') == 'selected':
        a = R.jload(VCD / 'rec' / ('t' + s) / 'k92_record.json') or {}
        b = R.jload(Pm['hook'] / msel['chosen']['folder'] / 'k92_record.json') or {}
        out['chosen_record_blocks_horizon_equal_1e12'] = R.near(a.get('blocks'), b.get('blocks'), 1e-12) and \
            R.near(a.get('horizon'), b.get('horizon'), 1e-12)
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'run':
        print(__doc__)
        return 2
    res = {'tool_sha256': R.fsha(__file__), 'recalc_tool_sha256': R.fsha(R.__file__), 'below_normal': set_below_normal(),
           'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    if (MYR / 'rerun.json').exists():
        raise SystemExit('rerun.json exists')
    MYR.mkdir(parents=True, exist_ok=True)
    log('START tool=%s below_normal=%s free=%s vissim=%d' % (res['tool_sha256'][:16], res['below_normal'], free_gb(),
                                                              vissim_n()))
    for f, w in ((HOOKDIR / 'sitecustomize.py', HOOK_SHA), (TUNING, TUNING_SHA), (GPREP, GPREP_SHA)):
        if R.fsha(f) != w:
            raise SystemExit('pinned input differs: %s' % f)
    if sorted(p.name for p in HOOKDIR.iterdir()) != ['sitecustomize.py']:
        raise SystemExit('HOOKDIR holds more than the hook')
    prev_trio = [VCD / 'dec' / ('action_%s%s' % (R.t6(TPREV), x)) for x in ('.json', '.csv', '.json.applied')]
    t1_trio = [VCD / 'dec' / ('action_%s%s' % (R.t6(T1), x)) for x in ('.json', '.csv', '.json.applied')]
    before = {'prev_trio': [R.fsha(p) for p in prev_trio], 'vb_dec': lst(VCD / 'dec'), 'vb_hook': lst(VCD / 'hook'),
              'vb_rec': lst(VCD / 'rec'), 'rr_s41': lst(RRD)}
    res['before'] = before
    res['tree'] = build_tree()
    if not res['tree']['equal_to_vbt'] or res['tree']['rec_sha256'] != REC_SHA:
        raise SystemExit('rerun tree differs from the V-B tree')
    r1, P1 = run_one(T1, prev_trio[0], 'VB-41/b1/T%s' % R.t6(T1))
    res['T1'] = r1
    r2, P2 = run_one(T2, MCD / 'dec' / ('action_%s.json' % R.t6(T1)), 'VB-41/b1/T%s' % R.t6(T2))
    res['T2'] = r2
    # identity rule R-ID
    id1 = identity(T1, P1, None, None)
    id1_subst = identity(T1, P1, [SUB_OUT], None)
    vb_t1 = {'json': R.fsha(t1_trio[0]), 'applied': R.fsha(t1_trio[2]) if t1_trio[2].is_file() else None}
    my_t1 = {'json': r1['json_sha256'], 'applied': (r1['receipt'] or {}).get('sha256')}

    def extra(path, kind, va, vb, group):
        g = R.gpath(path)
        if g in ('/metadata/sdmpc_state/previous_application/receipt_sha256',
                 '/metadata/joint_leader_selection/price_state/previous_application/receipt_sha256'):
            return '(a) receipt sha' if kind == 'value' and va == vb_t1['applied'] and vb == my_t1['applied'] else None
        if g == '/metadata/n31_binding/vsl_cohort_initialization/sha256':
            return '(b) previous JSON sha' if kind == 'value' and va == vb_t1['json'] and vb == my_t1['json'] else None
        if group == 'D' and R.lastc(path).endswith('action_token'):
            return '(c) action_token'
        return None
    id2 = identity(T2, P2, [SUB_OUT], extra)
    id2_raw = identity(T2, P2, None, None)
    res['identity'] = {
        'T1': id1, 'T1_with_place_substitution_report_only': id1_subst,
        'T2': id2, 'T2_without_substitution_report_only': {k: id2_raw[k] for k in (
            'verdict', 'csv_same', 'unclassified_n', 'allowed')},
        'vb_t1_sha': vb_t1, 'rerun_t1_sha': my_t1}
    res['identity']['T1_ok'] = id1['verdict'] == 'PASS' and id1['csv_same'] is True
    res['identity']['T2_ok'] = id2['verdict'] == 'PASS' and id2['csv_same'] is True
    res['identity']['ok'] = res['identity']['T1_ok'] and res['identity']['T2_ok']
    after = {'prev_trio': [R.fsha(p) for p in prev_trio], 'vb_dec': lst(VCD / 'dec'), 'vb_hook': lst(VCD / 'hook'),
             'vb_rec': lst(VCD / 'rec'), 'rr_s41': lst(RRD)}
    res['after'] = after
    res['read_only_unchanged'] = before == after
    res['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    res['log'] = LOG
    (MYR / 'rerun.json').write_text(json.dumps(res, indent=1, default=str), encoding='utf-8')
    log('END identity T1=%s T2=%s read_only_unchanged=%s rerun.json sha=%s' % (
        res['identity']['T1_ok'], res['identity']['T2_ok'], res['read_only_unchanged'], R.fsha(MYR / 'rerun.json')))
    print('VVB3_RERUN_DONE', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
