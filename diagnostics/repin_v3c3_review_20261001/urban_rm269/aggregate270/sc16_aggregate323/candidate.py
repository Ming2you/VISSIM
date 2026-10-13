"""Past-supported SC16 aggregate split/service and current lane ownership."""
from pathlib import Path
import copy,hashlib,importlib.util,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import membership

HERE=Path(__file__).resolve().parent;A=HERE.parent
SOURCE='SC12_to_SC16';LINK='1210012600';LEFT='SC16_N_SC12_to_E'
MOVEMENTS={'SC16_N_SC12_to_S_SC109':'10248','SC16_N_SC12_to_W_SC7':'10252',LEFT:'10250'}
spec=importlib.util.spec_from_file_location('sc16_current_projection323',A/'sc12_initial306/candidate.py')
projection=importlib.util.module_from_spec(spec);spec.loader.exec_module(projection)
projection.SOURCE=SOURCE;projection.LINK=LINK;projection.MOVEMENTS=MOVEMENTS

def install(cfg,state,raw,frame,network,lanes):
    support_path=HERE/'support.json';s=json.loads(support_path.read_bytes())
    if state.time_sec<s['cutoff_sec'] or hashlib.sha256(network).hexdigest()!=s['network_sha256']:
        raise ValueError('Support must be past data on the same network')
    for p,h in s['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Support changed: '+p)
    old={m:cfg.network.urban_movements[m]['beta'] for m in MOVEMENTS}
    if old!=s['beta_before'] or cfg.network.movement_capacity_by_movement_veh_h[LEFT]!=s['service_before_veh_h']:
        raise ValueError('Unexpected or repeated calibration')
    beta=s['left_net_arrivals']/s['net_arrivals'];new=s['beta_after']
    if not (0<beta<1 and abs(new[LEFT]-beta)<1e-12 and abs(sum(new.values())-1)<1e-12):
        raise ValueError('Invalid aggregate composition')
    if max(r['end_sec'] for r in s['rows'])!=s['cutoff_sec']:
        raise ValueError('Future calibration support')
    if s['service_after_veh_h']!=min(r['left_achieved_veh_h'] for r in s['rows'][-2:]):
        raise ValueError('Service is not the declared conservative past support')
    trial=copy.deepcopy(cfg)
    for m,b in new.items():trial.network.urban_movements[m]['beta']=b
    trial.network.movement_capacity_by_movement_veh_h[LEFT]=s['service_after_veh_h']
    sides,mpath=membership()
    if sides.get(LINK) not in (True,False):raise ValueError('Physical ownership absent')
    result,current=projection.project(state,trial,raw,frame,network,sides[LINK],lanes)
    # Commit only after the existing conserved current-observation projector succeeds.
    cfg.network.urban_movements=trial.network.urban_movements
    cfg.network.movement_capacity_by_movement_veh_h=trial.network.movement_capacity_by_movement_veh_h
    receipt=dict(variant='past_aggregate_sc16',at_sec=state.time_sec,cutoff_sec=s['cutoff_sec'],
        beta_before=old,beta_after=new,service_before_veh_h=s['service_before_veh_h'],service_after_veh_h=s['service_after_veh_h'],
        current_projection=current,source_pins={str(support_path):hashlib.sha256(support_path.read_bytes()).hexdigest(),
            str(mpath):hashlib.sha256(mpath.read_bytes()).hexdigest()},
        future_traffic_inputs=False,upstream_service_unchanged=True,production_adopted=False,
        limitations=s['limits'])
    return result,receipt
