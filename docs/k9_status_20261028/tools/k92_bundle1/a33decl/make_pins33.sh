#!/usr/bin/env bash
# Declare A33: writes AD33/a33_pins.expected.sha256 (amendment 33 section 7).  sha256sum lines "<sha> *<abs path>".
set -u
SP='C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'; KB="$SP/k92/bundle1"; OK2='D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1'; G='D:/VISSIM-merge/sim3-n31-k8'; SA="$G/diagnostics/sdmpc_n31_20260924/k8_gates/sa"; RR='D:/VISSIM_runs/20261004_sdmpc31_k8'
files=(
"$KB/a33decl/vbhook/sitecustomize.py" "$KB/a32decl/vb_select.py" "$KB/a32decl/vb_lib32.py" "$KB/a32decl/vb_closed_leaves.json"
"$KB/k92_vb2/vb_chain.py" "$KB/k92_vb2/vb_recalc.py" "$KB/k92_vb2/selftest/vb_selftest.json" "$KB/k92_vb2/selftest/vb_recalc_selftest.json"
"$KB/a33decl/dry_a33.py" "$KB/a33decl/run_bn.py"
"$KB/a33decl/dry/decl/dry_a33_static.json" "$KB/a33decl/dry/decl/dry_a33_hook.json" "$KB/a33decl/dry/decl/dry_a33_pidreuse.json" "$KB/a33decl/dry/decl/dry_a33_paths.json" "$KB/a33decl/dry/decl/dry_a33_mutants.json" "$KB/a33decl/dry/decl/dry_a33_summary.json"
"$KB/a33decl/diff/hook.diff" "$KB/a33decl/diff/vb_chain.diff" "$KB/a33decl/diff/vb_recalc.diff"
"$KB/a32decl/vbhook/sitecustomize.py" "$KB/a32decl/a32_pins.expected.sha256" "$KB/a32_pins.sha256"
"$KB/k92_vb/vb_chain.py" "$KB/k92_vb/vb_recalc.py" "$KB/k92_vb/vb_pins.sha256"
"$KB/k92_vb/K92_VB_REPORT_stop_r1.md" "$KB/VB_REPORT_stop_r1.md" "$OK2/vb/K92_VB_REPORT.md"
"$OK2/vb/STOP_vb_V5.json" "$OK2/vb/judge/vb_i1.json" "$OK2/vb/judge/vb_reportonly.json" "$OK2/vb/chain/vb41_off/hook/t003150/hook_error_26704.txt"
"D:/VISSIM-merge/k8_gate_trees/k92b1/vb_e27ceac8.build.json"
"$SP/K8_PREDECLARATION_AMENDMENT_32.md" "$KB/AMENDMENT32_FIXED.md" "$KB/k92_probe_a25/K92_VALUES.json"
"$KB/GATES_K92B1_A31.md" "$KB/VERIFY_GATES_K92B1_r3.md" "$KB/vgates4/out/vg4_result.json" "$KB/a31_pins.sha256"
"$KB/impl/k92lib.py" "$KB/impl/cglib.py" "$KB/impl/launch.ps1" "$KB/impl/k92snap.py"
"$SP/j1/fix/gates/gprep.py" "$SP/j1/fix/gates/gcommon.py"
"$SA/k92_compare.py" "$SA/k92_record.py" "$SA/k92_replay.py" "$SA/sa_arms.py" "$SA/k92_a27.py" "$SA/k92_common.py"
"$G/evaluation/controllers/sdmpc.py" "$G/scripts/run_real_world_stackelberg_controller.vbs" "$G/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py"
"D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py"
"$RR/sdmpc31_v3c3_k8j1r_s31/decisions_sdmpc31_v3c3_k8j1r_s31/action_003000.json.applied"
"$RR/sdmpc31_v3c3_k8j1_s43/decisions_sdmpc31_v3c3_k8j1_s43/action_003000.json.applied"
"$RR/sdmpc31_v3c3_k8j1_s41/decisions_sdmpc31_v3c3_k8j1_s41/action_003000.json.applied"
"$RR/sdmpc31_v3c3_k8j1_s41/decisions_sdmpc31_v3c3_k8j1_s41/action_000900.json.applied"
"$RR/sdmpc31_v3c3_k8j1_s41/decisions_sdmpc31_v3c3_k8j1_s41/action_002850.json.applied"
"$OK2/snap/s42_a33decl.json"
"$KB/a33decl/make_pins33.sh"
)
out="$KB/a33decl/a33_pins.expected.sha256"; : > "$out"
for f in "${files[@]}"; do sha256sum "$f" >> "$out" || { echo "FAIL $f"; exit 1; }; done
echo "lines=$(wc -l < "$out") sha=$(sha256sum "$out" | cut -c1-64) notok=$(sha256sum -c "$out" | grep -vc ': OK$')"
