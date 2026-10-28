import json, os
R = "D:/VISSIM_handoff/20261024/raw"
P = {"nc": f"{R}/nc/run_provenance_sdmpc31_nc9000_s29.json"}
for c in ["joint", "window", "off", "freeway_only", "urban_only"]:
    P[c] = f"{R}/{c}/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json"
D = {k: json.load(open(v, encoding="utf-8-sig")) for k, v in P.items()}
def flat(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, pre + "/" + str(k)))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(flat(v, pre + f"[{i}]"))
    else:
        out[pre] = d
    return out
F = {k: flat(v) for k, v in D.items()}
print("top keys nc:", list(D["nc"].keys()))
print("top keys joint:", list(D["joint"].keys()))
# files sha comparison
def files(d):
    return {k: v.get("sha256") for k, v in d.get("files", {}).items()}
for c in D:
    print(c, "seed", D[c].get("seed"), "period", D[c].get("sim_period_sec"), "controller", D[c].get("controller"), "ctrl_int", D[c].get("control_interval_sec"), "demand_scale", D[c].get("demand_scale"))
fn, fj = files(D["nc"]), files(D["joint"])
print("\nfiles: key | nc sha | joint sha | same")
for k in sorted(set(fn) | set(fj)):
    print(f"  {k:28s} {str(fn.get(k))[:12]:12s} {str(fj.get(k))[:12]:12s} {fn.get(k)==fj.get(k)}")
# signal programs
def sigs(d):
    return {os.path.basename(x["path"].replace("\\", "/")): x["sha256"] for x in d.get("signal_programs", [])}
sn, sj = sigs(D["nc"]), sigs(D["joint"])
print("\nsignal_programs nc", len(sn), "joint", len(sj), "same names", set(sn) == set(sj), "all sha same", all(sn[k] == sj.get(k) for k in sn))
# env
en, ej = D["nc"].get("env", {}), D["joint"].get("env", {})
print("\nenv diff (nc vs joint):")
for k in sorted(set(en) | set(ej)):
    a, b = en.get(k), ej.get(k)
    if a != b:
        print(f"  {k}: nc={str(a)[:90]!r} joint={str(b)[:90]!r}")
    else:
        print(f"  {k}: same {str(a)[:60]!r}")
# cross-arm (joint vs others) files diffs
for c in ["window", "off", "freeway_only", "urban_only"]:
    fc = files(D[c])
    diff = [k for k in sorted(set(fc) | set(fj)) if fc.get(k) != fj.get(k)]
    print(f"\n{c} vs joint files differing: {diff}")
    sc = sigs(D[c]); print("   sig same", sc == sj)
    ec = D[c].get("env", {})
    print("   env differing:", [k for k in sorted(set(ec) | set(ej)) if ec.get(k) != ej.get(k)])
