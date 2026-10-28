# per arm: distinct signal plans per SC over decisions, VSL values, RM rates; readback status for signals
import csv, collections, json
R = "D:/VISSIM_handoff/20261024/raw"
out = {}
for arm in ["joint", "window", "off", "freeway_only", "urban_only"]:
    rows = list(csv.DictReader(open(f"{R}/{arm}/sdmpc/action_sdmpc31_sdmpc8100_s29.csv", encoding="utf-8-sig")))
    sig = collections.defaultdict(set); vsl = collections.Counter(); rm = collections.defaultdict(set)
    rb = collections.Counter(); rbk = collections.Counter()
    times = sorted({float(r["sim_sec"]) for r in rows})
    for r in rows:
        k = r["kind"]
        if k == "signal":
            sig[r["id"]].add((r["p1_green"], r["p2_green"], r["p3_green"], r["p4_green"], r["offset"]))
            rb[r["readback"].split("|")[0][:20]] += 1
        elif k == "vsl":
            vsl[(r["speed_kph"], r["readback"])] += 1
        elif k == "ramp_meter":
            rm[r["id"]].add((r["rate_vph"], r["green_sec"]))
        elif k == "signal_sg":
            rbk[r["readback"][:25]] += 1
    out[arm] = dict(times=len(times), first=times[0], last=times[-1],
                    signal_plans_per_sc={k: len(v) for k, v in sorted(sig.items())},
                    vsl=dict((f"{a}|{b}", n) for (a, b), n in vsl.items()),
                    rm_distinct={k: len(v) for k, v in rm.items()}, signal_readback=dict(rb), sg_readback=dict(rbk.most_common(5)))
    print(arm, json.dumps(out[arm])[:900])
json.dump(out, open("act_audit_out.json", "w"), indent=1)
