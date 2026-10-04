"""One unchanged held rollout; intercept its existing response for diagnosis only."""
import ctypes
from ctypes import wintypes
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
path = BASE / 'probe_selected_arrival_path.py'
spec = importlib.util.spec_from_file_location('rm_saved_response_probe', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
original_probe = helper.probe_levers
calls = []


def instrument(captured, reference, output, **options):
    from src.controllers import rollout_endpoint
    endpoint = rollout_endpoint.evaluate_price_point

    def record(*args, **kwargs):
        point = endpoint(*args, **kwargs)
        response = point.control_area_response
        net = captured['cfg'].network
        catalog = {m:dict(owner=s['signal'], kind=s['kind'])
                   for m,s in net.urban_movements.items() if s['signal'] in net.signals}
        assert len(net.signals) == 17
        served = {m:0. for m in catalog}
        for row in response['transfers']:
            key = row['route_key']
            if isinstance(key, str) and key.startswith('movement:') and key[9:] in served:
                served[key[9:]] += row['vehicles']
        assert all(abs(v-point.control_area['flow_counts'].get('movement:'+m,0.))<1e-7
                   for m,v in served.items())
        signs = dict(boundary_in=1, off_ramp=1, boundary_out=-1, on_ramp=-1, internal=0)
        q = dict(movement_catalog=catalog, served_by_movement_veh=served,
                 np_veh=sum(signs[catalog[m]['kind']]*v for m,v in served.items()),
                 nonowner_service_included=False, movement_flow_counts_match=True)
        rows = [r for r in response['resource_allocations']
                if r['kind'].startswith('physical_ramp_')]
        record = dict(ttt_omega_veh_h=point.ttt, quantities=q,
            ramps=captured['cfg'].network.physical_ramp_branches['ramps'],
            resources=rows, no_physics_or_actuation_changes=True)
        (HERE/'held_resource_trace.json').write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        calls.append(point.ttt)
        return point

    rollout_endpoint.evaluate_price_point = record
    try:
        return original_probe(captured, reference, output, **options)
    finally:
        rollout_endpoint.evaluate_price_point = endpoint


helper.probe_levers = instrument
sys.argv = [str(path), '--closedloop-recorded', '--at=3600',
    '--recording-dir=E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json='+str(BASE/'sc1001_sources_20260929/candidate_config.json'),
    '--warm-head-history', '--held450', '--probe-label=live29_rm_resource_v1']
helper.main()
baseline = json.loads((BASE/'closedloop_recorded3600_lever450_live29_rm_diagnosis_v1/held_actual.json').read_bytes())
assert len(calls) == 1 and abs(calls[0]-baseline['ttt_omega_veh_h']) < 1e-9
print(json.dumps(dict(unchanged_held_rollout=True, count=len(calls))), flush=True)
