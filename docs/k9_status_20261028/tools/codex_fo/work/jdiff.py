# Read-only nested JSON diff (FO facts, 2026-10-27). usage: python -B jdiff.py A.json B.json out.txt [labelA labelB]
import json, sys

def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)

def short(v, n=300):
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= n else s[:n] + "...<%d chars>" % len(s)

def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = path + "." + str(k) if path else str(k)
            if k not in a:
                out.append(("ONLY_B", p, None, b[k]))
            elif k not in b:
                out.append(("ONLY_A", p, a[k], None))
            else:
                walk(a[k], b[k], p, out)
    elif a != b:
        out.append(("DIFF", path, a, b))

a, b = load(sys.argv[1]), load(sys.argv[2])
la = sys.argv[4] if len(sys.argv) > 4 else "A"
lb = sys.argv[5] if len(sys.argv) > 5 else "B"
out = []
walk(a, b, "", out)
with open(sys.argv[3], "w", encoding="utf-8") as f:
    f.write("A=%s\nB=%s\nn_diff=%d\n" % (sys.argv[1], sys.argv[2], len(out)))
    for kind, p, x, y in out:
        if kind == "DIFF":
            f.write("DIFF %s\n  %s: %s\n  %s: %s\n" % (p, la, short(x), lb, short(y)))
        elif kind == "ONLY_A":
            f.write("ONLY_%s %s = %s\n" % (la, p, short(x)))
        else:
            f.write("ONLY_%s %s = %s\n" % (lb, p, short(y)))
print(len(out))
