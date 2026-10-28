# B run "normal behaviour" baseline (2026-10-26, before the first B launch). Read-only.
# Gaps between progress signals in already-finished runs of the same codex code (a49981ff):
#  (1) inside a decision: consecutive lines of action_T.joint.progress.jsonl (elapsed_sec), plus decision start -> first line
#  (2) A1 run file mtimes: action_(T-150).csv -> state_T.json (VISSIM simulating 150 s, no decision running)
#      and state_T.json -> first progress line (approx. from elapsed_sec of the first line)
# Inputs: A1 run (64cf-s29) and the four gate-1 replays (v3c3, T=900). Output JSON on stdout.
import json, glob, os, sys, statistics
A1 = r'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
G1 = r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1/out'

def prog_gaps(path):
    el = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                el.append(float(json.loads(line)['elapsed_sec']))
            except Exception:
                pass
    if not el:
        return None
    gaps = [el[0]] + [b - a for a, b in zip(el, el[1:])]
    return {'lines': len(el), 'first': el[0], 'last': el[-1], 'max_gap': max(gaps),
            'max_gap_at_line': gaps.index(max(gaps))}

out = {'a1_progress': {}, 'g1_progress': {}, 'a1_between': []}
for p in sorted(glob.glob(os.path.join(A1, 'action_*.joint.progress.jsonl'))):
    out['a1_progress'][os.path.basename(p)] = prog_gaps(p)
for p in sorted(glob.glob(os.path.join(G1, '*', '*', 'T000900', 'files', '*', 'action_000900.joint.progress.jsonl'))):
    out['g1_progress'][p.replace('\\', '/').split('/out/')[1]] = prog_gaps(p)
# between decisions (A1): action_(T-150).csv mtime -> state_T.json mtime
Ts = sorted(int(os.path.basename(p)[6:12]) for p in glob.glob(os.path.join(A1, 'state_*.json')))
for a, b in zip(Ts, Ts[1:]):
    pa = os.path.join(A1, 'action_%06d.csv' % a); pb = os.path.join(A1, 'state_%06d.json' % b)
    if os.path.exists(pa) and os.path.exists(pb):
        out['a1_between'].append({'from_T': a, 'to_T': b, 'sec': round(os.path.getmtime(pb) - os.path.getmtime(pa), 1)})
a1g = [v['max_gap'] for v in out['a1_progress'].values() if v]
g1g = [v['max_gap'] for v in out['g1_progress'].values() if v]
bw = [x['sec'] for x in out['a1_between']]
out['summary'] = {
    'a1_decisions_with_progress': len(a1g), 'a1_max_in_decision_gap_sec': round(max(a1g), 1),
    'a1_median_of_max_gap_sec': round(statistics.median(a1g), 1),
    'g1_replays': len(g1g), 'g1_max_in_decision_gap_sec': round(max(g1g), 1),
    'a1_between_n': len(bw), 'a1_between_max_sec': max(bw), 'a1_between_median_sec': statistics.median(bw),
    'a1_between_max_at': [x for x in out['a1_between'] if x['sec'] == max(bw)],
}
json.dump(out, sys.stdout, indent=1)
