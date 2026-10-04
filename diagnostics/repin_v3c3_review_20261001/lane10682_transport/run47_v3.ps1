$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='C:\Users\alsrj\Desktop\학술\찐찐막\Codex\VISSIM\.review-deps\sdmpc;.;vendor/NumSim-mine'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py --at=2700 --closedloop-recorded --selection-check --warm-head-history --replay-vsl-history --trace-ramp=RM_C10681 '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47' --fixed-replay-summary=diagnostics/sdmpc_n31_20260924/integration_20260926/native_rm_observation2700_writerfix_v3/analysis/summary.json --selection-reference=diagnostics/sdmpc_n31_20260924/integration_20260926/closedloop_recorded2700_select_sc1001_corrected47 --tuning-json=diagnostics/repin_v3c3_review_20261001/lane10682_transport/candidate_config.json --probe-label=lane10682_transport_47v3 *> diagnostics/repin_v3c3_review_20261001/lane10682_transport/run47_v3.log
exit $LASTEXITCODE

