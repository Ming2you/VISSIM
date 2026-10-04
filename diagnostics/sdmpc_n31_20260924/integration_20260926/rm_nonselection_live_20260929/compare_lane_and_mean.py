"""Bounded saved-state diagnosis: exact timing, mean RM, full SDMPC surrogate.

Hooks are process-local observers, except the explicitly labelled existing
continuous-prediction mode. No native run, calibration or production edits.
"""
import ctypes
from ctypes import wintypes
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import pickle
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
path = BASE/'probe_selected_arrival_path.py'
spec = importlib.util.spec_from_file_location('lane_mean_diagnostic_helper', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
original_probe = helper.probe_levers
TARGET = 'RM_C10681'
MODES = ('execution', 'cycle_mean_rm', 'sdmpc_surrogate')
CASES = ('held_actual', 'meter_RM_C10681_flat8', 'meter_RM_C10681_progressive')


def instrument(captured, reference, output, **options):
    from src.controllers import rollout_endpoint
    from evaluation.controllers import lane_ramp_runtime, sdmpc_continuous
    from evaluation.controllers import signal_actuation_contract, physical_ramp_branches
    from evaluation.controllers.lane_urban_runtime import CandidateSignalProgram
    cfg, state = captured['cfg'], captured['state']
    initial_hash = hashlib.sha256(pickle.dumps(state, protocol=5)).hexdigest()
    buffer = state.lane_ramp_runtime.buffers[TARGET]
    initial = dict(buffer_metadata=buffer.metadata(), buffer_snapshot=buffer.snapshot(),
        lane_snapshots=[b.snapshot() for b in buffer._lane_buffers],
        receiving_node=state.lane_ramp_runtime.receiving_nodes.get(TARGET),
        lane_coupling=state.lane_ramp_runtime.lane_coupling.get(TARGET),
        ramp_config=cfg.network.physical_ramp_branches['ramps'][TARGET],
        future_observations_used=False, initial_state_pickle_sha256=initial_hash)
    (output/'lane_initial.json').write_text(json.dumps(initial,ensure_ascii=False,indent=2),encoding='utf-8')
    original_endpoint = rollout_endpoint.evaluate_price_point
    original_advance = lane_ramp_runtime.LaneRampRuntime.advance
    original_phase = signal_actuation_contract.phase_fraction
    original_prepare = physical_ramp_branches.prepare_control
    original_state_at = CandidateSignalProgram.state_at
    original_fraction = getattr(CandidateSignalProgram, 'service_fraction_at', None)
    had_flag = hasattr(cfg.network, '_sdmpc_continuous_prediction')
    original_flag = getattr(cfg.network, '_sdmpc_continuous_prediction', None)
    lane_rows = []
    calls = []
    mode = None

    def trace_advance(self, *args, **kwargs):
        result = original_advance(self, *args, **kwargs)
        lane_rows.append(result[2][TARGET])
        return result

    def trace_endpoint(*args, **kwargs):
        lane_rows.clear()
        point = original_endpoint(*args, **kwargs)
        assert len(lane_rows)==450
        index = sum(r['mode']==mode for r in calls)
        name = CASES[index]
        with gzip.open(output/(mode+'_'+name+'_lanes.json.gz'),'wt',encoding='utf-8',compresslevel=1) as stream:
            json.dump(lane_rows,stream,ensure_ascii=False)
        calls.append(dict(mode=mode,case=name,omega_ttt_veh_h=point.ttt))
        return point

    lane_ramp_runtime.LaneRampRuntime.advance = trace_advance
    rollout_endpoint.evaluate_price_point = trace_endpoint
    try:
        for mode in MODES:
            mode_output = output/mode
            mode_output.mkdir()
            if mode=='cycle_mean_rm':
                cfg.network._sdmpc_continuous_prediction = True
            elif mode=='sdmpc_surrogate':
                sdmpc_continuous.install(cfg)
            original_probe(captured,reference,mode_output,**options)
            assert hashlib.sha256(pickle.dumps(state,protocol=5)).hexdigest()==initial_hash
    finally:
        lane_ramp_runtime.LaneRampRuntime.advance = original_advance
        rollout_endpoint.evaluate_price_point = original_endpoint
        signal_actuation_contract.phase_fraction = original_phase
        physical_ramp_branches.prepare_control = original_prepare
        CandidateSignalProgram.state_at = original_state_at
        if original_fraction is None:
            if hasattr(CandidateSignalProgram,'service_fraction_at'):
                delattr(CandidateSignalProgram,'service_fraction_at')
        else:
            CandidateSignalProgram.service_fraction_at = original_fraction
        if had_flag: cfg.network._sdmpc_continuous_prediction = original_flag
        else: delattr(cfg.network,'_sdmpc_continuous_prediction')
    assert len(calls)==9
    prior = BASE/'closedloop_recorded3600_lever450_live29_rm_diagnosis_v1'
    for row in calls[:3]:
        old=json.loads((prior/(row['case']+'.json')).read_bytes())
        assert abs(row['omega_ttt_veh_h']-old['ttt_omega_veh_h'])<1e-9
    saved=json.loads((HERE/'saved_solver_evidence.json').read_bytes())
    observed=next(r['held_objective'] for r in saved['records'] if r['sim_sec']==3600)
    assert abs(calls[6]['omega_ttt_veh_h']-observed)<1e-7
    (output/'mode_comparison_receipt.json').write_text(json.dumps(dict(calls=calls,
        unchanged_execution_reproduced=True,stored_sdmpc_surrogate_reproduced=True,
        production_changed=False,native_runs=0,calibration=False),indent=2),encoding='utf-8')


helper.probe_levers = instrument
sys.argv = [str(path),'--closedloop-recorded','--at=3600',
    '--recording-dir=E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json='+str(BASE/'sc1001_sources_20260929/candidate_config.json'),
    '--warm-head-history','--lever-probe450','--meter-ramp='+TARGET,
    '--probe-label=live29_lane_mean_v2']
helper.main()
