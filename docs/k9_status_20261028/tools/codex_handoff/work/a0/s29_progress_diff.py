# First progress-log line (joint.progress.jsonl) whose non-clock fields differ from a reference.
# Clock fields dropped: elapsed_sec, seconds, and keys ending in _sec. usage: s29_progress_diff.py out.json
import glob, json, os, re, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC
CLOCK = re.compile(r'(?i)(^elapsed_sec$|^seconds$|_sec$)')


def lines(d, T):
    p = d + '/action_%06d.joint.progress.jsonl' % T
    return [json.loads(l) for l in open(p, encoding='utf-8')]


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if not CLOCK.search(k)}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        sx, sy = strip(x), strip(y)
        if sx != sy:
            keys = sorted(k for k in set(sx) | set(sy) if sx.get(k) != sy.get(k))
            return {'line': i, 'stage': x.get('stage'), 'ref_stage': y.get('stage'),
                    'fields': {k: [repr(sx.get(k))[:90], repr(sy.get(k))[:90]] for k in keys[:6]}}
    if len(a) != len(b):
        return {'line': min(len(a), len(b)), 'stage': 'length', 'lengths': [len(a), len(b)]}
    return None


out = []
for st in sorted(glob.glob(A0 + '/out/*/T*/replay_state.json')):
    dd = os.path.dirname(st).replace('\\', '/')
    label, T = dd.split('/')[-2], int(dd[-6:])
    f = dd + '/files/sdmpc/' + DEC
    if not os.path.exists(f + '/action_%06d.joint.progress.jsonl' % T):
        continue
    a = lines(f, T)
    row = {'label': label, 'T': T, 'n_lines': len(a), 'vs_recorded': first_diff(a, lines(REC, T))}
    out.append(row)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out:
    d = r['vs_recorded']
    print(r['label'], r['T'], 'lines', r['n_lines'], '-> same as record' if d is None else ('first diff line %s stage %s %s' % (d['line'], d['stage'], json.dumps(d.get('fields', d.get('lengths')), ensure_ascii=False)[:300])))
