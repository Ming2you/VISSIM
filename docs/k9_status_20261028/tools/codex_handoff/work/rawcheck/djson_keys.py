import json, sys, time
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
def summarize(o, pre="", depth=0, maxd=3):
    if isinstance(o, dict):
        for k, v in list(o.items())[:80]:
            t = type(v).__name__
            sz = len(v) if isinstance(v, (list, dict, str)) else ""
            sample = "" if isinstance(v, (list, dict)) else repr(v)[:80]
            print("  " * depth + f"{pre}{k}: {t} {sz} {sample}")
            if depth < maxd and isinstance(v, dict):
                summarize(v, "", depth + 1, maxd)
            elif depth < maxd and isinstance(v, list) and v and isinstance(v[0], dict):
                print("  " * (depth + 1) + f"[0] keys: {list(v[0].keys())[:30]}")
for fn in sys.argv[1:]:
    t0 = time.time()
    o = json.load(open(f"{D}/{fn}", encoding="utf-8"))
    print("=====", fn, round(time.time() - t0, 1), "s")
    summarize(o, maxd=int(2))
