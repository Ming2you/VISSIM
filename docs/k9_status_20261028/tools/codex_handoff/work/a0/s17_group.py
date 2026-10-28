# group differing leaves by subtree for an action JSON (replay label vs recorded), path-normalized keys skipped
import json, sys, collections
label, T, depth = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
name = sys.argv[4] if len(sys.argv) > 4 else 'action_%06d.json' % T
R = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/%s/T%06d/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/%s' % (label, T, name)
F = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/' + name
a = json.load(open(R, encoding='utf-8')); b = json.load(open(F, encoding='utf-8'))
cnt = collections.Counter(); tot = collections.Counter()
def walk(x, y, p):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y):
            if k in x and k in y: walk(x[k], y[k], p + [k])
            else: cnt['/'.join(map(str, (p + [k])[:depth])) + ' [key]'] += 1
    elif isinstance(x, list) and isinstance(y, list):
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + [i])
        if len(x) != len(y): cnt['/'.join(map(str, p[:depth])) + ' [len]'] += 1
    else:
        key = '/'.join(map(str, p[:depth])); tot[key] += 1
        if not (type(x) is type(y) and (x == y or (isinstance(x, float) and repr(x) == repr(y)))): cnt[key] += 1
walk(a, b, [])
for k, v in sorted(cnt.items(), key=lambda z: -z[1])[:40]: print(v, tot.get(k.split(' [')[0], 0), k)
