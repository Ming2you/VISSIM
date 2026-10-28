"""VerifyGates re-runs for bit-identity (task: at most 2 GB-7' replays and 1 hash A/B case).

python -B v_rerun.py run  <VGO>                 the three re-runs, then the comparison (writes VGO/rerun/...)
python -B v_rerun.py prep <dec> <T> <out> <rec> child: sha-checked COPY prepare + F17b history (no hard links)

Cases (fixed before any gate output is read):
  A1   GB-7'  T = 1     PYTHONHASHSEED 0      (no previous action; the R2-12 length key and E1-E4 decision)
  A750 GB-7'  T = 750   PYTHONHASHSEED 0      (last warm-up decision where E4 is expected; 4 history windows)
  H9000 hash  T = 9000  PYTHONHASHSEED unset  (59 history windows; the unset arm)
Each = FRZ_K92 make_replay_state_v2.prepare with link_or_copy -> copy only (prepare re-hashes each copy) + F17b history
copy (R-obs3 obs150/derived_<T'>.json, T' = 150 .. T-150, byte compared) + FRZ_K92 replay_decision_n31.ps1
-ReplayDir <bundle> -Root FRZ_K92 (Controller from the R-obs3 launch plan = no-control) + a second compare without
--tuning.  These are the frozen replay tools; nothing of VA/gates is used.  Child env = the gate rule (RW_* K8_* K8G_*
S31F_* GH1_* removed, threads 1, PYTHONUTF8 1, PYTHONDONTWRITEBYTECODE 1, NUMBA_NUM_THREADS removed,
NUMBA_CACHE_DIR = VGO/numba_cache, PYTHONHASHSEED as the case says), BELOW_NORMAL, one job at a time; waits while a
foreign replay/runner python runs (never kills anything).
Bit-identity = against the gate bundle of the same case: replay action CSV bytes equal, replay action JSON deep diff
only on V paths, derived_<T>.json equal except inputs.raw_sha256 (it hashes the state, which names the bundle folder),
ps1 / adapter exit and both compare verdicts equal, and my v_judge row of the re-run == my v_judge row of the gate
bundle (conditions 1-8, both condition-7 forms, control fields, outside paths, diff count).
BLIND: paths, kinds, booleans, counts, sha256, wall seconds only."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v_lib as L  # noqa: E402

BELOW_NORMAL = 0x00004000
CASES = (('A1', 'A', 1, '0', 'T000001'), ('A750', 'A', 750, '0', 'T000750'), ('H9000', 'H', 9000, 'unset', 'T009000_hunset_r1'))
PATTERNS = ('vissim_stackelberg_adapter', 'make_replay_state', 'replay_decision', 'run_sdmpc_n31', 'g_driver',
            'sdmpc_tangent_worker', 'run_real_world_stackelberg', 'gh1_driver', 'gr_driver')


def prep_child(dec, T, out_dir, rec_path):
    dec, T, out_dir = Path(dec), int(T), Path(out_dir)
    sys.path.insert(0, str(L.FRZN / L.TOOLS_REL))
    import n31_common  # noqa: E402  (frozen replay tool)
    import make_replay_state_v2 as m  # noqa: E402  (frozen replay tool)
    copies = []

    def copy_only(source, target):
        source, target = Path(source), Path(target)
        n31_common.require(source.is_file(), f'Missing file to copy: {source}')
        n31_common.require(not target.exists(), f'Copy target already exists: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(n31_common.long_path(source), n31_common.long_path(target))
        copies.append(str(target))
        return 'copy'
    n31_common.link_or_copy = copy_only
    m.link_or_copy = copy_only
    man = m.prepare(str(dec), T, str(out_dir))
    hist = []
    for Tp in range(150, T, 150):
        src = dec / 'obs150' / ('derived_%06d.json' % Tp)
        dst = out_dir / 'obs150' / ('derived_%06d.json' % Tp)
        if dst.exists():
            raise SystemExit('history target exists: %s' % dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if dst.read_bytes() != src.read_bytes():
            raise SystemExit('history copy differs: %s' % dst)
        hist.append(Tp)
    L.write_json(rec_path, {'T': T, 'links': len(man['links']), 'methods': sorted({x['method'] for x in man['links']}),
                            'history': len(hist), 'history_expected': len(range(150, T, 150))})
    print('VPREP_OK T=%d links=%d history=%d' % (T, len(man['links']), len(hist)))


def child_env(hashseed, numba):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('RW_', 'K8_', 'K8G_', 'S31F_', 'GH1_'))}
    env.update({'NUMBA_CACHE_DIR': str(numba), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                'OPENBLAS_NUM_THREADS': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    env.pop('NUMBA_NUM_THREADS', None)
    env.pop('PYTHONHASHSEED', None)
    if hashseed != 'unset':
        env['PYTHONHASHSEED'] = hashseed
    return env


def foreign():
    q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','powershell.exe','cscript.exe') } | "
         "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    r = subprocess.run([L.PS, '-NoProfile', '-Command', q], capture_output=True, text=True, encoding='utf-8', errors='replace')
    try:
        rows = json.loads(r.stdout or '[]')
    except ValueError:
        return []
    rows = rows if isinstance(rows, list) else [rows]
    return [[x['ProcessId'], x['Name']] for x in rows if any(p in str(x.get('CommandLine') or '') for p in PATTERNS)]


def vissim_count():
    r = subprocess.run([L.PS, '-NoProfile', '-Command', "@(Get-Process | Where-Object { $_.ProcessName -like 'VISSIM*' }).Count"],
                       capture_output=True, text=True)
    return (r.stdout or '').strip()


def run_capture(argv, out_path, env):
    t0 = time.perf_counter()
    with open(out_path, 'w', encoding='utf-8', errors='replace') as f:
        done = subprocess.run(argv, env=env, stdout=f, stderr=subprocess.STDOUT, creationflags=BELOW_NORMAL)
    return done.returncode, round(time.perf_counter() - t0, 1)


def log(vgo, msg):
    line = time.strftime('%Y-%m-%dT%H:%M:%S ') + msg
    with open(vgo / 'logs' / 'v_rerun.log', 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(line, flush=True)


def one(vgo, key, gate, T, seed, tag):
    group = vgo / 'rerun' / ('gb7' + gate)
    group.mkdir(parents=True, exist_ok=True)
    d = group / tag
    sp = group / (tag + '.summary.json')
    if sp.exists():
        log(vgo, 'SKIP %s (summary exists)' % key)
        return L.read_json(sp)
    if d.exists():
        moved = group / ('%s_interrupted_%s_%d' % (tag, time.strftime('%Y%m%d_%H%M%S'), time.time_ns() % 1000000))
        d.rename(moved)
        log(vgo, 'MOVED_INTERRUPTED %s -> %s' % (d, moved))
    waited = 0
    while True:
        f = foreign()
        if not f:
            break
        if waited % 300 == 0:
            log(vgo, 'BUSY before %s foreign=%s' % (key, f[:3]))
        time.sleep(15)
        waited += 15
    fs = {k: round(shutil.disk_usage(k).free / 1e9, 1) for k in ('C:\\', 'D:\\')}
    if min(fs.values()) < 8.0:
        log(vgo, 'LOW_SPACE %s STOP' % fs)
        raise SystemExit(3)
    env = child_env(seed, vgo / 'numba_cache')
    s = {'key': key, 'T': T, 'tag': tag, 'hashseed': seed, 'env_pythonhashseed': env.get('PYTHONHASHSEED'),
         'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'waited_sec': waited, 'free_gb': fs, 'vissim_at_start': vissim_count()}
    rc, sec = run_capture([L.PY, '-B', str(Path(__file__).resolve()), 'prep', str(L.ROBS3_DEC), str(T), str(d),
                           str(group / (tag + '.prep.json'))], group / (tag + '.prepare.txt'), env)
    s['prepare'] = {'exit': rc, 'sec': sec}
    if rc != 0:
        L.write_json(sp, s)
        log(vgo, 'PREP_FAILED %s rc=%s' % (key, rc))
        return s
    rc, sec = run_capture([L.PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                           str(L.FRZN / L.TOOLS_REL / 'replay_decision_n31.ps1'), '-ReplayDir', str(d), '-Root', str(L.FRZN)],
                          group / (tag + '.ps1.txt'), env)
    s['ps1'] = {'exit': rc, 'sec': sec}
    if (d / 'replay_compare.json').is_file():
        shutil.copy2(d / 'replay_compare.json', d / 'replay_compare_ps1.json')
        (d / 'replay_compare.json').unlink()
    rc2, sec2 = run_capture([L.PY, '-B', str(L.FRZN / L.TOOLS_REL / 'make_replay_state_v2.py'), 'compare', str(d)],
                            group / (tag + '.compare.txt'), env)
    s['compare'] = {'exit': rc2, 'sec': sec2}
    s['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    L.write_json(sp, s)
    rr = L.read_json(d / 'replay' / 'replay_run.json') if (d / 'replay' / 'replay_run.json').is_file() else {}
    log(vgo, 'DONE %s ps1_exit=%s compare_exit=%s adapter_exit=%s wall=%s hashseed=%s' % (
        key, rc, rc2, rr.get('exit_code'), rr.get('wall_sec'), s['env_pythonhashseed']))
    return s


def compare(vgo):
    import v_judge as VJ   # my own recomputation tool
    P = VJ.PROFILES['NEW']
    G = L.AllowedList(L.FRZN, L.GB7_FILE_SHA, L.LIST_SHA, 35)
    out = {}
    for key, gate, T, seed, tag in CASES:
        s6 = '%06d' % T
        mg = vgo / 'rerun' / ('gb7' + gate)
        gg = L.OUTVA / 'gb7' / gate
        md, gd = mg / tag, gg / tag
        r = {'T': T, 'hashseed': seed}
        mine_csv = open(L.long(md / 'replay' / ('action_%s.csv' % s6)), 'rb').read()
        gate_csv = open(L.long(gd / 'replay' / ('action_%s.csv' % s6)), 'rb').read()
        r['csv_bytes_equal'] = mine_csv == gate_csv
        r['csv_sha256'] = [L.sha256_bytes(mine_csv), L.sha256_bytes(gate_csv)]
        a = L.read_json(gd / 'replay' / ('action_%s.json' % s6))
        b = L.read_json(md / 'replay' / ('action_%s.json' % s6))
        diff = L.deep_diff(a, b)
        r['json_diff_paths'] = [[p, k] for p, k, _s in diff]
        r['json_diff_outside_V'] = [p for p, _k, _s in diff if p not in G.V]
        r['json_equal_except_V'] = not r['json_diff_outside_V']
        da = L.read_json(gd / 'obs150' / ('derived_%s.json' % s6))
        db = L.read_json(md / 'obs150' / ('derived_%s.json' % s6))
        ddiff = [p for p, _k, _s in L.deep_diff(da, db)]
        r['derived_diff_paths'] = ddiff
        r['derived_equal_except_raw_sha'] = all(p == '/inputs/raw_sha256' for p in ddiff)
        pg = L.ps1_facts(L.lines_of(gg / (tag + '.ps1.txt')), s6)
        pm = L.ps1_facts(L.lines_of(mg / (tag + '.ps1.txt')), s6)
        sm = L.read_json(mg / (tag + '.summary.json'))
        r['ps1_exit'] = {'mine_actual': sm['ps1']['exit'], 'mine_inferred': pm['ps1_exit_inferred'],
                         'gate_inferred': pg['ps1_exit_inferred']}
        r['ps1_exit_equal'] = sm['ps1']['exit'] == pm['ps1_exit_inferred'] == pg['ps1_exit_inferred']
        cg1, cm1 = L.read_json(gd / 'replay_compare_ps1.json'), L.read_json(md / 'replay_compare_ps1.json')
        cg2, cm2 = L.read_json(gd / 'replay_compare.json'), L.read_json(md / 'replay_compare.json')
        flags = lambda c: (c.get('verdict'), {k: v.get('ok') for k, v in (c.get('checks') or {}).items()})  # noqa: E731
        r['compare_flags_equal'] = flags(cg1) == flags(cm1) and flags(cg2) == flags(cm2)
        r['compare_verdicts'] = [cm1.get('verdict'), cm2.get('verdict')]
        rg, rm = L.read_json(gd / 'replay' / 'replay_run.json'), L.read_json(md / 'replay' / 'replay_run.json')
        r['adapter_exit'] = [rm.get('exit_code'), rg.get('exit_code')]
        r['wall_sec'] = [rm.get('wall_sec'), rg.get('wall_sec')]
        r['replay_run_args_equal_except_bundle'] = (
            [x.replace(str(md), '<b>') for x in rm.get('arguments') or []] == [x.replace(str(gd), '<b>') for x in rg.get('arguments') or []]
            and rm.get('env') == rg.get('env') and rm.get('controller') == rg.get('controller'))
        rowm = VJ.gb7_row(P, G, mg, tag, T)
        rowg = VJ.gb7_row(P, G, gg, tag, T)
        keys = VJ.COND + ('c7_declared_A', 'control_fields_equal', 'diff_count', 'outside_A', 'outside_A_and_EK92', 'ok')
        r['row_mine'] = {k: rowm.get(k) for k in keys}
        r['row_gate_bundle'] = {k: rowg.get(k) for k in keys}
        r['rows_equal'] = r['row_mine'] == r['row_gate_bundle']
        r['ek92_hits_equal'] = rowm.get('ek92_hits') == rowg.get('ek92_hits')
        r['env_pythonhashseed_mine'] = sm.get('env_pythonhashseed')
        r['bit_identical'] = (r['csv_bytes_equal'] and r['json_equal_except_V'] and r['derived_equal_except_raw_sha']
                              and r['ps1_exit_equal'] and r['compare_flags_equal'] and r['adapter_exit'] == [0, 0]
                              and r['replay_run_args_equal_except_bundle'] and r['rows_equal'] and r['ek92_hits_equal'])
        out[key] = r
        print('V_RERUN_CMP %s bit_identical=%s csv=%s json_outV=%d derived=%s ps1=%s rows=%s wall=%s' % (
            key, r['bit_identical'], r['csv_bytes_equal'], len(r['json_diff_outside_V']), r['derived_diff_paths'],
            r['ps1_exit'], r['rows_equal'], r['wall_sec']), flush=True)
    res = {'cases': out, 'all_bit_identical': all(v['bit_identical'] for v in out.values()),
           'finished': time.strftime('%Y-%m-%dT%H:%M:%S')}
    L.write_json(vgo / 'rerun' / 'rerun_result.json', res)
    print('V_RERUN_DONE all_bit_identical=%s sha256=%s' % (res['all_bit_identical'],
                                                          L.sha256_file(vgo / 'rerun' / 'rerun_result.json')), flush=True)


def set_below_normal():
    import ctypes
    k32 = ctypes.WinDLL('kernel32')
    k32.SetPriorityClass(k32.GetCurrentProcess(), BELOW_NORMAL)
    return k32.GetPriorityClass(k32.GetCurrentProcess())


if __name__ == '__main__':
    if sys.argv[1] == 'prep':
        prep_child(*sys.argv[2:6])
    elif sys.argv[1] == 'run':
        vgo = Path(sys.argv[2])
        (vgo / 'logs').mkdir(parents=True, exist_ok=True)
        pc = set_below_normal()
        log(vgo, 'V_RERUN start pid=%d priority=0x%x env_hashseed=%s' % (os.getpid(), pc, os.environ.get('PYTHONHASHSEED')))
        for c in CASES:
            one(vgo, *c)
        compare(vgo)
        log(vgo, 'V_RERUN end')
    else:
        raise SystemExit('usage')
