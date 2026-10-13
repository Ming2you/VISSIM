"""Scoped aggregate transport diagnosis: physical path, unchanged speed."""
from evaluation.controllers.calibrated_initial_projection import verify_speed as _repair_verify_speed
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,math,xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
TARGET='SC108_to_SC109'
EXPECTED={'SC108_N_SC7_to_E_SC109','SC108_W_SC107_to_E_SC109','SC108_S_to_E_SC109','SC108_W_to_E_SC109'}

def steps(distance_m,physical_speed_kph,nominal_kph,dt):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    if not all(math.isfinite(x) and x>0 for x in (distance_m,nominal_kph,dt)):
        raise ValueError('Invalid physical path or clock')
    if not math.isfinite(physical_speed_kph) or physical_speed_kph<0:
        raise ValueError('Invalid current moving speed')
    speed=max(physical_speed_kph,nominal_kph/OBSERVED_SPEED_DELAY_CAP_RATIO)
    return max(1,math.ceil(distance_m/(speed/3.6)/dt))

def geometry(cfg):
    from evaluation.controllers.route_choice_corridor import _length,_validate_path,_travel_segments
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    source=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    data=source.read_bytes();tree=ET.fromstring(data);links={x.get('no'):x for x in tree.findall('./links/link')}
    heads=tree.findall('./signalHeads/signalHead')
    dest_heads=[x for x in heads if x.get('lane').split()[0]=='173' and x.get('sg').split()[0]=='109']
    stop=min(float(x.get('pos')) for x in dest_heads);result={}
    target_members={m for m,s in cfg.network.urban_movements.items() if s.get('receiving_link')==TARGET}
    if target_members!=EXPECTED:raise ValueError('SC108 incoming movements changed')
    if any(v.get('target_storage')==TARGET for v in cfg.network.native_internal_inputs['inputs'].values()):
        raise ValueError('Uncovered generated source')
    for m in sorted(EXPECTED):
        spec=cfg.network.urban_movements[m];turns=cfg.network.control_area_routes['movement:'+m]['physical_turns']
        if len(turns)!=1:raise ValueError('Ambiguous source path')
        turn=turns[0];phase=spec['phase'].rsplit('_',1)[1]
        sgs=cfg.network.signal_actuation_contract['nodes']['SC108']['phase_signal_groups'][phase]
        source_heads=[x for x in heads if x.get('lane').split()[0]==turn['from_link'] and x.get('sg').split()[0]=='108' and x.get('sg').split()[1] in sgs]
        if not source_heads:raise ValueError('Source head not covered')
        start=min(float(x.get('pos')) for x in source_heads)
        prefix=[turn['from_link'],turn['connector'],turn['to_link']]
        if turn['to_link']=='1220000600':prefix+=['10024','174']
        elif turn['to_link']!='174':raise ValueError('Receiving geometry changed')
        paths=[prefix+[connector,'173'] for connector in ('10280','10281')]
        distances=[];segments=[]
        for path in paths:
            _validate_path(path,links)
            pieces=_travel_segments(path,links,{k:_length(links[k]) for k in path},stop)
            if start>pieces[0]['stop']:raise ValueError('Movement diverges before its signal')
            pieces[0]['start']=start;segments.append(pieces)
            distances.append(sum(x['stop']-x['start'] for x in pieces))
        result[m]=dict(paths=paths,segments=segments,distance_m=min(distances),distance_bounds_m=[min(distances),max(distances)],head_start_m=start)
    # Use the actually applied capacity-derived factor, not the FZP fallback table.
    ep=Path(adapter.STORAGE_CAPACITY_EVIDENCE_JSON);eb=ep.read_bytes();e=json.loads(eb)
    factor=e['urban_link_storage_veh'][TARGET]/(e['urban_link_length_km'][TARGET]*e['jam_density_veh_km_lane'])
    assert factor>1
    return dict(sources=result,lane_factor=factor,network_path=str(source),network_sha256=hashlib.sha256(data).hexdigest(),
        factor_path=str(ep),factor_sha256=hashlib.sha256(eb).hexdigest(),initial_calendars_unchanged=True)

def install(cfg,state):
    option=json.loads((HERE/'config.json').read_bytes())
    if option['diagnostic_source_geometry_transport']!=TARGET or option['new_future_observation_inputs']:
        raise ValueError('Explicit causal diagnostic option required')
    if hasattr(cfg.network,'sc109_transport317'):raise ValueError('Duplicate transport hook')
    geom=geometry(cfg)
    physical=state.urban_link_speed_kph[TARGET]/geom['lane_factor']
    geom['speed_receipt']=_repair_verify_speed(state,cfg,TARGET,geom['lane_factor'])
    geom['current_physical_speed_kph']=physical
    geom['delay_sec']={m:steps(x['distance_m'],physical,cfg.network.urban_avg_speed_km_h,cfg.simulation.T_u_sec)*cfg.simulation.T_u_sec for m,x in geom['sources'].items()}
    cfg.network.sc109_transport317=geom
    return geom

@contextmanager
def enabled():
    from evaluation.controllers import urban_flow_accounting as ufa
    from evaluation.controllers.omega_distance import record_ordinary_movement
    from src.models import urban_queue_model as uqm
    old=ufa._receive_corridor;receipts=[]
    def receive(state,cfg,movement,vehicles,step,*,entry_step=None):
        geom=getattr(cfg.network,'sc109_transport317',None)
        if not geom or cfg.network.urban_movements[movement].get('receiving_link')!=TARGET:
            return old(state,cfg,movement,vehicles,step,entry_step=entry_step)
        if old(state,cfg,movement,vehicles,step,entry_step=entry_step):
            raise ValueError('Existing corridor owns this transfer')
        row=geom['sources'][movement]
        delay=steps(row['distance_m'],state.urban_link_speed_kph[TARGET]/geom['lane_factor'],
                    cfg.network.urban_avg_speed_km_h,cfg.simulation.T_u_sec)
        entry=step if entry_step is None else entry_step;due=entry+delay
        uqm._schedule(state.urban_arrival_buffer,TARGET,due,vehicles)
        uqm._schedule(state.urban_storage_release_buffer,TARGET,due,vehicles)
        record_ordinary_movement(state,cfg,movement,vehicles,entry,due)
        receipts.append(dict(source=movement,entry_sec=entry*cfg.simulation.T_u_sec,due_sec=due*cfg.simulation.T_u_sec,vehicles=float(vehicles)))
        return True
    ufa._receive_corridor=receive
    try:yield receipts
    finally:ufa._receive_corridor=old
