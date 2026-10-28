# B decision concurrency (2026-10-26, read-only on run folders). usage: python -B b_concurrency.py <out.json> [<other_vissim_windows.json>]
# For each B run (v3c3-s31/s41/s43) and each decision T >= 900: start = mtime of decisions/state_<T>.json,
# end = mtime of decisions/action_<T>.decision_budget.json (falls back to action_<T>.json), wall = run log CONTROLLER_DECISION wall_sec.
# Concurrency over [start, end]: mean number of B decisions running at the same time (this one included, time-weighted)
# and the max. Other-session VISSIM windows (v2): JSON list of {pid, start_min, start_max, end_min, end_max} as 'YYYY-MM-DD HH:MM:SS' KST
# (end_* null = still running at the last check). Per decision and window: 'yes' if surely inside, 'no' if surely outside, else 'unknown';
# other_vissim_n = number of 'yes' windows, other_vissim = 'yes' (>=1 yes), 'no' (all no), else 'unknown'.
# Without the file: the v1 rule for 29264 only (seen 21:11:10, gone 21:19:32).
import os, re, sys, json, glob, statistics, datetime
OUTF = sys.argv[1]
ROOT = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
SEEN = datetime.datetime(2026, 10, 26, 21, 11, 10).timestamp()
GONE = datetime.datetime(2026, 10, 26, 21, 19, 32).timestamp()
WINDOWS = None
if len(sys.argv) > 2:
    def _ts(x):
        return None if x is None else datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S').timestamp()
    with open(sys.argv[2], encoding='utf-8') as f:
        WINDOWS = [{k: (_ts(w.get(k)) if k != 'pid' else w.get(k)) for k in ('pid', 'start_min', 'start_max', 'end_min', 'end_max')} for w in json.load(f)]
iv = {}
for s in (31, 41, 43):
    name = 'sdmpc31_sdmpc9000_s%d' % s
    sd = '%s/s%d/sdmpc' % (ROOT, s)
    dec = sd + '/decisions_' + name
    walls = {}
    rl = sd + '/runlog_' + name + '.txt'
    if os.path.exists(rl):
        with open(rl, encoding='utf-8', errors='replace') as f:
            for l in f:
                m = re.match(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)', l)
                if m:
                    walls[int(m.group(1))] = (float(m.group(2)), int(m.group(3)))
    rows = []
    for p in sorted(glob.glob(dec + '/state_*.json')):
        m = re.search(r'state_(\d+)\.json$', p)
        if not m:
            continue
        t = int(m.group(1))
        if t < 900:
            continue
        e = dec + '/action_%06d.decision_budget.json' % t
        if not os.path.exists(e):
            e = dec + '/action_%06d.json' % t
        if not os.path.exists(e):
            continue
        rows.append({'seed': s, 't': t, 'start': os.path.getmtime(p), 'end': os.path.getmtime(e),
                     'wall': walls.get(t, (None, None))[0], 'exit': walls.get(t, (None, None))[1]})
    iv[s] = rows
allrows = [r for s in iv for r in iv[s]]
for r in allrows:
    a, b = r['start'], r['end']
    pts = sorted({a, b} | {x for o in allrows if o is not r for x in (o['start'], o['end']) if a < x < b})
    acc = 0.0; mx = 1
    for u, v in zip(pts, pts[1:]):
        mid = (u + v) / 2
        n = 1 + sum(1 for o in allrows if o is not r and o['start'] <= mid < o['end'])
        acc += n * (v - u); mx = max(mx, n)
    r['mean_concurrent_b'] = round(acc / (b - a), 2) if b > a else None
    r['max_concurrent_b'] = mx
    if WINDOWS is None:
        r['other_vissim'] = 'yes' if b <= SEEN else ('no' if a >= GONE else 'unknown')
    else:
        marks = []
        for w in WINDOWS:
            s0, s1, e0, e1 = w['start_min'], w['start_max'], w['end_min'], w['end_max']   # e0/e1 None = still running
            if s1 <= a and e0 is not None and b <= e0:
                marks.append('yes')                       # surely running during the whole decision
            elif s1 <= a and e0 is None and e1 is None:
                marks.append('yes')                       # still running at the last check, started before
            elif (e1 is not None and e1 <= a) or b <= s0:
                marks.append('no')                        # surely gone before / started after
            else:
                marks.append('unknown')
        r['other_vissim_marks'] = marks
        r['other_vissim_n'] = marks.count('yes')
        r['other_vissim'] = 'yes' if 'yes' in marks else ('no' if all(m == 'no' for m in marks) else 'unknown')
    r['start_kst'] = datetime.datetime.fromtimestamp(a).strftime('%H:%M:%S')
    r['end_kst'] = datetime.datetime.fromtimestamp(b).strftime('%H:%M:%S')


def stats(ws):
    ws = [w for w in ws if w is not None]
    if not ws:
        return None
    return {'n': len(ws), 'mean': round(statistics.mean(ws), 1), 'median': round(statistics.median(ws), 1), 'min': min(ws), 'max': max(ws)}


summ = {}
for s in iv:
    rs = iv[s]
    summ['s%d' % s] = {
        'all': stats([r['wall'] for r in rs]),
        'other_vissim_yes': stats([r['wall'] for r in rs if r['other_vissim'] == 'yes']),
        'other_vissim_no': stats([r['wall'] for r in rs if r['other_vissim'] == 'no']),
        'other_vissim_unknown': stats([r['wall'] for r in rs if r['other_vissim'] == 'unknown']),
        'mean_concurrent_b': stats([r['mean_concurrent_b'] for r in rs]),
        'by_max_concurrent_b': {k: stats([r['wall'] for r in rs if r['max_concurrent_b'] == k]) for k in (1, 2, 3)},
    }
with open(OUTF, 'w', encoding='utf-8') as f:
    json.dump({'summary': summ, 'decisions': allrows}, f, indent=1)
print(json.dumps(summ))
