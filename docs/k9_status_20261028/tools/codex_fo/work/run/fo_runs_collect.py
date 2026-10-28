# -*- coding: utf-8 -*-
"""fo_runs_collect.py - read-only collector for FO_RUNS.md (2026-10-28 KST). Reads the FO launcher records, launcher log,
each seed's wrapper records, watchdog progress, run log, decisions folder listing, .err line counts and file sizes.
Writes one JSON (argv[1]). Seeds are read from run_provenance (not from folder names). No FZP content is read.
"""
import glob, hashlib, json, os, re, statistics, sys

ROOT = 'D:/VISSIM_runs/20261028_codex_fo_v3c3'
FO = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo'
LOG = FO + '/fo_launcher.log'


def jl(p):
    return json.load(open(p, encoding='utf-8-sig'))


def txt(p):
    raw = open(p, 'rb').read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig', errors='replace')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def dirsize(d):
    n = 0
    for dp, dn, fn in os.walk(d):
        for f in fn:
            try:
                n += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return n


def pct(v, q):
    s = sorted(v)
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


out = {'root': ROOT, 'seeds': {}}
ld = ROOT + '/_launcher'
for seed in (31, 41, 43):
    name = 'sdmpc31_sdmpc9000_s%d' % seed
    res = ROOT + '/s%d' % seed
    sd = res + '/sdmpc'
    dec = sd + '/decisions_' + name
    o = {}
    prov = jl(sd + '/run_provenance_' + name + '.json')
    o['provenance_seed'] = prov.get('seed')
    o['provenance_sha256'] = sha(sd + '/run_provenance_' + name + '.json')
    o['tries'] = sorted(os.path.basename(p) for p in glob.glob(ld + '/launched_s%d_run*_try*.json' % seed))
    o['stalled_records'] = sorted(os.path.basename(p) for p in glob.glob(ld + '/stalled_s%d_*.json' % seed))
    rc = jl(ld + '/receipt_s%d_run1_try1.json' % seed)
    o['receipt'] = {k: rc.get(k) for k in ('time_before_create', 'time_after_create', 'ReturnValue', 'ProcessId', 'wrapper_creation',
                                            'PriorityClass', 'vissim_count_before', 'vissim_pids_before', 'pending_before', 'disk_free_gb')}
    o['tryend'] = jl(ld + '/tryend_s%d_run1_try1.json' % seed)
    st = jl(res + '/fo_launch/wrapper_run1_try1_started.json')
    en = jl(res + '/fo_launch/wrapper_run1_try1_end.json')
    o['wrapper_started'] = {k: st.get(k) for k in ('time', 'wrapper_pid', 'wrapper_priority')}
    o['wrapper_end'] = en
    o['wrapper_error_exists'] = os.path.exists(res + '/fo_launch/wrapper_run1_try1_error.json')
    wp = txt(sd + '/WATCHDOG_PROGRESS.txt')
    m = re.findall(r'(?m)^(\S+ \S+)\s+VISSIM_PROCESS ' + name + r' pid=(\d+)', wp)
    o['watchdog_vissim'] = m
    o['watchdog_kill_policy'] = re.findall(r'(?m)^.*KILL_POLICY.*$', wp)[:2]
    o['watchdog_last'] = [l for l in wp.splitlines() if l.strip()][-2:]
    o['watchdog_kill_lines'] = [l for l in wp.splitlines() if re.search(r'KILL|STALL|TIMEOUT', l) and 'KILL_POLICY' not in l][:10]
    rl = txt(sd + '/runlog_' + name + '.txt')
    lines = rl.splitlines()
    o['runlog_lines'] = len(lines)
    o['runlog_markers'] = {k: [(i + 1, l) for i, l in enumerate(lines) if l.startswith(k)][-1:] for k in
                           ('STAGE=SIM_DONE', 'SIM_SEC=', 'DECISIONS_OK=', 'DECISIONS_FAILED=', 'DECISIONS_HELD_PREVIOUS=',
                            'DECISIONS_HELD_ON_EXCEPTION=', 'RUN_MODE=')}
    d = [(int(a), float(b), int(c)) for a, b, c in re.findall(r'(?m)^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', rl)]
    warm = [x for x in d if x[0] < 900]
    ctl = [x for x in d if x[0] >= 900]
    w = [x[1] for x in ctl]
    mx = max(ctl, key=lambda x: x[1])
    o['decisions'] = {'n': len(d), 'warmup_n': len(warm), 'control_n': len(ctl), 'exit_nonzero': sum(1 for x in d if x[2] != 0),
                      'warmup_wall_min': min(x[1] for x in warm), 'warmup_wall_max': max(x[1] for x in warm),
                      'first_control': [x for x in ctl if x[0] == 900],
                      'control_wall': {'n': len(w), 'mean': round(statistics.mean(w), 1), 'median': round(statistics.median(w), 1),
                                       'p90': round(pct(w, 0.9), 1), 'min': min(w), 'max': mx[1], 'max_T': mx[0],
                                       'gt360': sum(1 for x in w if x > 360), 'gt1500': sum(1 for x in w if x > 1500),
                                       'gt3600': sum(1 for x in w if x > 3600)},
                      'hold_attempt_lines': len(re.findall(r'(?m)^DECISION_HOLD_ATTEMPT', rl)),
                      'held_previous_lines': len(re.findall(r'(?m)^DECISION_HELD_PREVIOUS', rl))}
    o['runlog_error_like_lines'] = len([l for l in lines if re.match(r'^(ERROR|FATAL|ABORT|STOP)', l)])
    o['action_json_n'] = len(glob.glob(dec + '/action_[0-9][0-9][0-9][0-9][0-9][0-9].json'))
    o['error_txt_n'] = len(glob.glob(dec + '/action_*.error.txt'))
    ns = jl(res + '/native_status.json')
    o['native_status_stage'] = ns.get('stage')
    errs = {}
    for p in sorted(glob.glob(sd + '/network/*.err')) + sorted(glob.glob(sd + '/*.err')):
        t = txt(p)
        ls = [l for l in t.splitlines() if l.strip()]
        errs[os.path.relpath(p, sd).replace('\\', '/')] = {'lines': len(ls), 'bytes': os.path.getsize(p),
                                                           'warning': sum(1 for l in ls if 'Warning' in l), 'note': sum(1 for l in ls if 'Note' in l),
                                                           'vehicle_input_not_finished': sum(1 for l in ls if 'could not be finished completely' in l)}
    o['err_files'] = errs
    fz = sd + '/vissim_eval/' + name + '_001.fzp'
    o['fzp_bytes'] = os.path.getsize(fz) if os.path.exists(fz) else None
    o['vissim_eval_files'] = sorted(os.listdir(sd + '/vissim_eval')) if os.path.isdir(sd + '/vissim_eval') else []
    o['result_root_bytes'] = dirsize(res)
    out['seeds']['s%d' % seed] = o

# launcher log: polls, seat waits, other VISSIM windows
lg = txt(LOG)
polls = re.findall(r'(?m)^(\S+ \S+) KST \[run pid=\d+\] POLL n=(\d+) vissim=(\d+) \[([^\]]*)\]', lg)
out['launcher'] = {'start': re.findall(r'(?m)^(\S+ \S+) KST .*LAUNCHER_START', lg), 'exit': re.findall(r'(?m)^(\S+ \S+) KST .*LAUNCHER_EXIT.*$', lg),
                   'polls': len(polls), 'max_vissim': max(int(p[2]) for p in polls),
                   'seat_busy_polls': len(re.findall(r'action=SEAT_BUSY', lg)), 'errors': re.findall(r'(?m)^.*\] ERROR .*$', lg)[:5],
                   'launch_stopped': re.findall(r'(?m)^.*LAUNCH_STOPPED.*$', lg), 'launched': re.findall(r'(?m)^(\S+ \S+) KST .*LAUNCHED (s\d+_run\d+_try\d+) ReturnValue=(\d+) wrapper_pid=(\d+) vissim_before=(\d+)', lg),
                   'vissim_wait_end': re.findall(r'(?m)^(\S+ \S+) KST .*VISSIM_WAIT_END (\S+) reason=(\S+) vissim_pid=(\d+) after=(\d+)s', lg),
                   'try_end': re.findall(r'(?m)^(\S+ \S+) KST .*TRY_END (\S+) status=(\S+)', lg),
                   'log_sha256': sha(LOG)}
others = {}
for t, n, cnt, lst in polls:
    for item in lst.split(','):
        if item and ':' not in item:
            others.setdefault(item, []).append(t)
ourmap = {}
for t, n, cnt, lst in polls:
    for item in lst.split(','):
        if ':' in item:
            ourmap.setdefault(item, []).append(t)
ptimes = [p[0] for p in polls]
win = {}
for k, v in others.items():
    i0, i1 = ptimes.index(v[0]), ptimes.index(v[-1])
    win[k] = {'first_seen_poll': v[0], 'poll_before_first': ptimes[i0 - 1] if i0 > 0 else None, 'last_seen_poll': v[-1],
              'first_poll_without': ptimes[i1 + 1] if i1 + 1 < len(ptimes) else None, 'polls': len(v)}
out['launcher']['other_vissim_windows'] = win
out['launcher']['our_vissim_polls'] = {k: [v[0], v[-1], len(v)] for k, v in ourmap.items()}
cnts = {}
for p in polls:
    cnts[p[2]] = cnts.get(p[2], 0) + 1
out['launcher']['vissim_count_hist'] = cnts
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', sys.argv[1])
