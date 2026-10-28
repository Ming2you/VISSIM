"""Read-only: structural diff of two JSON docs (pointer-level), print summary."""
import json, sys
a = json.load(open(sys.argv[1], encoding='utf-8')); b = json.load(open(sys.argv[2], encoding='utf-8'))
out = []
def walk(x, y, p):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x: out.append(('+', p + '/' + k))
            elif k not in y: out.append(('-', p + '/' + k))
            else: walk(x[k], y[k], p + '/' + k)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + '/' + str(i))
    elif x != y:
        out.append(('~', p, repr(x)[:160], repr(y)[:160]))
walk(a, b, '')
print(len(out))
for row in out[:int(sys.argv[3]) if len(sys.argv) > 3 else 60]: print(*row)
