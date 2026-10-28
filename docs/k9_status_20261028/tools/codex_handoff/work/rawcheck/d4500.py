import json, collections
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
o = json.load(open(f"{D}/action_004500.json", encoding="utf-8"))
j = o["metadata"]["joint_leader_selection"]
coords = collections.defaultdict(list)
for c in j["coordinates"]: coords[c["owner"]].append(c)
print("candidates:", json.dumps(j["candidates"])[:1500])
for lr in j["local_rows"]:
    if lr["owner"] in ("FW_E",):
        cs = coords[lr["owner"]]
        print("cap", round(lr["cap"], 1), "it", lr["iteration"], lr.get("message"), "keys", sorted(lr.keys()))
        for c, g, e, p, s in zip(cs, lr["own_gradient"], lr["externality_gradient"], lr["price_gradient"], lr["step"]):
            if c["kind"] == "vsl":
                print(f"   {c['key']:12s} b{c['block']} own {g:8.4f} ext {e:8.4f} price {p:8.4f} step {s:8.4f}")
print("trial_rows:")
for t in j["trial_rows"]:
    print("  ", round(t["cap"], 1), t["iteration"], t.get("feasible"), round(t["objective"], 4) if t.get("objective") is not None else None, t["action_token"][:10])
print("iteration_dual_updates:", json.dumps(j["iteration_dual_updates"])[:1200])
print("price_state:", json.dumps(j["price_state"])[:600])
