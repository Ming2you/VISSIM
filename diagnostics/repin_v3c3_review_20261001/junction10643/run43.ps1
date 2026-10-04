$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='C:\Users\alsrj\Desktop\학술\찐찐막\Codex\VISSIM\.review-deps\sdmpc;.;vendor/NumSim-mine'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py --at=2250 --closedloop-recorded --warm-head-history --replay-vsl-history --trace-ramp=RM_C10681 '--recording-dir=D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43' --four-arm-receipt=diagnostics/sdmpc_n31_20260924/integration_20260926/seed43_fullplant_20260929/analysis_v2/observation_reuse.json --tuning-json=diagnostics/repin_v3c3_review_20261001/junction10643/candidate_config.json --output-suffix=junction10643_43 *> diagnostics/repin_v3c3_review_20261001/junction10643/run43.log
exit $LASTEXITCODE