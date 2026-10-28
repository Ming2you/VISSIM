# Read-only: compare every file of the codex solo code subset with the same relative path in FRZ_B1 (FO facts, 2026-10-27).
# usage: python -B cmp_solo_vs_frz.py SOLO_ROOT FRZ_ROOT OUT_JSON
import hashlib, json, os, sys

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

solo, frz, out = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
for dp, dn, fn in os.walk(solo):
    for n in fn:
        if n == "SHA256SUMS.txt":
            continue
        p = os.path.join(dp, n)
        rel = os.path.relpath(p, solo).replace("\\", "/")
        q = os.path.join(frz, rel)
        a = sha(p)
        b = sha(q) if os.path.isfile(q) else None
        rows.append(dict(rel=rel, solo_sha=a, frz_sha=b,
                         status=("same" if a == b else ("absent_in_frz" if b is None else "differs"))))
rows.sort(key=lambda r: r["rel"])
summary = {}
for r in rows:
    summary[r["status"]] = summary.get(r["status"], 0) + 1
with open(out, "w", encoding="utf-8") as f:
    json.dump(dict(solo_root=solo, frz_root=frz, summary=summary, rows=rows), f, indent=1, ensure_ascii=False)
print(json.dumps(summary))
for r in rows:
    if r["status"] != "same":
        print(r["status"], r["rel"])
