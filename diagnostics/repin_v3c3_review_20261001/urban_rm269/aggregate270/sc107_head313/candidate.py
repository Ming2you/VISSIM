"""Bounded current SC107 head-cohort repair; no future turn-rate fitting.

Known current lanes2..5 cannot return to the right branch behind them. Lane5
uses its physical SG5; the unsupported lane1 stock is retained explicitly.
Future approach distributions are unchanged, so this is not a full SC107 model.
"""
from copy import deepcopy
import math,xml.etree.ElementTree as ET

LINK='1220000201';ORIGIN='SC1005_to_SC107'
THROUGH='SC107_W_SC1005_to_E_SC108'
LEFT='SC107_W_SC1005_to_N_SC1';RIGHT='SC107_W_SC1005_to_S'
SG5=THROUGH+'__current_sg5'
UNKNOWN='SC107_W_SC1005_current_unresolved'
OLD=(THROUGH,LEFT,RIGHT)
GROUP='diagnostic_SC107_current_sg5'


def register_owner(follower,cfg):
    """Late diagnostic insertion must refresh the same SC107 local owner."""
    from src.controllers.local_signal_plant import build_local_model
    from evaluation.controllers.area_leader_objective import _joint_catalog
    if follower.cfg is not cfg:raise ValueError('Follower must share the candidate configuration')
    specs=dict(follower._specs);phases=deepcopy(follower._phase_movements)
    for movement in (SG5,UNKNOWN):
        row=cfg.network.urban_movements[movement]
        phase=row['phase'].rsplit('_',1)[1]
        if movement in specs or movement in phases['SC107'][phase]:raise ValueError('Head owner already registered')
        specs[movement]=row;phases['SC107'][phase].append(movement)
    follower._specs=specs;follower._phase_movements=phases
    follower._wu._specs=specs;follower._wu._phase_movements=phases
    follower._local_models['SC107']=build_local_model(cfg,'SC107',specs,phases)
    _,_,catalog,_=_joint_catalog(follower)
    if any(catalog[m]!=('SC107','internal') for m in (SG5,UNKNOWN)):
        raise ValueError('New head must retain unique SC107 ownership')
    return dict(new_movements=[SG5,UNKNOWN],owner='SC107',unique_owner_verified=True,new_control_axes=0)


def partition(records,geometry):
    totals={THROUGH:0.,SG5:0.,UNKNOWN:0.};moving={THROUGH:0.,SG5:0.,UNKNOWN:0.}
    details=[]
    for r in records:
        if r['position_m']<=geometry['right_pos'] or r['position_m']>geometry['through_pos']:
            raise ValueError('Current cohort must lie after right branch and before through connector')
        lane=r['lane_no']
        if lane in (2,3,4):target=THROUGH
        elif lane==5:target=SG5
        elif lane==1:target=UNKNOWN
        else:raise ValueError('Unsupported physical lane')
        (totals if r['stopped'] else moving)[target]+=1.
        details.append(dict(vehicle=r['veh_no'],target=target,lane=lane,position_m=r['position_m'],ready=r['stopped']))
    return totals,moving,details


def install(cfg,state,raw,frame,network_bytes):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
    if SG5 in cfg.network.urban_movements:raise ValueError('Cannot install twice')
    if raw['sim_sec']!=state.time_sec or frame['time_s']!=state.time_sec or not frame['complete']:
        raise ValueError('Current paused frame required')
    obs=raw['vehicle_records']
    if not obs['complete'] or any(obs[k]!=state.time_sec for k in ('paused_at_sim_sec','capture_sim_sec_before','capture_sim_sec_after')):
        raise ValueError('Current complete physical records required')
    records=[r for r in obs['records'] if str(r['link_no'])==LINK]
    frames={r[0]:r for r in frame['vehicles'] if str(r[1])==LINK}
    if set(frames)!={r['veh_no'] for r in records}:raise ValueError('Frame IDs differ')
    for r in records:
        f=frames[r['veh_no']]
        if f[2]!=r['lane_no'] or abs(f[3]-r['position_m'])>1e-7 or any(x is not None for x in f[6:10]):
            raise ValueError('Review current known route separately; cannot overwrite intent')
    tree=ET.fromstring(network_bytes);links={x.get('no'):x for x in tree.findall('./links/link')}
    through=links['10023'];right=links['10616']
    if through.find('fromLinkEndPt').get('lane')!=LINK+' 2' or len(through.findall('./lanes/lane'))!=4:
        raise ValueError('Through connector no longer spans2..5')
    if right.find('fromLinkEndPt').get('lane')!=LINK+' 1':raise ValueError('Right branch changed')
    heads=[x for x in tree.findall('./signalHeads/signalHead') if x.get('lane','').split()[0]==LINK]
    for lane,sg in ((2,'2'),(3,'2'),(4,'2'),(5,'5')):
        selected=[h for h in heads if h.get('lane')==LINK+' '+str(lane)]
        if len(selected)!=1 or selected[0].get('sg')!='107 '+sg:raise ValueError('Head binding changed')
    geometry=dict(right_pos=float(right.find('fromLinkEndPt').get('pos')),through_pos=float(through.find('fromLinkEndPt').get('pos')))
    queues,tags,details=partition(records,geometry)
    support=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][LINK]
    if set(support)-{'storage:'+ORIGIN,*('movement:'+m for m in OLD)}:raise ValueError('Physical owner changed')
    if abs(sum(support.values())-len(records))>1e-8 or abs(sum(queues.values())-sum(support.get('movement:'+m,0.) for m in OLD))>1e-8:
        raise ValueError('Ready and physical counts differ')
    if any(cfg.network.urban_movements[m]['beta']!=0 or state.urban_movement_queue[m]!=0 for m in (LEFT,'SC107_W_SC1004_to_N_SC1')):
        raise ValueError('Positive left intent cannot be repurposed or pooled without route proof')
    if ORIGIN in state.gate_initial_route_tags:raise ValueError('Source already tagged')
    arrival=state.urban_arrival_buffer[ORIGIN]
    if arrival!=state.urban_storage_release_buffer[ORIGIN] or len(arrival)!=1:raise ValueError('Paired existing reservation required')
    step,parent=next(iter(arrival.items()))
    if parent<sum(tags.values()) or abs(sum(tags.values())-support.get('storage:'+ORIGIN,0.))>1e-8:
        raise ValueError('Residual ownership differs')
    ledger=get_ledger(state)
    if ledger.event_count or ledger.ttt_veh_h or ledger.captures_response:raise ValueError('Initial assimilation only')
    before={m:support.get('movement:'+m,0.) for m in OLD}
    for m,n in before.items():
        if ledger.stocks['movement:'+m]['outside']!=0 or ledger.stocks['movement:'+m]['inside']<n-1e-8:
            raise ValueError('Current physical subset must be inside Omega')
    inherited=sum(cfg.network.movement_capacity_by_movement_veh_h[m] for m in (LEFT,'SC107_W_SC1004_to_N_SC1'))
    if not math.isfinite(inherited) or inherited<=0:raise ValueError('Invalid inherited SG5 envelope')
    movements=deepcopy(cfg.network.urban_movements);caps=dict(cfg.network.movement_capacity_by_movement_veh_h)
    movements[SG5]={**movements[THROUGH],'beta':0.,'phase':'SC107_p4'};caps[SG5]=inherited
    movements[UNKNOWN]={**movements[THROUGH],'beta':0.};caps[UNKNOWN]=0.
    cfg.network.urban_movements=movements;cfg.network.movement_capacity_by_movement_veh_h=caps
    # A signal-head split changes service timing, not the physical through
    # path or Omega boundary crossings. Register that same proved path for
    # the new key; never bypass the ledger's unresolved-route rejection.
    routes=deepcopy(cfg.network.control_area_routes)
    for prefix in ('movement:','arrival:'):
        if prefix+THROUGH not in routes:raise ValueError('Existing through area path proof required')
        routes[prefix+SG5]=deepcopy(routes[prefix+THROUGH])
    routes['arrival:'+UNKNOWN]=deepcopy(routes['arrival:'+THROUGH])
    cfg.network.control_area_routes=routes
    invalidate_topology_cache(cfg.network)
    summary=state.local_observation_summary
    new_counts={THROUGH:queues[THROUGH],LEFT:0.,RIGHT:0.,SG5:queues[SG5],UNKNOWN:queues[UNKNOWN]}
    for m,n in new_counts.items():
        delta=n-before.get(m,0.)
        state.urban_movement_queue[m]=state.urban_movement_queue.get(m,0.)+delta
        summary['urban_movement_queue'][m]=summary['urban_movement_queue'].get(m,0.)+delta
        support['movement:'+m]=n
        stock=ledger.stocks.setdefault('movement:'+m,dict(inside=0.,outside=0.));stock['inside']+=delta
    state.gate_initial_route_tags[ORIGIN]={step:{m:n for m,n in tags.items() if n}}
    ledger.assert_stocks(model_inventory(state,cfg))
    return dict(status='current_cohort_head_partition_only',queue_before=before,queue_after=new_counts,
        initial_stock_veh=len(records),current_geometry=geometry,tagged_moving=tags,parent_veh=parent,due_step=step,
        sg5_inherited_envelope_veh_h=inherited,unresolved_retained_veh=queues[UNKNOWN]+tags[UNKNOWN],
        unresolved_450s_cost_upper_bound=(queues[UNKNOWN]+tags[UNKNOWN])*450/3600,
        future_routing_unchanged=True,future_sg5_arrivals_not_implemented=True,
        unsupported_future_right_prebranch_dynamics_not_repaired=True,production_adopted=False,
        records_used_at_initialization_only=details)
