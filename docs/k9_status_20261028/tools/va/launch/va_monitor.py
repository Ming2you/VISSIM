"""V-A blind monitor (amendment 34 sec.6.3).  READ ONLY toward the run folders.

python -B va_monitor.py <out.json> [--seeds 31,41,43] [--min-age 300]   (test only: --rva --live --pattern)

Per run RVA\\sdmpc31_v3c3_k92va_s<S> it prints / writes ONLY: decision T list and count; runlog CONTROLLER_DECISION
exit= and wall_sec; NATIVE_SIM_PROGRESS and RUN_CONTINUOUS_BREAK last sim_sec; presence / size / mtime of files; hold lines
(DECISION_HOLD_ATTEMPT, DECISION_HELD_ON_EXCEPTION, ERROR=) count, sim_sec and first token; hold receipt outer / root
type names and the first message line with digits masked; STAGE= and EXIT lines; runner launch-log SEAT / START /
REFUSED / EXIT / WATCHDOG_EXIT lines; NOT_LAUNCHED.txt; ages of the newest runlog / launch-log / decision-folder change;
whether the launch cmd.exe (PID + creation time from VA/launch/launch_s<S>.json) is alive; the S-VA-7 stall flag
(all three ages > 4800 s, no EXIT line, cmd alive); PC-wide VISSIM count and window titles; health booleans of the
latest VA/launch/health_s<S>_T*.json.  It never reads objective values, predictions, prices, green times, Omega,
TTT, delays (watch_sdmpc.py is not used).  Logs are snapshot copies into REPVA\\live\\<run>\\monitor\\<stamp>\\;
decision-folder files (hold receipts) are copied only when older than --min-age seconds.
"""
import csv
import ctypes
import datetime
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

sys.dont_write_bytecode = True
RVA = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
LIVE = r'D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_va\live'
LAUNCH = os.path.dirname(os.path.abspath(__file__))
STALL_SEC = 4800
DIGITS = re.compile(r'\d+(?:\.\d+)?')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def snap(src, dst_dir):
    if not os.path.isfile(src):
        return None
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    for _ in range(3):
        s1 = sha(src)
        shutil.copyfile(src, dst)
        if s1 == sha(src) == sha(dst):
            return dst
        time.sleep(2)
    return None


def lines_of(p):
    if not p:
        return []
    with io.open(p, encoding='utf-8', errors='replace') as f:
        return f.read().splitlines()


def age(p):
    return round(time.time() - os.path.getmtime(p), 1) if os.path.exists(p) else None


def proc_alive(pid, created_iso):
    """True when a process with this PID exists and its creation time is within 3 s of the recorded one."""
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = wintypes.DWORD()
        if k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != 259:  # STILL_ACTIVE
            return False
        c, e, kk, u = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kk), ctypes.byref(u)):
            return False
        ft = (c.dwHighDateTime << 32) | c.dwLowDateTime
        created = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(microseconds=ft // 10)
        want = datetime.datetime.fromisoformat(created_iso)
        return abs((created - want).total_seconds()) < 3.0
    finally:
        k.CloseHandle(h)


def vissim_list():
    try:
        out = subprocess.run(['tasklist', '/v', '/fo', 'csv', '/fi', 'IMAGENAME eq VISSIM*'], capture_output=True,
                             timeout=60).stdout.decode('mbcs', errors='replace')
    except Exception as e:  # noqa: BLE001
        return {'error': str(e)}
    rows = [r for r in csv.reader(io.StringIO(out)) if r and r[0].lower().startswith('vissim')]
    return {'count': len(rows), 'pids_titles': [(r[1], r[-1]) for r in rows],
            'dev': sum(1 for r in rows if re.search('obs150|sdmpc|probe', r[-1]))}


def monitor_run(seed, stamp, min_age, rva=RVA, live=LIVE, pattern='sdmpc31_v3c3_k92va_s%d'):
    name = pattern % seed
    run = os.path.join(rva, name)
    dec = os.path.join(run, 'decisions_' + name)
    r = {'name': name, 'run_dir_exists': os.path.isdir(run), 'not_launched_txt': os.path.isfile(os.path.join(run, 'NOT_LAUNCHED.txt'))}
    lj = os.path.join(LAUNCH, 'launch_s%d.json' % seed)
    if os.path.isfile(lj):
        info = json.load(io.open(lj, encoding='utf-8-sig'))
        r['cmd_pid'] = info.get('pid')
        r['cmd_alive'] = proc_alive(info['pid'], info['created']) if info.get('pid') and info.get('created') else None
    else:
        r['cmd_pid'] = r['cmd_alive'] = None
    if not r['run_dir_exists']:
        return r
    cdir = os.path.join(live, name, 'monitor', stamp)
    rl = lines_of(snap(os.path.join(run, 'runlog_%s.txt' % name), cdir))
    la = lines_of(snap(os.path.join(run, 'launch_%s.log' % name), cdir))
    cd = []
    for line in rl:
        m = re.match(r'CONTROLLER_DECISION sim_sec=(\d+)', line)
        if m:
            e = re.search(r'exit=(-?\d+)', line)
            w = re.search(r'wall_sec=([0-9.]+)', line)
            cd.append([int(m.group(1)), int(e.group(1)) if e else None, float(w.group(1)) if w else None])
    r['controller_decisions'] = cd
    prog = [x for x in rl if x.startswith('NATIVE_SIM_PROGRESS')]
    m = re.search(r'sim_sec=(\d+)', prog[-1]) if prog else None
    r['last_native_sim_sec'] = int(m.group(1)) if m else None
    br = [x for x in rl if x.startswith('RUN_CONTINUOUS_BREAK')]
    mb = re.search(r'actual_sim_sec=(\d+)', br[-1]) if br else None
    r['last_break_sim_sec'] = int(mb.group(1)) if mb else None

    def hl(prefix):
        o = []
        for x in rl:
            if prefix in x:
                mm = re.search(r'sim_sec=(\d+)', x)
                o.append([int(mm.group(1)) if mm else None, x.split()[0] if x.split() else ''])
        return o
    r['hold_attempt'] = hl('DECISION_HOLD_ATTEMPT')
    r['held'] = hl('DECISION_HELD_ON_EXCEPTION')
    r['error_lines'] = hl('ERROR=')
    r['stage_lines'] = [x[:120] for x in rl if x.startswith('STAGE=') or x.startswith('DECISIONS_')]
    r['runlog_policy_lines'] = sum(1 for x in rl if x.startswith('DECISION_ERROR_POLICY='))
    r['launch_lines'] = [x[:200] for x in la if re.search(r'  (SEAT|START|REFUSED|EXIT|WATCHDOG_EXIT)\b', x)]
    r['exit_line'] = [x[:200] for x in la if re.search(r'  EXIT %s code=' % re.escape(name), x)]
    names = sorted(os.listdir(dec)) if os.path.isdir(dec) else []
    r['decision_T'] = sorted(int(n[7:13]) for n in names if re.fullmatch(r'action_\d{6}\.json', n))
    r['decisions_count'] = len(r['decision_T'])
    r['error_files'] = [n for n in names if n.endswith('.error.txt')]
    r['hold_error_files'] = [n for n in names if n.endswith('.hold_error.txt')]
    receipts = []
    for n in [n for n in names if n.endswith('.hold.json')]:
        p = os.path.join(dec, n)
        if time.time() - os.path.getmtime(p) < min_age:
            receipts.append({'file': n, 'copied': False, 'reason': 'too_new'})
            continue
        dst = snap(p, os.path.join(cdir, 'hold'))
        ex = (json.load(io.open(dst, encoding='utf-8')).get('exception') or {}) if dst else {}
        receipts.append({'file': n, 'copied': bool(dst), 'type': ex.get('type'), 'root_type': ex.get('root_type'),
                         'message_masked': DIGITS.sub('#', str(ex.get('message_first_line', '')))[:160]})
    r['hold_receipts'] = receipts
    newest = max((os.path.getmtime(os.path.join(dec, n)) for n in names), default=None)
    r['last_files'] = [[n, os.path.getsize(os.path.join(dec, n)),
                        datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dec, n))).strftime('%m-%d %H:%M:%S')]
                       for n in sorted(names, key=lambda n: os.path.getmtime(os.path.join(dec, n)))[-6:]]
    r['age_sec'] = {'runlog': age(os.path.join(run, 'runlog_%s.txt' % name)),
                    'launch_log': age(os.path.join(run, 'launch_%s.log' % name)),
                    'decisions_newest': round(time.time() - newest, 1) if newest else None}
    ages = [v for v in r['age_sec'].values()]
    r['stall_S_VA_7'] = bool(all(a is not None and a > STALL_SEC for a in ages) and not r['exit_line'] and r.get('cmd_alive') is True)
    hs = sorted(glob.glob(os.path.join(LAUNCH, 'health_s%d_T*.json' % seed)))
    if hs:
        h = json.load(io.open(hs[-1], encoding='utf-8'))
        r['health'] = {'file': os.path.basename(hs[-1]), 'all_items_true': h.get('all_items_true'),
                       'failed_items': h.get('failed_items')}
    return r


def main():
    out = sys.argv[1]
    seeds = [int(x) for x in (sys.argv[sys.argv.index('--seeds') + 1] if '--seeds' in sys.argv else '31,41,43').split(',')]
    min_age = int(sys.argv[sys.argv.index('--min-age') + 1]) if '--min-age' in sys.argv else 300
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    res = {'checked_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
           'tool_sha256': sha(os.path.abspath(__file__)), 'vissim': vissim_list(), 'runs': {}}
    # test-only overrides (pre-launch tool test on J1 runs): --rva <root> --live <dir> --pattern <name %d pattern>
    rva = sys.argv[sys.argv.index('--rva') + 1] if '--rva' in sys.argv else RVA
    live = sys.argv[sys.argv.index('--live') + 1] if '--live' in sys.argv else LIVE
    pattern = sys.argv[sys.argv.index('--pattern') + 1] if '--pattern' in sys.argv else 'sdmpc31_v3c3_k92va_s%d'
    for s in seeds:
        res['runs']['s%d' % s] = monitor_run(s, stamp, min_age, rva, live, pattern)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    v = res['vissim']
    print('MONITOR %s vissim=%s dev=%s' % (res['checked_at'], v.get('count'), v.get('dev')))
    for s, r in res['runs'].items():
        if not r.get('run_dir_exists'):
            print('  %s run_dir=absent cmd_alive=%s' % (s, r.get('cmd_alive')))
            continue
        lastcd = r['controller_decisions'][-1] if r['controller_decisions'] else None
        print('  %s decisions=%d last_T=%s last_cd=%s sim_sec=%s/%s holds=%d/%d err_lines=%d errfiles=%d exit=%s cmd_alive=%s '
              'ages=%s stall=%s health=%s' % (
                  s, r['decisions_count'], r['decision_T'][-1] if r['decision_T'] else None, lastcd,
                  r['last_native_sim_sec'], r['last_break_sim_sec'], len(r['hold_attempt']), len(r['held']), len(r['error_lines']),
                  len(r['error_files']), r['exit_line'], r.get('cmd_alive'), r['age_sec'], r['stall_S_VA_7'],
                  (r.get('health') or {}).get('all_items_true')))


if __name__ == '__main__':
    main()
