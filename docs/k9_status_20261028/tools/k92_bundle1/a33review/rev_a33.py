"""ReviewDeclare A33: adversarial synthetic checks of the amendment-33 hook naming (diagnostics only, never committed).
SYNTHETIC inputs only, own folder KB/a33review.  Read-only uses: AD33/dry_a33.py (imported for its synthetic program
strings and listing helpers only; its main() is not run and nothing is written under AD33), AD33/vbhook and AD32/vbhook
(loaded into synthetic children), AD32/vb_select.py (child on synthetic folders), KV2/vb_chain.py and KV2/vb_recalc.py
(imported for vbi7 / reselect / i7_of on synthetic folders), the committed recorder bytes (GWT8, sha 1d1dfa36...,
copied into the synthetic tree).  No decision replay, no adapter, no VISSIM.

    python -B rev_a33.py all   -> out/rev_a33.json (+ one line per case)

Cases
  R1  real OS process ids, no forcing: one hook folder, an adapter-role program (idle) and N worker-role programs run one
      after another (each ends before the next starts) -> natural PID reuse is counted; new hook: tokens unique, no
      error, select 'selected', VB-I7 true (driver and recalculator equal)
  R1o the same with the amendment-32 hook (control): if the OS reused a pid, a collision / overwrite must show
  R2  forced same pid AND same time_ns for 12 worker-role programs started at the same time, 4 threads each
  R3  retry inside one process: the hook module is executed twice in one process (importlib.reload), worker role and
      adapter role; new hook vs old hook
  R4  forced same pid, same time_ns and same random bytes for two of three sequential workers (third distinct)"""
import hashlib
import importlib
import importlib.util
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
KB = HERE.parent
AD33 = KB / 'a33decl'
AD32 = KB / 'a32decl'
KV2 = KB / 'k92_vb2'
SYN = HERE / 'syn'
OUT = HERE / 'out'
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
GWT8_SA = Path(r'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/sa')
RECORDER_SHA = '1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90'
NEW_HOOK_SHA = '691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c'
OLD_HOOK_SHA = '4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321'
DRY_SHA = 'd1992a8c244c654b5663f8b14fe8875f9682549a5f7f0b888972b41ed9b027ab'
DRIVER_SHA = '87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322'
RECALC_SHA = '6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b'
SELECT_SHA = '33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc'
ADAPTER = 'vissim_stackelberg_adapter.py'
WORKER = 'sdmpc_tangent_worker.py'
RELOAD = 'import importlib as _il\nimport sitecustomize as _sc\n_il.reload(_sc)\n'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path, name, want):
    if sha(path) != want:
        raise SystemExit('pinned module differs: %s' % path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def below_normal():
    # explicit HANDLE types: with ctypes' default int return type the pseudo-handle of GetCurrentProcess() is cut to
    # 32 bits and SetPriorityClass fails with ERROR_INVALID_HANDLE (seen in run 2 of this tool)
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k32.GetPriorityClass.restype = wintypes.DWORD
    h = k32.GetCurrentProcess()
    k32.SetPriorityClass(h, 0x00004000)
    return k32.GetPriorityClass(h) == 0x00004000


DRY = load(AD33 / 'dry_a33.py', 'dry_a33_rev', DRY_SHA)
DRV = load(KV2 / 'vb_chain.py', 'vb_chain_rev', DRIVER_SHA)
RCL = load(KV2 / 'vb_recalc.py', 'vb_recalc_rev', RECALC_SHA)
HOOKS = {'new': (AD33 / 'vbhook', NEW_HOOK_SHA), 'old': (AD32 / 'vbhook', OLD_HOOK_SHA)}


def build():
    if SYN.exists():
        shutil.rmtree(SYN)
    pkg = SYN / 'pkg'
    (pkg / 'evaluation' / 'controllers').mkdir(parents=True)
    (pkg / 'sdmpc.py').write_text(DRY.PKG_SDMPC, encoding='utf-8')
    (pkg / 'other.py').write_text(DRY.PKG_OTHER, encoding='utf-8')
    (pkg / 'evaluation' / '__init__.py').write_text('', encoding='utf-8')
    (pkg / 'evaluation' / 'controllers' / '__init__.py').write_text('', encoding='utf-8')
    (pkg / 'evaluation' / 'controllers' / 'sdmpc_dual.py').write_text(DRY.PKG_DUAL, encoding='utf-8')
    for role, name in (('adapter', ADAPTER), ('worker', WORKER)):
        for variant, pre in (('plain', ''), ('reload', RELOAD)):
            d = SYN / ('prog_%s_%s' % (role, variant))
            d.mkdir(parents=True)
            (d / name).write_text(DRY.BOOT + pre + DRY.CHILD, encoding='utf-8')
    tree = SYN / 'tree'
    tree.mkdir(parents=True)
    shutil.copy2(GWT8_SA / 'k92_record.py', tree / 'k92_record.py')
    if sha(tree / 'k92_record.py') != RECORDER_SHA:
        raise SystemExit('recorder copy differs')
    return tree / 'k92_record.py'


def env_for(hook, hd, rec, case, fake=None):
    code_dir, want = HOOKS[hook]
    if sha(code_dir / 'sitecustomize.py') != want:
        raise SystemExit('hook bytes differ: %s' % hook)
    extra = {'PYTHONPATH': os.pathsep.join([str(code_dir), str(SYN / 'pkg')]), 'K92VB_HOOK_DIR': str(hd),
             'K92VB_RECORDER': str(rec), 'K92VB_RECORDER_SHA256': RECORDER_SHA, 'K92VB_T': '3000',
             'K92VB_SEED': '41', 'K92VB_LABEL': 'rev33/%s' % case}
    if fake:
        extra['DRY33_SITE_LATE'] = '1'
        for k, v in fake.items():
            if v is not None:
                extra['DRY33_FAKE_' + k] = str(v)
    return DRY.clean_env(extra)


def argv_for(role, variant, mode, out, fake):
    name = ADAPTER if role == 'adapter' else WORKER
    script = SYN / ('prog_%s_%s' % (role, variant)) / name
    return [PY, '-B'] + (['-S'] if fake else []) + [str(script), mode, str(out)], script.parent


def run(hook, hd, rec, case, role='worker', variant='plain', mode='normal', fake=None):
    out = SYN / 'out' / (case + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    argv, cwd = argv_for(role, variant, mode, out, fake)
    p = subprocess.run(argv, cwd=str(cwd), env=env_for(hook, hd, rec, case, fake), capture_output=True, text=True,
                       timeout=600)
    o = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else None
    return {'rc': p.returncode, 'pid': (o or {}).get('pid_seen'), 'results': (o or {}).get('results'),
            'err': p.stderr[-400:]}


def judge(hd, case_dir, g3=23.588):
    act = DRY.out_action(case_dir / 'dec' / 'action_003000.json', g3)
    rc_s, sel = DRY.run_select(hd, act, case_dir / 'rec')
    i7 = DRV.vbi7(hd, case_dir / 'rec')
    rs = RCL.reselect(hd, json.loads(act.read_text(encoding='utf-8')), 3000)
    ri7 = RCL.i7_of(hd, case_dir / 'rec')
    lst = DRY.hook_listing(hd)
    toks = DRY.tokens_of(lst)
    c_toks = sorted({re.match(r'^c_(.+)_[0-9]{4,}$', c).group(1) for c in lst['candidates']})
    lpid = {}
    for n in lst['loaded']:
        j = json.loads((hd / n).read_text(encoding='utf-8'))
        lpid[n[len('loaded_'):-len('.json')]] = j.get('pid')
    cand_pid_ok = all(json.loads((hd / c / 'cand.json').read_text(encoding='utf-8')).get('pid') ==
                      lpid.get(re.match(r'^c_(.+)_[0-9]{4,}$', c).group(1)) for c in lst['candidates']
                      if (hd / c / 'cand.json').is_file())
    return {'n_loaded': len(lst['loaded']), 'n_candidates': len(lst['candidates']), 'errors': lst['errors'],
            'setup_errors': lst['setup_errors'], 'names_token_form': DRY.names_ok(lst), 'tokens': len(toks),
            'tokens_unique': len(toks) == len(set(toks)),
            'every_candidate_token_has_loaded': set(c_toks) <= set(toks), 'cand_pid_eq_loaded_pid': cand_pid_ok,
            'select_rc': rc_s, 'select_status': (sel or {}).get('status'), 'n_match': (sel or {}).get('n_match'),
            'chosen': ((sel or {}).get('chosen') or {}).get('folder'), 'vbi7': i7['ok'], 'vbi7_checks': i7['checks'],
            'recalc_status': rs['status'], 'recalc_i7': ri7['ok'],
            'select_eq_recalc': (sel or {}).get('status') == rs['status'] and
            ((sel or {}).get('chosen') or {}).get('folder') == rs.get('chosen')}


def case_r1(rec, hook, n):
    cd = SYN / ('r1_%s' % hook)
    hd = cd / 'hook'
    hd.mkdir(parents=True)
    runs = [run(hook, hd, rec, 'r1_%s_adapter' % hook, role='adapter', mode='idle')]
    t0 = time.perf_counter()
    for i in range(n):
        runs.append(run(hook, hd, rec, 'r1_%s_w%03d' % (hook, i)))
    pids = [r['pid'] for r in runs]
    seen, reused = {}, 0
    for p in pids:
        seen[p] = seen.get(p, 0) + 1
    reused = sum(v - 1 for v in seen.values() if v > 1)
    j = judge(hd, cd)
    j.update(processes=len(runs), rcs_zero=all(r['rc'] == 0 for r in runs), distinct_pids=len(seen),
             pid_reuse_events=reused, pids_reused=sorted(p for p, v in seen.items() if v > 1)[:20],
             sec=round(time.perf_counter() - t0, 1),
             results_same=len({json.dumps(r['results']) for r in runs[1:]}) == 1)
    if hook == 'new':
        j['ok'] = (j['rcs_zero'] and j['results_same'] and j['n_loaded'] == n + 1 and j['tokens_unique']
                   and j['n_candidates'] == 3 * n and not j['errors'] and not j['setup_errors']
                   and j['names_token_form'] and j['every_candidate_token_has_loaded'] and j['cand_pid_eq_loaded_pid']
                   and j['select_status'] == 'selected' and j['vbi7'] and j['recalc_i7'] and j['select_eq_recalc'])
    else:
        # control: old names are per pid, so loaded files = distinct pids; without reuse no error and 3 per worker
        j['ok'] = (j['rcs_zero'] and j['results_same'] and j['n_loaded'] == len(seen)
                   and (reused > 0 or (not j['errors'] and j['n_candidates'] == 3 * n)))
        j['old_collision_seen'] = reused > 0 and (bool(j['errors']) or j['n_loaded'] < n + 1)
    return j


def case_r2(rec):
    cd = SYN / 'r2_new'
    hd = cd / 'hook'
    hd.mkdir(parents=True)
    runs = [run('new', hd, rec, 'r2_adapter', role='adapter', mode='idle')]
    fake = {'PID': 4242, 'NS': 1761111111000000000}
    procs = []
    for i in range(12):
        out = SYN / 'out' / ('r2_w%02d.json' % i)
        argv, cwd = argv_for('worker', 'plain', 'threads', out, fake)
        procs.append((subprocess.Popen(argv, cwd=str(cwd), env=env_for('new', hd, rec, 'r2_w%02d' % i, fake),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), out))
    rcs, pids = [], []
    for p, out in procs:
        p.communicate(timeout=600)
        rcs.append(p.returncode)
        o = json.loads(out.read_text(encoding='utf-8')) if out.is_file() else {}
        pids.append(o.get('pid_seen'))
    j = judge(hd, cd, g3=20.0)
    j.update(rcs=rcs, pids_seen=sorted(set(pids)))
    j['ok'] = (runs[0]['rc'] == 0 and rcs == [0] * 12 and pids == [4242] * 12 and j['n_loaded'] == 13
               and j['tokens_unique'] and j['n_candidates'] == 48 and not j['errors'] and not j['setup_errors']
               and j['names_token_form'] and j['every_candidate_token_has_loaded'] and j['n_match'] == 12
               and j['select_status'] == 'selected' and j['vbi7'] and j['recalc_i7'] and j['select_eq_recalc'])
    return j


def case_r3(rec):
    out = {}
    for hook in ('new', 'old'):
        for role in ('worker', 'adapter'):
            cd = SYN / ('r3_%s_%s' % (hook, role))
            hd = cd / 'hook'
            hd.mkdir(parents=True)
            runs = []
            if role == 'worker':
                runs.append(run(hook, hd, rec, 'r3_%s_%s_adapter' % (hook, role), role='adapter', mode='idle'))
            runs.append(run(hook, hd, rec, 'r3_%s_%s' % (hook, role), role=role, variant='reload', mode='normal'))
            j = judge(hd, cd)
            j['rcs'] = [r['rc'] for r in runs]
            out['%s_%s' % (hook, role)] = j
    n_w, n_a, o_w, o_a = out['new_worker'], out['new_adapter'], out['old_worker'], out['old_adapter']
    # expected: new hook, worker -> two tokens in one process, duplicate candidates of the same calls, no error,
    # selected (the duplicates hold the same record); adapter -> two adapter 'loaded' files -> VB-I7 false (STOP side).
    # old hook -> loaded overwritten and the second counter collides -> hook_error (STOP side).
    out['expect'] = {'new_worker_dup_no_error_selected': n_w['n_loaded'] == 3 and n_w['n_candidates'] == 6 and
                     not n_w['errors'] and n_w['select_status'] == 'selected' and n_w['vbi7'],
                     'new_adapter_vbi7_false': n_a['vbi7'] is False and n_a['vbi7_checks']['c1_loaded'] is False,
                     'old_worker_stop_side': o_w['vbi7'] is False and o_w['select_status'] == 'hook_error',
                     'old_adapter_stop_side': o_a['vbi7'] is False}
    out['ok'] = all(out['expect'].values()) and all(x['rcs'] == [0] * len(x['rcs']) for k, x in out.items()
                                                    if isinstance(x, dict) and 'rcs' in x)
    return out


def case_r4(rec):
    cd = SYN / 'r4_new'
    hd = cd / 'hook'
    hd.mkdir(parents=True)
    runs = [run('new', hd, rec, 'r4_adapter', role='adapter', mode='idle')]
    same = {'PID': 4242, 'NS': 1761111111000000000, 'RAND': '00112233aabbccdd'}
    runs.append(run('new', hd, rec, 'r4_w0', fake=same))
    before = {str(p.relative_to(hd)): sha(p) for p in sorted(hd.rglob('*')) if p.is_file()}
    runs.append(run('new', hd, rec, 'r4_w1', fake=same))
    runs.append(run('new', hd, rec, 'r4_w2', fake={'PID': 4242, 'NS': 1761111111000000000, 'RAND': 'ffeeddccbbaa9988'}))
    after = {str(p.relative_to(hd)): sha(p) for p in sorted(hd.rglob('*')) if p.is_file()}
    j = judge(hd, cd)
    j['first_files_unchanged'] = all(after.get(k) == v for k, v in before.items())
    j['n_first_files'] = len(before)
    j['rcs'] = [r['rc'] for r in runs]
    j['ok'] = (j['rcs'] == [0] * 4 and j['first_files_unchanged'] and len(j['setup_errors']) == 1
               and j['select_status'] == 'hook_error' and j['vbi7'] is False and j['recalc_i7'] is False
               and j['n_loaded'] == 3 and j['n_candidates'] == 6)
    return j


def main(argv):
    if argv[:1] != ['all']:
        print(__doc__)
        return 2
    n = int(argv[1]) if len(argv) > 1 else 120
    bn = below_normal()
    rec = build()
    res = {'below_normal': bn, 'tool_sha256': sha(__file__), 'when_start': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'hook_new': NEW_HOOK_SHA, 'hook_old': OLD_HOOK_SHA, 'select': sha(AD32 / 'vb_select.py') == SELECT_SHA}
    for name, fn in (('R1_new', lambda: case_r1(rec, 'new', n)), ('R1o_old', lambda: case_r1(rec, 'old', n)),
                     ('R2', lambda: case_r2(rec)), ('R3', lambda: case_r3(rec)), ('R4', lambda: case_r4(rec))):
        res[name] = fn()
        print('REV33 %s ok=%s' % (name, res[name]['ok']), flush=True)
    res['all_ok'] = bn and res['select'] and all(res[k]['ok'] for k in ('R1_new', 'R1o_old', 'R2', 'R3', 'R4'))
    res['when_end'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / 'rev_a33.json'
    p.write_text(json.dumps(res, indent=1, sort_keys=True, default=repr) + '\n', encoding='utf-8')
    print('REV33 all_ok=%s sha=%s' % (res['all_ok'], sha(p)), flush=True)
    return 0 if res['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
