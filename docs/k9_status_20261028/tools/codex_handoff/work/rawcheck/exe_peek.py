import json
B = "D:/VISSIM_handoff/20261024/analysis/comparison"
for arm in ["joint", "freeway_only", "urban_only"]:
    e = json.load(open(f"{B}/{arm}/execution.json", encoding="utf-8"))
    print("=====", arm, "keys:", [k for k in e.keys()][:40])
    for k in ("passed", "native_execution_passed", "native_lsa_com_coverage_passed", "terminal_sec", "run_id"):
        print("  ", k, e.get(k))
    ch = e.get("checks", {})
    for k, v in ch.items():
        if isinstance(v, dict):
            s = {kk: vv for kk, vv in v.items() if not isinstance(vv, (dict, list))}
            print("   check", k, json.dumps(s, ensure_ascii=False)[:400])
        else:
            print("   check", k, repr(v)[:200])
