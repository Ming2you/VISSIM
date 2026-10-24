"""Reproduce the first live observation failure; no rollout, fitting or native calls."""
import ctypes
import json
import os
import pickle
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
PHASE = next((x.split('=',1)[1] for x in sys.argv if x.startswith('--phase=')), 'before')
AT = int(next((x.split('=',1)[1] for x in sys.argv if x.startswith('--at=')), '4500'))
ROLLOUT='--rollout' in sys.argv
assert PHASE in ('before','after','legacy')
NAME = 'first_failure' if PHASE=='before' and AT==4500 else f'{PHASE}_{AT}'
NAME += next((x.split('=',1)[1] for x in sys.argv if x.startswith('--attempt=')), '')
assert not (D / (NAME+'_inputs.json')).exists(), 'Preserve prior evidence'
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ['NUMSIM_REPO_ROOT'] = str(ROOT / 'vendor/NumSim-mine')
os.environ['RW_DECISION_FAIL_FAST'] = '1'
os.environ['RW_MAINLINE_SG_ONLY'] = '1'
os.environ['RW_OFFSET_WRITER'] = 'experiment'
os.environ['RW_RAMP_AMBER_SEC'] = '0'
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.GetCurrentProcess.restype = ctypes.c_void_p
k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
from evaluation.controllers import lane_plant_runtime as lane
original = lane.initialize
if PHASE=='legacy':
    lane.prepare_offramp_projection=lambda *args,**kwargs: {}


def observed(context, observation, cfg, state, detectors, **kwargs):
    counts = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    now = next(f for f in observation['frames'] if f['time_s'] == state.time_sec)
    rows = [v for v in now['vehicles'] if int(v[1]) == 10483]
    owners = counts.get('10483', {})
    stores = {key.split(':', 1)[1] for key in owners if key.startswith('storage:')}
    result = dict(time_sec=state.time_sec, observed_count=len(rows), vehicles=rows,
        assigned=owners, storage_capacity={s:cfg.network.urban_link_storage_veh[s] for s in stores},
        storage_free={s:state.urban_link_storage[s] for s in stores},
        origins=detectors.get('link_to_origins', {}).get('10483'),
        physical_projection=detectors.get('physical_storage_projection',{}),
        projection_diagnostics=state.local_observation_summary['projection_diagnostics'])
    (D / (NAME+'_inputs.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('time_sec','observed_count','assigned','storage_capacity','storage_free','origins')}), flush=True)
    try:
        answer=original(context, observation, cfg, state, detectors, **kwargs)
    except Exception as error:
        tb=error.__traceback__
        details=[]
        while tb:
            if tb.tb_frame.f_code.co_name=='initialize':
                loc=tb.tb_frame.f_locals
                details.append({key:loc.get(key) for key in ('key','removed','used','cap','spacing','moved_by_parent','old_dedicated')})
            tb=tb.tb_next
        (D / (NAME+'_exception.json')).write_text(json.dumps(dict(error=str(error),details=details),indent=2),encoding='utf-8')
        raise
    (D / (NAME+'_state.pkl')).write_bytes(pickle.dumps((state,cfg)))
    result=dict(reservations=context.get('offramp_projection_reservations',{}),
        restored_capacity=cfg.network.urban_link_storage_veh['SC1001_W_out'],
        physical_assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['10483'],
        port_capacity=cfg.network.urban_link_storage_veh['lane_off_10483'],
        port_stock=cfg.network.urban_link_storage_veh['lane_off_10483']-state.urban_link_storage['lane_off_10483'])
    (D / (NAME+'_restored.json')).write_text(json.dumps(result, indent=2),encoding='utf-8')
    print('RESTORED',json.dumps(result),flush=True)
    return answer


lane.initialize = observed
from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
if PHASE=='after' and AT==4500:
    original_replay=probe.replay_vsl_history
    def replay_failed_current(*args,**kwargs):
        return original_replay(*args,**kwargs,allow_missing_current_online=True)
    probe.replay_vsl_history=replay_failed_current
sys.argv = [probe.__file__, f'--at={AT}', '--closedloop-recorded', '--held450' if ROLLOUT else '--initialize-only',
    '--warm-head-history', '--replay-vsl-history', '--probe-label=rm233_projection_'+NAME,
    '--recording-dir=D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json=' + str(D.parent / 'config.json')]
probe.main()
