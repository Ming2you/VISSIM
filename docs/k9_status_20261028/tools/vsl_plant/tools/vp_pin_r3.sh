#!/bin/bash
# Pin list writer for PRE_VP_R3 (Git Bash; data-after amendment r3, user decisions D-K9-108 / D-K9-109).
# Writes VP/SHA256SUMS_VP_r3.txt (relative paths, check with `sha256sum -c` in VP) and VP/SHA256SUMS_VP_EXT_r3.txt
# (absolute paths).  Against r2 (vp_pin.sh, SHA256SUMS_VP.txt / _EXT.txt, kept as records):
#   - VP list: the three r3 tools (vp_probe, vp_jobcheck, vp_queue) with new bytes, their r2 bytes (*_r2.py), the new
#     vp_treefields.py and this script, decl/R3_MARKS.json, the r3 self-test and patch-test records, the r2 -> r3 diffs,
#     PRE_VP_FIXED.md and the two r2 lists;
#   - EXT list: the r2 EXT list without GT/code_va.tree.json (H0 rewrites its time field, D-K9-109 (3));
#     its ok / count fields are checked by tools/vp_treefields.py instead.
# Refuses to overwrite existing r3 lists.
set -e
VP="C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant"
SP="C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8"
GT="D:/VISSIM-merge/k8_gate_trees/vsl_plant"
PY="C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
cd "$VP"
if [ -e SHA256SUMS_VP_r3.txt ] || [ -e SHA256SUMS_VP_EXT_r3.txt ]; then echo "r3 lists exist (never overwritten)"; exit 3; fi
sha256sum tools/vp_common.py tools/vp_states.py tools/vp_tree.py tools/vp_fzp.py tools/vp_pinned.py tools/vp_probe.py \
  tools/vp_hooks/sitecustomize.py tools/vp_job.py tools/vp_queue.py tools/vp_launch.ps1 tools/vp_jobcheck.py \
  tools/vp_analyze.py tools/vp_selftest.py tools/vp_smokecheck.py tools/vp_tablesmoke.py tools/vp_pin.sh \
  tools/vp_pin_r3.sh tools/vp_treefields.py tools/vp_probe_r2.py tools/vp_jobcheck_r2.py tools/vp_queue_r2.py \
  decl/VP_STATES.json decl/VP_FZP_SOURCES.json decl/jobs_fzp.json decl/specs/jobs_A.json decl/specs/spec_A_*.json \
  decl/R3_MARKS.json \
  smoke/specs/spec_smoke_v5.json smoke/jobs_pre5.json smoke/jobcheck_v5.json smoke/tablesmoke_v5.json \
  smoke/smokecheck_v5.json selftest/selftest_final_r2.json selftest/selftest_amend_r3.json \
  review_r3/r3_patchtest.py review_r3/r3_patchtest.json review_r3/diff_vp_probe_r2_r3.txt \
  review_r3/diff_vp_jobcheck_r2_r3.txt review_r3/diff_vp_queue_r2_r3.txt \
  PRE_VP_r1.md PRE_VP_FIXED.md SHA256SUMS_VP.txt SHA256SUMS_VP_EXT.txt > SHA256SUMS_VP_r3.txt
sha256sum "$SP/vsl_v3c3/tools/vsl_cell_scan.py" "$SP/vsl_v3c3/o1o2/tools/o2_fzp_cells.py" \
  "$SP/vsl_v3c3/o1o2/tools/o_analyze.py" "$SP/j1/fix/gates/gprep.py" \
  "$SP/vsl_v3c3/out/cell/nc3_s31.json" "$SP/vsl_v3c3/out/cell/nc3_s41.json" "$SP/vsl_v3c3/out/cell/nc3_s43.json" \
  "$SP/vsl_v3c3/out/cell/vsl_s31.json" "$SP/vsl_v3c3/out/cell/vsl_s41.json" "$SP/vsl_v3c3/out/cell/vsl_s43.json" \
  "D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833/FREEZE.json" \
  "D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py" \
  "$GT/smoke/s31_T002400_v5/probe.json" "$GT/smoke/s31_T002400_v5/job_summary.json" > SHA256SUMS_VP_EXT_r3.txt
wc -l SHA256SUMS_VP_r3.txt SHA256SUMS_VP_EXT_r3.txt
sha256sum -c SHA256SUMS_VP_r3.txt | grep -vc ': OK$' || true
sha256sum -c SHA256SUMS_VP_EXT_r3.txt | grep -vc ': OK$' || true
"$PY" -B tools/vp_treefields.py
sha256sum SHA256SUMS_VP_r3.txt SHA256SUMS_VP_EXT_r3.txt
