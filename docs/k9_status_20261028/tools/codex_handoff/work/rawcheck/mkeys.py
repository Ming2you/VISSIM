import json, re, sys
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
o = json.load(open(f"{D}/{sys.argv[1]}", encoding="utf-8"))
md = o["metadata"]
pat = re.compile(sys.argv[2], re.I)
for k, v in md.items():
    if pat.search(k):
        t = type(v).__name__
        if isinstance(v, (dict, list)):
            s = json.dumps(v)[:300]
            print(f"{k}: {t} len={len(v)} {s}")
        else:
            print(f"{k}: {t} {repr(v)[:200]}")
