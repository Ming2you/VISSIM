#!/bin/bash
# Pin list writer for PRE_VP_FIXED (Git Bash; review r2).  Writes VP/SHA256SUMS_VP.txt (relative paths, check with
# `sha256sum -c` in VP) and VP/SHA256SUMS_VP_EXT.txt (absolute paths of reused tools and outputs, the zone-definition
# source, the code-copy record and the smoke v5 records).  r1 lists are kept as SHA256SUMS_VP_r1.txt / _EXT_r1.txt.
set -e
VP="C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant"
SP="C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8"
GT="D:/VISSIM-merge/k8_gate_trees/vsl_plant"
cd "$VP"
sha256sum tools/vp_common.py tools/vp_states.py tools/vp_tree.py tools/vp_fzp.py tools/vp_pinned.py tools/vp_probe.py \
  tools/vp_hooks/sitecustomize.py tools/vp_job.py tools/vp_queue.py tools/vp_launch.ps1 tools/vp_jobcheck.py \
  tools/vp_analyze.py tools/vp_selftest.py tools/vp_smokecheck.py tools/vp_tablesmoke.py tools/vp_pin.sh \
  decl/VP_STATES.json decl/VP_FZP_SOURCES.json decl/jobs_fzp.json decl/specs/jobs_A.json decl/specs/spec_A_*.json \
  smoke/specs/spec_smoke_v5.json smoke/jobs_pre5.json smoke/jobcheck_v5.json smoke/tablesmoke_v5.json \
  smoke/smokecheck_v5.json selftest/selftest_final_r2.json PRE_VP_r1.md > SHA256SUMS_VP.txt
sha256sum "$SP/vsl_v3c3/tools/vsl_cell_scan.py" "$SP/vsl_v3c3/o1o2/tools/o2_fzp_cells.py" \
  "$SP/vsl_v3c3/o1o2/tools/o_analyze.py" "$SP/j1/fix/gates/gprep.py" \
  "$SP/vsl_v3c3/out/cell/nc3_s31.json" "$SP/vsl_v3c3/out/cell/nc3_s41.json" "$SP/vsl_v3c3/out/cell/nc3_s43.json" \
  "$SP/vsl_v3c3/out/cell/vsl_s31.json" "$SP/vsl_v3c3/out/cell/vsl_s41.json" "$SP/vsl_v3c3/out/cell/vsl_s43.json" \
  "D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833/FREEZE.json" "$GT/code_va.tree.json" \
  "D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py" \
  "$GT/smoke/s31_T002400_v5/probe.json" "$GT/smoke/s31_T002400_v5/job_summary.json" > SHA256SUMS_VP_EXT.txt
wc -l SHA256SUMS_VP.txt SHA256SUMS_VP_EXT.txt
