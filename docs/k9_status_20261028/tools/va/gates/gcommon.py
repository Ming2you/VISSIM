"""K9-2 V-A OfflineGates (amendment 34 section 5 on FRZ_K92) shared constants and helpers.

Copy of the K8b gate tool SP/j1/fix/gates/gcommon.py (556a6511...) with the expected values of amendment 34 section 5.0
R4 item 1 (FRZ_K92 = sdmpc31_c20aff1d_202610230833, K9-2-7 head, tuning c8e3ee2c..., list file / list sha, OUTVA) and the
K8b self-test profile constants of R4 item 7 (FRZ_K8b, b9734abe, d0f9ef39..., list f954c2b0..., OUTH).
Read-only on: FRZ_K92, FRZ_K8b, FRZ_K7, R-obs3, the J1 run folders, OUTH.  Writes under OUTVA (D:) and SP/k92/va/gates.
GWT8 is used as a replay Root only for SDMPC decisions (amendment 21 section 7.0); its new tangent-cache files are moved
to OUTVA/moved_tangentcache_gwt8/ at the end.
BLIND: nothing here prints an objective / prediction value."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FRZN = Path(r'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833')        # FRZ_K92 (this stage, PushFreeze record)
FRZ8 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821')        # FRZ_K8b (previous freeze; read only)
FRZ7 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831')        # FRZ_K7 (R-obs3 recorded root)
WT = Path(r'D:/VISSIM-merge/sim3-n31-k8')                                    # GWT8
ROBS3 = Path(r'D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31')     # R-obs3
ROBS3_DEC = ROBS3 / 'decisions_sdmpc31_v3c3_nc_s31'
RUNS = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')                           # RR (J1 runs; read only)
J1 = {'31r': RUNS / 'sdmpc31_v3c3_k8j1r_s31', '31': RUNS / 'sdmpc31_v3c3_k8j1_s31',
      '41': RUNS / 'sdmpc31_v3c3_k8j1_s41', '43': RUNS / 'sdmpc31_v3c3_k8j1_s43'}
RVA = Path(r'D:/VISSIM_runs/20261023_sdmpc31_k92')                           # V-A RunsRoot (G-H5' preflights only)
TOOLS = FRZN / 'diagnostics/sdmpc_n31_20260924/tools'                        # replay tools (sha == FRZ_K8b copies)
REP8 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8')
OUTH = REP8 / 'offline_gates_k8h'                                            # FRZ_K8b gate outputs (read only)
OUTV = REP8 / 'k92_va' / 'offline_gates'                                     # this stage (OUTVA)
K7GB = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/gb')
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'      # = provenance RW_PYTHON
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
DEPROOT = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
HEAD = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'                           # K9-2-7 (pushed head)
HEAD_K925 = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'                      # K9-2-5 (FG base)
HEAD_K8B = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'                       # K8-10 (FRZ_K8b head)
FREEZE_SHA = '011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476'
FREEZE_K8B_SHA = '6143d3eb0d455e5fde46b190b4d4d8c2a7068a96c7fc9178126b922af937c7b6'
TUNING_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
TUNING_K8B_SHA = 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6'
TUNING_REL = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
CAO_REL = 'evaluation/controllers/control_area_objective.py'
GB7_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
LIST_SHA = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
ALLOWED_FILE_SHA = '61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319'   # K9-2-7 blob 1ca72d81 bytes
A_K8_N = 35
LIST_K8B_SHA = 'f954c2b0510ddc8d77d8b5b6d2efb288eee4110e37eac935a4d153baefe366e7'
ALLOWED_FILE_K8B_SHA = 'c6f9ca1cbf1e1ac49f1bc7adf44e33add289fea5858be8f5884c7225753894c8'
A_K8_N_K8B = 34
FLOOR_KEY = 'head_discharge_floor_173_p4_e36d6761cfeac634'                   # R-obs3 v3c3-s31 name (amendment 34 5.2)
EK92_SHA = 'd15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11'   # gb7_k92decl.py (S-A34-11)
TOOL_SHA = {'make_replay_state_v2.py': '4adf41cfa7569047d87774bb648b353780fbb7ffc9b916a9c8f726e1d1de0714',
            'replay_decision_n31.ps1': '5d34109fdd61decaf3cbdd32c5b9d80a0768043d3c26fce83306f54144ce99c9'}
BELOW_NORMAL = 0x00004000
WINDOW = 150
NUMBA = str(OUTV / 'numba_cache')
PATTERN = ('vissim_stackelberg_adapter', 'make_replay_state', 'replay_decision', 'sdmpc_tangent_worker',
           'run_sdmpc_n31', 'run_real_world_stackelberg', 'og_driver', 'og2_driver', 'cap_child', 'sa_capture',
           'worker.py', 's31_arm', 'p0_run', 'decision_hold', 'g_driver', 'gh1_driver', 'gr_driver')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def set_below_normal():
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k32.GetPriorityClass.restype = wintypes.DWORD
    h = k32.GetCurrentProcess()
    k32.SetPriorityClass(h, BELOW_NORMAL)
    pc = k32.GetPriorityClass(h)
    if pc != BELOW_NORMAL:
        raise SystemExit('priority read-back 0x%x is not BELOW_NORMAL' % pc)
    return pc


def child_env(hashseed='0', extra=None, drop_numba_threads=True):
    """og_common.child_env / p0common.child_env: RW_* K8_* K8G_* S31F_* GH1_* removed, threads 1, NUMBA cache in OUTH."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RW_', 'K8_', 'K8G_', 'S31F_', 'GH1_'))}
    env.update({'NUMBA_CACHE_DIR': NUMBA, 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    if drop_numba_threads:
        env.pop('NUMBA_NUM_THREADS', None)
    else:
        env['NUMBA_NUM_THREADS'] = '1'
    env.pop('PYTHONHASHSEED', None)
    if hashseed not in (None, 'unset'):
        env['PYTHONHASHSEED'] = str(hashseed)
    if extra:
        env.update(extra)
    return env


def free_space_gb():
    return {d[0]: round(shutil.disk_usage(d).free / 1e9, 2) for d in ('C:\\', 'D:\\')}


def require_space(log):
    fs = free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        log('LOW_SPACE %s (< 8 GB): STOP' % fs)
        raise SystemExit('LOW_SPACE %s' % fs)
    return fs


def processes():
    ps = ("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
          "ConvertTo-Json -Compress")
    done = subprocess.run([PS, '-NoProfile', '-Command', ps], capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=180)
    try:
        rows = json.loads(done.stdout)
    except Exception:  # noqa: BLE001
        return []
    return rows if isinstance(rows, list) else [rows]


def census(rows=None):
    rows = processes() if rows is None else rows
    parent = {r['ProcessId']: r['ParentProcessId'] for r in rows}
    me = os.getpid()
    by = {}
    foreign = []
    for r in rows:
        name = str(r.get('Name')).lower()
        by[name] = by.get(name, 0) + 1
        cmd = str(r.get('CommandLine') or '')
        if name in ('python.exe', 'powershell.exe', 'cscript.exe') and any(p in cmd for p in PATTERN):
            pid, mine, seen = r['ProcessId'], False, set()
            while pid in parent and pid not in seen:
                seen.add(pid)
                if pid == me:
                    mine = True
                    break
                pid = parent[pid]
            if not mine:
                foreign.append((r['ProcessId'], name, cmd[:160]))
    keep = ('python.exe', 'vissim200.exe', 'vissim.exe', 'vissim2024.exe', 'cscript.exe', 'powershell.exe')
    return {'counts': {k: by.get(k, 0) for k in keep},
            'vissim_any': sum(v for k, v in by.items() if k.startswith('vissim')),
            'foreign_runner_or_replay': foreign}


def wait_idle(log, step):
    """Wait while a foreign replay/runner python runs (og_common.wait_idle).  Never kills anything."""
    t0 = time.perf_counter()
    last = -1e9
    while True:
        c = census()
        waited = time.perf_counter() - t0
        if not c['foreign_runner_or_replay']:
            if waited > 5:
                log('IDLE after %d s wait before %s' % (waited, step))
            return round(waited, 1), c
        if waited - last >= 300:
            log('BUSY before %s: %s' % (step, c['foreign_runner_or_replay'][:3]))
            last = waited
        time.sleep(5)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, default=str), encoding='utf-8')


def run_capture(argv, out_path, env, cwd=None):
    t0 = time.perf_counter()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', errors='replace') as f:
        done = subprocess.run(argv, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, creationflags=BELOW_NORMAL)
    return done.returncode, time.perf_counter() - t0, Path(out_path).read_text(encoding='utf-8', errors='replace')


def listing(root, cache_dirs=('__pycache__', '__tangentcache__', '.pytest_cache')):
    """rel path -> [size, mtime] (metadata only), caches kept apart (p0common.listing)."""
    files, caches = {}, {}
    root = str(root)
    for base, dirs, names in os.walk(root):
        dirs.sort()
        rel_base = os.path.relpath(base, root)
        in_cache = any(p in cache_dirs for p in Path(rel_base).parts)
        for n in sorted(names):
            p = os.path.join(base, n)
            rel = os.path.relpath(p, root).replace('\\', '/')
            try:
                st = os.stat(p)
            except OSError as e:
                (caches if in_cache else files)[rel] = ['ERR', str(e)]
                continue
            (caches if in_cache else files)[rel] = [st.st_size, round(st.st_mtime, 6)]

    def digest(d):
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
    return {'root': root, 'files': len(files), 'digest': digest(files), 'cache_files': len(caches),
            'cache_digest': digest(caches), 'table': files, 'cache_table': caches}


def listing_brief(l):
    return {k: l[k] for k in ('root', 'files', 'digest', 'cache_files', 'cache_digest')}


def compare_listing(a, b):
    out = {}
    for part in ('table', 'cache_table'):
        ta, tb = a[part], b[part]
        out[part] = {'changed': sorted(k for k in ta.keys() & tb.keys() if ta[k] != tb[k]),
                     'added': sorted(tb.keys() - ta.keys()), 'removed': sorted(ta.keys() - tb.keys())}
    return out


def listing_same(a, b, include_cache=True):
    d = compare_listing(a, b)
    parts = ('table', 'cache_table') if include_cache else ('table',)
    return all(not v for p in parts for v in d[p].values()), d


def frozen_entries():
    base = Path(r'D:/VISSIM-merge/frozen')
    out = {}
    for p in sorted(base.iterdir()):
        st = p.stat()
        out[p.name] = {'dir': p.is_dir(), 'mtime': st.st_mtime, 'size': (st.st_size if p.is_file() else None)}
    return out


def git(*args, cwd=WT):
    return subprocess.run(['git', '-C', str(cwd)] + list(args), capture_output=True, text=True).stdout


def fm():
    sys.path.insert(0, str(TOOLS))
    import freeze_manifest
    return freeze_manifest


def freeze_doc(frz=FRZN):
    return read_json(frz / 'FREEZE.json')


def tree_vs_freeze(root, frz=FRZN):
    """freeze_manifest.hash_tree(root) vs FREEZE.json files of frz: {changed, missing, extra} (caches excluded)."""
    m = fm()
    actual, total = m.hash_tree(root)
    d = m.diff_tables(freeze_doc(frz)['files'], actual)
    return d, total


def aim_gwt8(log):
    """Amendment 21 section 7.0 / amendment 34 section 5.0 aim check for Root = GWT8 @ K9-2-7: HEAD = K9-2-7,
    status --porcelain --ignored without caches = 0 lines, GWT8 bytes = FRZ_K92 FREEZE table (changed/missing/extra
    0/0/0), FREEZE sha/head as recorded."""
    fsha = sha256_file(FRZN / 'FREEZE.json')
    doc = freeze_doc()
    head = git('rev-parse', 'HEAD').strip()
    status = [l for l in git('status', '--porcelain', '--ignored').splitlines()
              if l and '__tangentcache__' not in l and '__pycache__' not in l and '.pytest_cache' not in l]
    d, _ = tree_vs_freeze(WT)
    rec = {'freeze_sha256': fsha, 'frz_head': doc['git']['head'], 'gwt_head': head, 'gwt_status': status[:20],
           'gwt_vs_frz_count': {k: len(v) for k, v in d.items()}, 'gwt_vs_frz': {k: sorted(v)[:20] for k, v in d.items()},
           'free_gb': free_space_gb(), 'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    rec['ok'] = (fsha == FREEZE_SHA and doc['git']['head'] == HEAD and head == HEAD and not status
                 and not any(rec['gwt_vs_frz_count'].values()))
    log('AIM_GWT8 ok=%s freeze=%s frz_head=%s gwt_head=%s status=%d diff=%s' % (
        rec['ok'], fsha[:8], doc['git']['head'][:8], head[:8], len(status), rec['gwt_vs_frz_count']))
    return rec


def tangentcache_names(root):
    d = Path(root) / 'evaluation' / 'controllers' / '__tangentcache__'
    return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


def move_new_tangentcache(before_names, tag, log):
    """New GWT8 tangent-cache files -> OUTVA/moved_tangentcache_gwt8/ (+ list csv).  Old files untouched."""
    import csv
    new = sorted(set(tangentcache_names(WT)) - set(before_names))
    rows = []
    if new:
        dst_dir = OUTV / 'moved_tangentcache_gwt8'
        dst_dir.mkdir(parents=True, exist_ok=True)
        src_dir = WT / 'evaluation' / 'controllers' / '__tangentcache__'
        for name in new:
            src, dst = src_dir / name, dst_dir / name
            if dst.exists():
                raise SystemExit('moved tangent cache target exists: %s' % dst)
            st = src.stat()
            rows.append({'name': name, 'size': st.st_size, 'mtime': st.st_mtime, 'sha256': sha256_file(src)})
            shutil.move(str(src), str(dst))
        lst = OUTV / ('moved_tangentcache_gwt8_list_%s.csv' % tag)
        with open(lst, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['name', 'size', 'mtime', 'sha256'])
            w.writeheader()
            w.writerows(rows)
    log('TANGENTCACHE_MOVED tag=%s n=%d' % (tag, len(rows)))
    return rows


def load_allowed(frz=FRZN, file_sha=ALLOWED_FILE_SHA, list_sha=LIST_SHA, n_a=A_K8_N):
    """gb7_allowed.py of a frozen root (default FRZ_K92: file sha = K9-2-7 blob bytes sha, list a8148f38..., A_K8 35,
    V 7; the K8b self-test profile passes FRZ_K8b, c6f9ca1c..., f954c2b0..., 34), list sha / counts checked."""
    p = Path(frz) / GB7_REL
    fsha = sha256_file(p)
    if fsha != file_sha:
        raise SystemExit('gb7_allowed.py sha %s != %s' % (fsha, file_sha))
    import importlib.util
    spec = importlib.util.spec_from_file_location('gb7_allowed_' + Path(frz).name, str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lsha = mod.list_sha256()
    if lsha != list_sha or len(mod.A_K8) != n_a or len(mod.V) != 7:
        raise SystemExit('gb7_allowed list check failed sha=%s n=%d V=%d' % (lsha, len(mod.A_K8), len(mod.V)))
    return mod, {'file': str(p), 'file_sha256': fsha, 'list_sha256': lsha, 'A_K8': len(mod.A_K8), 'V': len(mod.V)}


def tools_check():
    got = {n: sha256_file(TOOLS / n) for n in TOOL_SHA}
    got8 = {n: sha256_file(FRZ8 / 'diagnostics/sdmpc_n31_20260924/tools' / n) for n in TOOL_SHA}
    return {'frzn': got, 'frz8': got8, 'ok': got == TOOL_SHA == got8}


def progress_present(path):
    """True if the progress log has an sdmpc_completed record (no value is returned)."""
    path = Path(path)
    if not path.is_file():
        return False
    for line in reversed(path.read_text(encoding='utf-8').splitlines()):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if (record.get('stage') or record.get('event')) == 'sdmpc_completed':
            return True
    return False


def text_count(path, needle):
    p = Path(path)
    if not p.is_file():
        return None
    return sum(needle in l for l in p.read_text(encoding='utf-8', errors='replace').splitlines())


def csv_kind_counts(path):
    import csv
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out[r.get('kind')] = out.get(r.get('kind'), 0) + 1
    return out


def lp(path):
    return '\\\\?\\' + os.path.abspath(str(path))


def ps1_lines(text, s6):
    lines = text.splitlines()
    return {'verdict_line': [l[:200] for l in lines if l.startswith('REPLAY_COMPARE')],
            'checks': [l[:200] for l in lines if l.startswith('REPLAY_CHECK')],
            'replay_line': [l[:200] for l in lines if l.startswith('REPLAY_' + s6)],
            'freeze_line': [l[:300] for l in lines if l.startswith('FREEZE')][-1:],
            'root_lines': [l[:300] for l in lines if l.startswith(('ROOT_NOT_FROZEN', 'REBASE', 'REPLAY_START'))],
            'refused': [l[:300] for l in lines if l.startswith('REPLAY_REFUSED')],
            'stderr_tail_count': sum(l.startswith('STDERR') for l in lines),
            'decision_failed': sum('DECISION_FAILED' in l for l in lines)}


def verdict_of(lines):
    for l in reversed(lines):
        m = re.search(r'verdict=(\w+)', l)
        if m:
            return m.group(1)
    return None
