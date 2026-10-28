import json, sys
D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"
o = json.load(open(f"{D}/{sys.argv[1]}", encoding="utf-8"))
j = o["metadata"]["joint_leader_selection"]
for k, v in j.items():
    s = json.dumps(v)
    print(f"--- {k}: {type(v).__name__} len={len(v) if isinstance(v,(list,dict,str)) else ''} :: {s[:int(sys.argv[2]) if len(sys.argv)>2 else 400]}")
