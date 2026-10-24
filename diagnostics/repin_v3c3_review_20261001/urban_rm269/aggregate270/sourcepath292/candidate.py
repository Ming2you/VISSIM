"""Bounded source-path delay experiment; no production install or fitting.

Only newly accepted SC12->SC6 traffic is affected. Current calendars, demand,
head capacities, routing and receiving remain the canonical model's owners.
The fixed intermediate SC10 signal is still omitted: this isolates travel
distance and is not a complete corridor model.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET

ORIGIN = 'SC12_to_SC6'
MODE = 'source_path_current_physical_speed'


def delay_steps(distance_m, effective_speed_kph, lane_factor, nominal_kph, dt):
    if not all(math.isfinite(v) and v > 0 for v in
               (distance_m, lane_factor, nominal_kph, dt)):
        raise ValueError('Invalid geometry or clock')
    if not math.isfinite(effective_speed_kph) or effective_speed_kph < 0:
        raise ValueError('Invalid current speed')
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    physical = max(effective_speed_kph/lane_factor,
                   nominal_kph/OBSERVED_SPEED_DELAY_CAP_RATIO)
    return max(1, math.ceil(distance_m/(physical/3.6)/dt))


def geometry(root, cfg):
    from evaluation.controllers.route_choice_corridor import _length, _travel_segments, _validate_path
    source = root/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    data = source.read_bytes()
    tree = ET.fromstring(data)
    links = {n.get('no'):n for n in tree.findall('./links/link')}
    heads = [h for h in tree.findall('./signalHeads/signalHead')
             if h.get('lane').split()[0] == '1210018302' and h.get('sg').split()[0]=='6']
    stop = min(float(h.get('pos')) for h in heads)
    shared = ['1220015100','10212','136','10211','1220018301',
              '10216','1220018302','10209','1210018302']
    result = {}
    def measure(paths):
        distances=[]
        for path in paths:
            _validate_path(path, links)
            rows=_travel_segments(path,links,{k:_length(links[k]) for k in path},stop)
            distances.append(sum(s['stop']-s['start'] for s in rows))
        return dict(paths=paths, distance_m=min(distances), bounds_m=[min(distances),max(distances)])
    for key,spec in cfg.network.urban_movements.items():
        if spec.get('receiving_link') != ORIGIN: continue
        proof=cfg.network.control_area_routes['movement:'+key]['physical_turns']
        assert len(proof)==1 and proof[0]['to_link']==shared[0]
        path=[proof[0]['connector']]+shared
        paths=[path,path[:-2]+['10210',path[-1]]]
        result['movement:'+key]=measure(paths)
    inputs={k:v for k,v in cfg.network.native_internal_inputs['inputs'].items()
            if v['target_storage']==ORIGIN}
    assert set(inputs)=={'1085'}
    assert inputs['1085']['source_contract_validated']
    result['input:internal:1085']=measure(inputs['1085']['approach_paths'])
    assert abs(result['input:internal:1085']['distance_m']-
               inputs['1085']['minimum_approach_distance_m'])<1e-6
    factor_path=root/'outputs/storage_effective_lanes_20260904.json'
    factor=json.loads(factor_path.read_bytes())['storage_effective_lanes'][ORIGIN]
    return dict(sources=result,lane_factor=factor, network_sha256=hashlib.sha256(data).hexdigest(),
                stop_position_m=stop,network_path=str(source),
                lane_factor_path=str(factor_path),lane_factor_sha256=hashlib.sha256(factor_path.read_bytes()).hexdigest())


@contextmanager
def installed(cfg, option, geometry):
    """Process-local explicit diagnostic hooks, restored on every exit."""
    if option is None:
        yield []
        return
    if option != MODE: raise ValueError('Unreviewed delay experiment')
    from evaluation.controllers import urban_flow_accounting as ufa, native_internal_input as nii
    from evaluation.controllers.omega_distance import record_ordinary_movement
    from src.models import urban_queue_model as uqm
    old_receive,old_advance,old_delay=ufa._receive_corridor,nii.advance,uqm._link_delay_steps
    records=[]; in_generation=False
    def calculate(state, cfg_arg, key):
        row=geometry['sources'][key]
        steps=delay_steps(row['distance_m'],state.urban_link_speed_kph[ORIGIN],
                          geometry['lane_factor'],cfg_arg.network.urban_avg_speed_km_h,
                          cfg_arg.simulation.T_u_sec)
        records.append(dict(source=key,sec=state.time_sec,delay_sec=steps*cfg_arg.simulation.T_u_sec))
        return steps
    def receive(state,cfg_arg,movement,vehicles,step,*,entry_step=None):
        handled=old_receive(state,cfg_arg,movement,vehicles,step,entry_step=entry_step)
        target=cfg_arg.network.urban_movements[movement].get('receiving_link')
        if target!=ORIGIN: return handled
        assert not handled,'Do not replace an existing physical corridor'
        entry=step if entry_step is None else entry_step
        due=entry+calculate(state,cfg_arg,'movement:'+movement)
        uqm._schedule(state.urban_arrival_buffer,ORIGIN,due,vehicles)
        uqm._schedule(state.urban_storage_release_buffer,ORIGIN,due,vehicles)
        record_ordinary_movement(state,cfg_arg,movement,vehicles,entry,due)
        return True
    def advance(*args,**kwargs):
        nonlocal in_generation
        assert not in_generation
        in_generation=True
        try:return old_advance(*args,**kwargs)
        finally:in_generation=False
    def delay(state,cfg_arg,target):
        if target==ORIGIN and in_generation:
            return calculate(state,cfg_arg,'input:internal:1085')
        return old_delay(state,cfg_arg,target)
    ufa._receive_corridor=receive;nii.advance=advance;uqm._link_delay_steps=delay
    try:yield records
    finally:
        ufa._receive_corridor=old_receive;nii.advance=old_advance;uqm._link_delay_steps=old_delay
