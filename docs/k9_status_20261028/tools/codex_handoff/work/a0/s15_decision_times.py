# Decision wall-time distributions from runlogs (CONTROLLER_DECISION wall_sec, sim_sec >= 900).
import glob, json, re, statistics
pat = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
runs = {}
for arm in ('joint', 'off', 'window', 'urban_only', 'freeway_only'):
    for f in glob.glob('D:/VISSIM_handoff/20261024/raw/' + arm + '/sdmpc/runlog_*.txt'):
        runs['codexPC:' + arm] = f
runs['thisPC:W264'] = glob.glob('D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/runlog_*.txt')[0]
out = {}
for k, f in runs.items():
    vals, exits = [], {}
    held = 0
    for line in open(f, encoding='utf-8', errors='replace'):
        m = pat.match(line)
        if m and int(m.group(1)) >= 900:
            vals.append((int(m.group(1)), float(m.group(2))))
            exits[m.group(3)] = exits.get(m.group(3), 0) + 1
        if line.startswith('DECISION_HELD_PREVIOUS'):
            held += 1
    w = [v for _, v in vals]
    if not w:
        out[k] = {'file': f, 'n': 0}
        continue
    ws = sorted(w)
    out[k] = {'file': f, 'n': len(w), 'mean': round(statistics.mean(w), 1), 'median': round(statistics.median(w), 1),
              'p90': round(ws[int(0.9 * (len(ws) - 1))], 1), 'max': round(max(w), 1), 'min': round(min(w), 1), 'sum': round(sum(w), 1),
              'over_1800': sum(v > 1800 for v in w), 'over_600': sum(v > 600 for v in w), 'exit_codes': exits, 'held_lines': held,
              'by_T': {str(t): v for t, v in vals if t in (900, 2700, 4950)}}
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0/decision_times.json', 'w', encoding='utf-8'), indent=1)
for k, v in out.items():
    print(k, {a: b for a, b in v.items() if a != 'file'})
