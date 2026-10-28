import json, sys
R='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/%s/T%06d/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.joint.json'
F='D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.joint.json'
label, T, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
lim = int(sys.argv[4]) if len(sys.argv) > 4 else 30
a = json.load(open(R % (label, T, T), encoding='utf-8')); b = json.load(open((sys.argv[5] if len(sys.argv) > 5 else F) % T, encoding='utf-8'))
def get(x, p):
    for s in p.strip('/').split('/'):
        x = x[int(s)] if isinstance(x, list) else x[s]
    return x
out = []
def walk(x, y, p):
    if len(out) >= lim: return
    if isinstance(x, dict) and isinstance(y, dict):
        for k in x:
            if k in y: walk(x[k], y[k], p + '/' + k)
            else: out.append((p + '/' + k, 'only_replay', ''))
        for k in y:
            if k not in x: out.append((p + '/' + k, '', 'only_ref'))
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y): out.append((p, 'len%d' % len(x), 'len%d' % len(y)))
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + '/' + str(i))
    else:
        if not (x == y and type(x) is type(y)) and not (isinstance(x, float) and isinstance(y, float) and repr(x) == repr(y)):
            out.append((p, repr(x)[:100], repr(y)[:100]))
walk(get(a, prefix), get(b, prefix), prefix)
for o in out[:lim]: print(*o, sep='  |  ')
