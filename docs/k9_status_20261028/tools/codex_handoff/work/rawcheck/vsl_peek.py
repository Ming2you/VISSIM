import json, sys, collections
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
o = json.load(open(f"{D}/{sys.argv[1]}", encoding="utf-8"))
j = o["metadata"]["joint_leader_selection"]
print("coord kinds", collections.Counter(c["kind"] for c in j["coordinates"]))
print("grad kinds", collections.Counter(r["kind"] for r in j["gradient_rows"]))
v = [r for r in j["gradient_rows"] if r["kind"] not in ("green", "offset")]
for r in v[:40]:
    print(json.dumps(r)[:600])
print("policy:", json.dumps({k: j["policy"][k] for k in j["policy"] if "vsl" in k.lower() or "secant" in k.lower() or "tol" in k.lower() or "fd" in k.lower() or "prox" in k.lower() or "step" in k.lower()}))
lr = j["local_rows"]
print("local_rows owners", collections.Counter(r["owner"] for r in lr))
for r in lr:
    if r["owner"] in ("FW_E", "FW_W"):
        print(json.dumps(r)[:1500]); break
