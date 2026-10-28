import difflib, os, sys, json
solo = r"D:\VISSIM_handoff\20261024\original_code_dependencies\solo"
cw = r"D:\VISSIM-merge\k8_gate_trees\codexhandoff\a49981ff"
frz = r"D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410"
rows = json.load(open(sys.argv[1], encoding="utf-8"))["rows"]
out = []
for r in rows:
    if r["status"] == "same":
        continue
    rel = r["rel"]
    a = os.path.join(cw, rel)
    s = os.path.join(solo, rel)
    if not os.path.isfile(a):
        out.append((rel, "absent_in_codex_a49981ff", None, None))
        continue
    la = open(a, encoding="utf-8", errors="replace").read().splitlines()
    ls = open(s, encoding="utf-8", errors="replace").read().splitlines()
    plus = minus = 0
    for line in difflib.unified_diff(la, ls, lineterm="", n=0):
        if line.startswith("+") and not line.startswith("+++"):
            plus += 1
        elif line.startswith("-") and not line.startswith("---"):
            minus += 1
    out.append((rel, "solo_vs_codexA", plus, minus))
for o in out:
    print(o)
