import difflib, os, sys
solo = r"D:\VISSIM_handoff\20261024\original_code_dependencies\solo"
frz = r"D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410"
files = ["area_follower_objective.py","joint_owner_neighbors.py","runtime_setup.py","sdmpc.py","sdmpc_budget.py","sdmpc_central.py","sdmpc_pfo.py","sdmpc_sequence.py","sdmpc_tangent.py","sdmpc_tangent_constraints.py","sdmpc_tangent_surrogate.py","sdmpc_tangent_worker.py","vissim_stackelberg_adapter.py"]
out = open(sys.argv[1], "w", encoding="utf-8")
for f in files:
    rel = "evaluation/controllers/" + f
    a = open(os.path.join(frz, rel), encoding="utf-8").read().splitlines()
    b = open(os.path.join(solo, rel), encoding="utf-8").read().splitlines()
    for line in difflib.unified_diff(a, b, "FRZB1/" + rel, "SOLO/" + rel, lineterm="", n=2):
        out.write(line + "\n")
out.close()
