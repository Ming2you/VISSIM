# Read-only: compare code-file sha256 across three FREEZE manifests (FO facts, 2026-10-27).
# SOLO = codex solo freeze (2f28000a, freeway_only/urban_only), JOINT = codex joint freeze (ca181e84 dirty),
# FRZB1 = our FRZ_B1 (a49981ff + B0 patches + B1 runner). Code = .py/.ps1/.vbs/.yaml/.yml/.psm1 under
# evaluation/, scripts/, vendor/, tools/, harness/, plant/ and the integration runner folder.
import json, sys
P = {
    "SOLO": r"D:\VISSIM_handoff\20261024\evidence\original_solo_FREEZE.json",
    "JOINT": r"D:\VISSIM_handoff\20261024\evidence\original_FREEZE.json",
    "FRZB1": r"D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410\FREEZE.json",
}
EXT = (".py", ".ps1", ".vbs", ".yaml", ".yml", ".psm1")
PRE = ("evaluation/", "scripts/", "vendor/", "tools/", "harness/", "plant/",
       "diagnostics/sdmpc_n31_20260924/integration_20260926/run_")
F = {k: json.load(open(v, encoding="utf-8-sig"))["files"] for k, v in P.items()}

def code(files):
    return {p: s for p, s in files.items() if p.endswith(EXT) and p.startswith(PRE) and "/tests/" not in p and not p.startswith("vendor/NumSim-mine/tests")}

C = {k: code(v) for k, v in F.items()}
out = {"manifests": P, "counts": {k: len(v) for k, v in C.items()}}
def cmp(a, b):
    A, B = C[a], C[b]
    only_a = sorted(set(A) - set(B)); only_b = sorted(set(B) - set(A))
    diff = sorted(p for p in set(A) & set(B) if A[p] != B[p])
    return {"only_" + a: only_a, "only_" + b: only_b, "differs": diff}
out["SOLO_vs_JOINT"] = cmp("SOLO", "JOINT")
out["SOLO_vs_FRZB1"] = cmp("SOLO", "FRZB1")
out["JOINT_vs_FRZB1"] = cmp("JOINT", "FRZB1")
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
for k in ("SOLO_vs_JOINT", "SOLO_vs_FRZB1", "JOINT_vs_FRZB1"):
    v = out[k]
    print(k, {kk: len(vv) for kk, vv in v.items()})
    for kk, vv in v.items():
        if len(vv) <= 40:
            for p in vv:
                print("   ", kk, p)
