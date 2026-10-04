"""Read-only current-state inventory for full-Omega distance implementation."""
import ctypes
import hashlib
import json
from pathlib import Path
import sys
from collections import deque

from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
from evaluation.controllers import runtime_setup, obs150_contract as oc
from evaluation.controllers.control_area_objective import get_ledger

HERE = Path(__file__).resolve().parent


def compact(value, depth=0):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): compact(v, depth+1) for k,v in value.items()}
    if isinstance(value, (tuple, list, deque)):
        return [compact(v, depth+1) for v in value]
    if isinstance(value, (set, frozenset)):
        return [compact(v, depth+1) for v in sorted(value, key=str)]
    if not hasattr(value, '__dict__'):
        return dict(class_name=type(value).__name__, unexpanded=True)
    if depth > 4:
        return dict(class_name=type(value).__name__, fields=sorted(vars(value)))
    return dict(class_name=type(value).__name__, fields=compact(vars(value), depth+1))


def main():
    k = ctypes.windll.kernel32
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    output = HERE/'distance_state3600.json'
    assert not output.exists()
    captured, pins = {}, {}
    original, writer = runtime_setup.configure_runtime, oc.write_derived
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.update(state=result[0],cfg=args[1])
        return result
    def read_only(raw, derived):
        obs=raw[oc.RAW_STATE_KEY]; p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        return p
    runtime_setup.configure_runtime,oc.write_derived=capture,read_only
    try:
        tuning=probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
        sys.argv=[str(Path(probe.__file__)), '--closedloop-recorded','--at=3600',
            '--initialize-only','--warm-head-history','--replay-vsl-history',
            '--recording-dir=D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
            '--tuning-json='+str(tuning),'--probe-label=fullomega_distance_inventory_r2']
        probe.main()
    finally:
        runtime_setup.configure_runtime,oc.write_derived=original,writer
    state,cfg=captured['state'],captured['cfg']
    net=cfg.network
    fields=('urban_movement_queue','urban_link_storage','urban_link_speed_kph',
        'urban_arrival_buffer','urban_storage_release_buffer','urban_inflow_transit_buffer',
        'offramp_transit_buffer','route_choice_corridor_state','native_input_prehead_state',
        'native_internal_input_state','physical_gate_travel_state','known_legsplit_state',
        'direct_exit_legsplit_state','sc2001_corridor_state','shared_approach_state',
        'local_observation_summary')
    data=dict(time_sec=state.time_sec,state_fields=sorted(vars(state)),
        state={f:compact(getattr(state,f,None)) for f in fields},
        stocks=compact(get_ledger(state).stocks),network={})
    keys=('control_area_routes','urban_movements','urban_link_storage_veh','urban_link_length_km',
        'urban_link_length_m','physical_gate_travel','known_legsplit_routes','direct_exit_legsplit',
        'route_choice_corridor','native_internal_inputs','sc2001_corridor','shared_approach',
        'physical_ramp_branches','control_area_membership','control_area_model_stock_supports')
    data['network']={key:compact(getattr(net,key,None)) for key in keys}
    data['runtime']={name:compact(getattr(state,name,None)) for name in
        ('lane_ramp_runtime','lane_offramp_runtime','lane_urban_runtime')}
    data['coverage_keys']=[key for key in vars(net) if any(x in key for x in ('area','travel','length','route','transit'))]
    data['pins']=pins
    for p,h in pins.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    data.update(native_runs=0,forecast_rollouts=0,model_changes=0)
    output.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(path=str(output),stocks=len(data['stocks']),state_fields=len(data['state_fields']))),flush=True)


def fixed_initial_transport():
    """Reuse the saved snapshot; separate initial ETA constants from responses."""
    from evaluation.controllers.omega_distance import urban_path_catalog
    from types import SimpleNamespace as NS
    snapshot=HERE/'distance_state3600.json';data=json.loads(snapshot.read_bytes())
    net=data['network'];state=data['state'];stocks=data['stocks']
    assignments=state['local_observation_summary']['projection_diagnostics']['physical_stock_assignment_by_link']
    arrivals=state['urban_arrival_buffer'];releases=state['urban_storage_release_buffer']
    physical=set(net['route_choice_corridor']['capacity_veh'])
    for key in ('shared_approach','sc2001_corridor','known_legsplit_routes','direct_exit_legsplit'):
        physical.add(net[key]['storage'])
    runtime=data['runtime']['lane_urban_runtime']['fields']
    physical.add(runtime['origin']);physical.update(runtime['local_storage'].values());physical.add(runtime['off_storage'])
    physical.update(row['storage'] for row in data['runtime']['lane_offramp_runtime']['fields']['descriptions'].values())
    ordinary={key:row for key,row in releases.items() if row and key not in physical}
    starts=[(link,key) for key in ordinary for link,row in assignments.items() if row.get('storage:'+key,0)>0]
    network=HERE.parent.parent/'selected/network/native_seed29.inpx'
    cfg=NS(network=NS(**net));catalog=urban_path_catalog(network,cfg,initial_starts=starts)
    rows=[]
    for key,row in ordinary.items():
        n=sum(row.values());support={link:amounts['storage:'+key] for link,amounts in assignments.items() if amounts.get('storage:'+key,0)>0}
        rows.append(dict(stock=key,scheduled_veh=n,inside_veh=stocks.get('storage:'+key,{}).get('inside',0),
            paired_arrival_release=row==arrivals.get(key,{}),physical_assignment_veh=sum(support.values()),
            due_times=list(row),support=support,
            unreachable_assignments={link:catalog['initial_errors'][link+'|'+key] for link in support if link+'|'+key in catalog['initial_errors']}))
    result=dict(status='initial_transport_scope_audit_not_objective_qualification',rows=rows,
        total_initial_veh=sum(r['scheduled_veh'] for r in rows),
        unpaired=[r['stock'] for r in rows if not r['paired_arrival_release']],
        stock_projection_discrepancies=[r['stock'] for r in rows if abs(r['scheduled_veh']-r['physical_assignment_veh'])>1e-7],
        potential_common_constant='Existing ordinary initial reservations expire at fixed ETA, before signal service. Their pre-head travel can cancel in candidate differences only after proving the whole accepted-transport chain and same-origin cohort ownership. This audit does not yet authorize dropping or inventing absolute distance.',
        full_omega_scoring_enabled=False,forecasts=0,native_runs=0,
        pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (snapshot,network,Path(__file__))})
    out=HERE/'initial_transport_audit.json';assert not out.exists()
    out.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(stocks=len(rows),vehicles=result['total_initial_veh'],unpaired=result['unpaired'],
        projection_discrepancies=result['stock_projection_discrepancies'],unreachable=sum(len(r['unreachable_assignments']) for r in rows))))


if __name__ == '__main__':
    fixed_initial_transport() if '--fixed-initial-transport' in sys.argv else main()
