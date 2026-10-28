import os, collections
R = "D:/VISSIM_handoff/20261024/raw"
for c in ["joint/sdmpc", "nc", "window/sdmpc", "off/sdmpc", "freeway_only/sdmpc", "urban_only/sdmpc"]:
    base = f"{R}/{c}"
    ext = collections.Counter(); sz = collections.Counter()
    big = []
    for dp, dn, fn in os.walk(base):
        for f in fn:
            p = os.path.join(dp, f).replace("\\", "/")
            s = os.path.getsize(p)
            e = os.path.splitext(f)[1].lower()
            ext[e] += 1; sz[e] += s
            if "decisions_" not in p and not f.endswith(".sig"):
                big.append((p[len(base)+1:], s))
    print("==", c, dict(ext))
    for p, s in sorted(big):
        print(f"   {s:>14,d}  {p}")
