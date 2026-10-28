import json, sys
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
o = json.load(open(f"{D}/action_{int(sys.argv[1]):06d}.joint.json", encoding="utf-8"))
def walk(x, path, depth):
    if depth > 3: return
    if isinstance(x, dict):
        for k, v in x.items():
            p = path + "/" + k
            if "vsl" in k.lower() or depth < 1:
                s = json.dumps(v)
                print(p, type(v).__name__, (len(v) if isinstance(v, (list, dict)) else ""), s[:300])
            walk(v, p, depth + 1)
walk(o, "", 0)
