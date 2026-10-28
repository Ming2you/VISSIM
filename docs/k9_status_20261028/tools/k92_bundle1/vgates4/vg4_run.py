"""VerifyGates 3 driver: independent verification A31 (amendment 31 section 4.3 V1-V4; user decision D-K9-60).

    python -B vg4_run.py run        (once; detached via vg4launch.ps1; BELOW_NORMAL; PYTHONHASHSEED=0)

Order: guards (amendment 31 / fixation / pin list sha, my tools' sha in the LOG, J / F values fixed, drives >= 8 GB,
VISSIM 0) -> read-only snapshot before -> V4 (archives, C7 sets, C9 sealed top, git / worktree state, CAP bytes) ->
V2 (sealed-root k92_record scan) -> V3 (jb_unit rule from the two logs) -> V1 (G-K4 plant raw rows) -> snapshot
after.  Before the first read of sealed records / G-K4 row files / OUT31 records / the two pytest logs / CAP and its
manifest, an automatic line goes to KB/LOG.md (file, minute, purpose).  Writes only VG4/out and LOG lines.  Never
writes OUTK, OUT31, the sealed root, TREE, GWT8, the repository, V4, frozen trees or run folders.  No VISSIM, COM,
runner, freeze, replay, pytest.  Exit 0 = every V PASS, 3 = a V not PASS (STOP), 4 = a guard false (no data read).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vg4lib as V  # noqa: E402
import vg4_scan as S  # noqa: E402
import vg4_unit as U  # noqa: E402
import vg4_gk4 as G  # noqa: E402
import vg4_keep as K  # noqa: E402

PY = r'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
SNAP = V.KB / 'impl' / 'k92snap.py'
S02 = V.OK2 / 'snap' / 's02_after_probe_stop.json'
TOOLS = [HERE / n for n in ('vg4lib.py', 'vg4_scan.py', 'vg4_unit.py', 'vg4_gk4.py', 'vg4_keep.py', 'vg4_run.py',
                            'vg4launch.ps1')]
UNIT_FILES = ['diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach.py',
              'diagnostics/sdmpc_n31_20260924/tests/test_stopline_wiring.py',
              'diagnostics/sdmpc_n31_20260924/tests/test_stopline_evidence.py',
              'diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach_captured.py']
# OUT31 record sha256 prefixes from the apply report (GATES_K92B1_A31.md / task text); the files must be unchanged
OUT31_PREFIX = {'check31.json': '007d316f', 'scan31.json': '98de5508', 'sealed_records_a31.json': '47f91364',
                'unit31_run.json': '73e2984d', 'unit_judge.json': 'b7e9b649', 'unit31.json': '23591103',
                'chain31.json': '5ca6c428', 'unit_base/unit_b9734abe.log': 'e2aaf860'}


def expected():
    return {'a31': V.A31_SHA256, 'fixed31': V.FIXED31_SHA256, 'pins': V.A31_PINS_SHA256, 'rjg4': V.RJG4_SHA256,
            'cap_manifest': V.CAP_MANIFEST_SHA256, 'out31_prefix': dict(OUT31_PREFIX), 'scope_n': 29,
            'scope_outk_n': 26}


def guards(P, E, tools):
    g = {}
    a31 = V.sha256_or_none(P['A31'])
    try:
        first = Path(P['A31_SHA']).read_text(encoding='utf-8').split()[0]
    except (OSError, IndexError):
        first = None
    try:
        fixed_text = Path(P['FIXED31']).read_text(encoding='utf-8')
    except OSError:
        fixed_text = ''
    g['a31_fixed'] = (a31 == E['a31'] and first == E['a31'] and E['a31'] in fixed_text
                      and V.sha256_or_none(P['FIXED31']) == E['fixed31'])
    g['pins_file'] = V.sha256_or_none(P['A31_PINS']) == E['pins']
    tp = V.tools_pinned(tools)
    g['tools_pinned'] = tp['ok']
    jf = V.jf_fixed()
    g['jf_fixed'] = jf['ok']
    fc, fd = V.free_gb('C:\\'), V.free_gb('D:\\')
    g['disk'] = bool(fc and fd and fc >= 8 and fd >= 8)
    pc = V.count_procs() or {}
    g['vissim_0'] = pc.get('vissim', 1) == 0
    return g, {'tools': tp['tools'], 'jf': jf, 'free_gb': {'C': fc, 'D': fd}, 'procs': pc}


def snapshot(name, P):
    out = Path(P['OUT']) / ('snap_%s.json' % name)
    r1 = subprocess.run([PY, '-B', str(SNAP), 'take', str(out)], capture_output=True, text=True, timeout=1800)
    r2 = subprocess.run([PY, '-B', str(SNAP), 'diff', str(S02), str(out)], capture_output=True, text=True,
                        timeout=600)
    return {'file': str(out), 'take_rc': r1.returncode, 'diff_rc': r2.returncode,
            'diff_line': (r2.stdout.strip().splitlines() or [''])[-1][:300], 'sha256': V.sha256_or_none(out),
            'same_as_s02': r1.returncode == 0 and r2.returncode == 0}


def steps_rc(path, name):
    rcs = []
    try:
        for ln in V.read_text(path).splitlines():
            if not ln.strip():
                continue
            d = json.loads(ln)
            if d.get('name') == name:
                rcs.append(d.get('rc'))
    except (OSError, ValueError):
        return None, 'unreadable'
    return (rcs[0] if len(rcs) == 1 else None), len(rcs)


def v4(P, E, opts):
    r = {}
    r['pins'] = K.check_pins(P)
    r['sets'] = K.check_sets(P)
    r['sealed_top'] = K.check_sealed_top(P)
    r['git'] = opts['git'](P)
    V.log_md('열람 기록: CAP `OK2/k92t/jb/sa/cap/k92t`(파일 목록·크기·바이트 sha256만)과 기준 `KB/a31review/out/'
             'cap_manifest.json`, 목적 = 보충 31 독립 검증 V4')
    man_sha = V.sha256_or_none(P['CAP_MANIFEST'])
    manifest = V.read_json_or(P['CAP_MANIFEST'], None) if man_sha == E['cap_manifest'] else None
    r['cap_manifest_sha_ok'] = man_sha == E['cap_manifest']
    r['cap'] = K.check_cap(P, manifest)
    r['ok'] = (r['pins']['scope_all_same'] and r['pins']['scope_n'] == E['scope_n']
               and r['pins']['scope_outk_n'] == E['scope_outk_n'] and r['sets']['stops_ok']
               and r['sets']['stages_ok'] and r['sets']['judges_ok'] and r['sets']['steps_ok']
               and r['sealed_top']['tops_ok'] and r['sealed_top']['k92t_logs_ok'] and r['git']['ok']
               and r['cap_manifest_sha_ok'] and r['cap']['ok'])
    return r


def v2(P, E, opts):
    V.log_md('열람 기록: 파일 = `OK2/sealed_s47/**/k92_record.json`(seed·vissim·vissim_reason 칸, 도구 메모리 안), '
             '목적 = 보충 31 독립 검증 V2 (봉인 훑기 다시 셈); 그리고 `OK2/a31/scan31.json`·`sealed_records_a31.json`')
    res = S.scan(P['SEALED'])
    j = S.judge(res)
    scan31 = V.read_json_or(Path(P['OUT31']) / 'scan31.json', None)
    sr_path = Path(P['OUT31']) / 'sealed_records_a31.json'
    sr = V.read_json_or(sr_path, None)
    cmp_rows = S.compare_records(res, scan31, sr, V.sha256_or_none(sr_path))
    return {'counts': {'files': res['files'], 's47': res['s47'], 'bad': res['bad']}, 'scan': res, 'judge': j,
            'record_compare': cmp_rows, 'ok': all(j.values()) and all(cmp_rows.values())}


def v3(P, E, opts):
    V.log_md('열람 기록: `OK2/a31/unit_base/unit_b9734abe.log`·`OK2/k92t/jb/sa/unit_k92t.log`(두 pytest 로그 전체)와 '
             '`OK2/a31/unit_judge.json`·`unit31_run.json`·`steps31.jsonl`·`OK2/k92t/steps.jsonl`, 목적 = 보충 31 독립 '
             '검증 V3 (jb_unit 규칙 다시 셈)')
    out31 = Path(P['OUT31'])
    run = V.read_json_or(out31 / 'unit31_run.json', {}) or {}
    rc_steps, n_steps = steps_rc(out31 / 'steps31.jsonl', 'unit31_pytest')
    try:
        meta = V.read_text(Path(P['UB']) / 'unit_b9734abe.meta.txt')
        meta_rc = [ln for ln in meta.splitlines() if ln.startswith('rc=')]
        meta_rc = int(meta_rc[-1][3:]) if meta_rc else None
    except (OSError, ValueError):
        meta_rc = None
    base_rc = run.get('base_rc')
    rc_agree = base_rc == rc_steps == meta_rc and n_steps == 1
    new_rc, n_new = steps_rc(Path(P['OUTK']) / 'steps.jsonl', 'jb_unit')
    roots = [P['WT'], P['TREE'], P['UB'], P['JB'], P['CAP'], P['WT_ADMIN'], P['GIT_DIR_K92']]
    try:
        bt = V.read_text(P['UNIT_LOG_BASE'])
        nt = V.read_text(P['UNIT_LOG_NEW'])
    except OSError as e:
        return {'ok': False, 'error': 'log unreadable: %s' % e}
    mine = U.judge(bt, nt, UNIT_FILES, [str(x) for x in roots], str(P['WT']), str(P['TREE']),
                   base_rc if rc_agree else None, new_rc if n_new == 1 else None)
    rec = V.read_json_or(out31 / 'unit_judge.json', None)
    cmp_rows, np_detail = U.compare_record(mine, rec)
    run_report = {'selection_equal': run.get('selection') == UNIT_FILES, 'wt_head_k8': run.get('wt_head') == V.K8,
                  'wt_git_dir_equal': V.norm_slash(run.get('wt_git_dir') or '').lower().rstrip('/')
                  == V.norm_slash(P['WT_ADMIN']).lower().rstrip('/'),
                  'wt_removed_and_state_same': run.get('wt_removed_and_state_same'),
                  'problem': run.get('problem'), 'report_wt_vs_b9_ref': run.get('report_wt_vs_b9_ref'),
                  'report_wt_status_after_n': (run.get('report_wt_status_after') or {}).get('n')}
    ok = (mine['verdict'] == 'PASS' and all(cmp_rows.values()) and rc_agree and n_new == 1
          and run_report['selection_equal'] and run_report['wt_git_dir_equal']
          and run_report['wt_removed_and_state_same'] is True)
    return {'mine': mine, 'record_compare': cmp_rows, 'non_passed_detail': np_detail,
            'rc': {'base_run_json': base_rc, 'base_steps31': rc_steps, 'base_steps31_lines': n_steps,
                   'base_meta': meta_rc, 'agree': rc_agree, 'new_steps': new_rc, 'new_steps_lines': n_new},
            'run_report': run_report, 'roots': [str(x) for x in roots], 'ok': ok}


def v1(P, E, opts):
    plan = G.row_plan(P)
    files = ['%s/%s' % (V.norm_slash(row[side]), f) for row in plan for side in ('old', 'new') for f in G.FILES]
    V.log_md('열람 기록: G-K4 plant 행 원자료 %d파일 = %s, 그리고 `OK2/a27/judge/rjg4.json`, 목적 = 보충 31 독립 검증 V1 '
             '(D-K9-55·D-K9-60 G-K4 plant 원자료 재계산; v3c3-s31 1,500·v3c3-s43 1,050만, v3c3-s47 잡 0)' % (
                 len(files), '; '.join('`%s`' % f for f in files)))
    mine = G.run_rows(P)
    rj_sha = V.sha256_or_none(P['RJG4'])
    rj = V.read_json_or(P['RJG4'], None) if rj_sha == E['rjg4'] else None
    cmp = G.compare_record(mine, rj)
    return {'rows': mine, 'record_compare': cmp, 'rjg4_sha_ok': rj_sha == E['rjg4'],
            'ok': rj_sha == E['rjg4'] and cmp['all_same']}


def out31_unchanged(P, E):
    rows = {}
    for rel, pre in E['out31_prefix'].items():
        s = V.sha256_or_none(Path(P['OUT31']) / rel)
        rows[rel] = {'sha256': s, 'same_prefix': bool(s) and s.startswith(pre)}
    return {'rows': rows, 'ok': all(r['same_prefix'] for r in rows.values())}


def run(P, E, opts, tools):
    t0 = time.time()
    out = Path(P['OUT'])
    out.mkdir(parents=True, exist_ok=True)
    res = {'schema': 'vg4/v1', 'start': V.now()}
    g, gd = guards(P, E, tools)
    res['guards'], res['guard_detail'] = g, gd
    if not all(g.values()):
        res['verdict'] = 'STOP_GUARD'
        V.write_json(out / opts.get('result_name', 'vg4_result.json'), res)
        print('VG4 guards false: %s' % [k for k, v in g.items() if not v], flush=True)
        return 4
    res['snap_before'] = opts['snap']('before', P)
    res['out31_unchanged'] = out31_unchanged(P, E)
    steps = (('V4', v4), ('V2', v2), ('V3', v3), ('V1', v1))
    for name, fn in steps:
        t = time.time()
        try:
            res[name] = fn(P, E, opts)
        except Exception as exc:  # noqa: BLE001  (a crash is recorded, never hidden)
            res[name] = {'ok': False, 'exception': '%s: %s' % (type(exc).__name__, exc)}
        res[name]['sec'] = round(time.time() - t, 1)
        print('VG4 %s ok=%s sec=%s' % (name, res[name].get('ok'), res[name]['sec']), flush=True)
    res['snap_after'] = opts['snap']('after', P)
    res['procs_end'] = V.count_procs()
    oks = {n: bool(res[n].get('ok')) for n, _ in steps}
    oks['out31_unchanged'] = res['out31_unchanged']['ok']
    oks['snap_before_same'] = bool(res['snap_before'].get('same_as_s02'))
    oks['snap_after_same'] = bool(res['snap_after'].get('same_as_s02'))
    res['oks'] = oks
    res['verdict'] = 'PASS' if all(oks.values()) else 'STOP'
    res['end'] = V.now()
    res['sec'] = round(time.time() - t0, 1)
    sha = V.write_json(out / opts.get('result_name', 'vg4_result.json'), res)
    print('VG4 verdict=%s %s sha256=%s' % (res['verdict'], json.dumps(oks), sha), flush=True)
    if opts.get('log_result', True):
        V.log_md('VerifyGates 3 실행 끝: 판정 %s (%s), 출력 `KB/vgates4/out/%s` sha256 `%s`' % (
            res['verdict'], ', '.join('%s=%s' % (k, v) for k, v in oks.items()),
            opts.get('result_name', 'vg4_result.json'), sha))
    return 0 if res['verdict'] == 'PASS' else 3


def main():
    try:
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:  # noqa: BLE001
        pass
    if len(sys.argv) != 2 or sys.argv[1] != 'run':
        print(__doc__)
        return 2
    if os.environ.get('PYTHONHASHSEED') != '0':
        print('PYTHONHASHSEED must be 0')
        return 2
    if (Path(V.P['OUT']) / 'vg4_result.json').exists():
        print('vg4_result.json exists: the run is made once')
        return 2
    opts = {'git': K.check_git, 'snap': snapshot}
    return run(V.P, expected(), opts, TOOLS)


if __name__ == '__main__':
    raise SystemExit(main())
