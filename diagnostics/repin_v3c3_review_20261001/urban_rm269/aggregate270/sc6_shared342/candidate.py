"""Diagnostic pre-head right turn with aggregate shared-lane blockage.

One shadow label partitions the existing through queue; it is not new stock.
Current lane observations seed the label. Later unlabelled aggregate arrivals
share the physical through lanes equally. No rate is fitted here.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib, math, xml.etree.ElementTree as ET

RIGHT='SC6_E_SC104_to_N_SC103'
THROUGH='SC6_E_SC104_to_W_SC5'
SOURCE='1220021201'
ATTR='_shared_prehead342'
NETWORK_SHA='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'


def access_limit(ready, lane_queue, pocket, full_right, full_through, accepted_through):
    if min(ready,lane_queue,pocket,full_right,full_through,accepted_through)<-1e-8:
        raise ValueError('Negative shared-lane operand')
    if full_through<=0 or accepted_through>full_through+1e-7:
        raise ValueError('Through service exceeds its existing ungated rate')
    coverage=min(1.,max(0.,lane_queue-pocket))
    progress=min(1.,accepted_through/full_through)
    allowed=min(ready,full_right*(1.-coverage*(1.-progress)))
    return allowed,coverage,progress


def install(cfg,state,raw,frame,network,lane_queues):
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import validate
    validate(raw,frame,state.time_sec)
    assert hashlib.sha256(network).hexdigest()==NETWORK_SHA
    assert not hasattr(cfg.network,ATTR) and not hasattr(state,ATTR)
    assert cfg.simulation.T_u_sec==10 and cfg.simulation.T_f_sec==5
    tree=ET.fromstring(network);links={n.get('no'):n for n in tree.findall('./links/link')}
    right=links['10142'];through=links['10200']
    re=right.find('fromLinkEndPt');te=through.find('fromLinkEndPt')
    assert re.get('lane')==te.get('lane')==SOURCE+' 1'
    lanes=len(through.findall('./lanes/lane'));assert lanes==4
    heads=tree.findall('./signalHeads/signalHead')
    head=next(h for h in heads if h.get('no')=='90601')
    assert head.get('lane')==re.get('lane') and head.get('sg')=='6 6'
    assert not any(h.get('lane').split()[0]=='10142' for h in heads)
    gap=float(head.get('pos'))-float(re.get('pos'));assert gap>0
    # Same conserved jam-spacing convention already used by the68/124 gates.
    spacing=state.lane_ramp_runtime.buffers['RM_C10681'].spacing_m
    rows={r[0]:r for r in frame['vehicles']}
    records=[v for v in raw['vehicle_records']['records'] if str(v['link_no'])==SOURCE and v['lane_no']==1]
    n=lane_queues.get((SOURCE,'1'),0.);assert n==int(n)
    front=sorted(records,key=lambda v:-v['position_m'])[:int(n)]
    assert len(front)==n and all(v['stopped'] for v in front)
    # Count only confirmed through vehicles; never infer an unknown current
    # destination from the later observed trajectory or a controller command.
    assert all(rows[v['veh_no']][9] in (10142.,10200.) for v in front)
    shared=sum(rows[v['veh_no']][9]==10200. for v in front)
    q=state.urban_movement_queue[THROUGH]
    assert 0<=shared<=q+1e-8
    spec=dict(right=RIGHT,through=THROUGH,shared_lane=1,through_lanes=lanes,
              gap_m=gap,spacing_m=spacing,pocket_veh=gap/spacing,
              future_lane_share=1./lanes,network_sha256=NETWORK_SHA)
    setattr(cfg.network,ATTR,spec)
    setattr(state,ATTR,dict(lane_queue=float(shared),after_through=q,last_step=None,history=[]))
    return dict(spec,initial_lane_queue=shared,initial_through_queue=q,
        initial_right_queue=state.urban_movement_queue[RIGHT],current_vehicle_ids=[v['veh_no'] for v in front],
        stock_mutated=False,fit=False,future_observations=False,
        limitation='Existing initial movement projection is retained. Future aggregate lane shares are uniform; no lateral gap or strict FIFO model.')


@contextmanager
def enabled():
    from evaluation.controllers import urban_flow_accounting as ufa,route_choice_corridor as rc
    old_intended,old_limits=ufa._corridor_intended,rc.known_entry_lane_limits
    def intended(state,control,cfg,movement,available,step,ordinary):
        spec=getattr(cfg.network,ATTR,None)
        if spec is None or movement!=RIGHT:
            return old_intended(state,control,cfg,movement,available,step,ordinary)
        # No direct head on this branch. Actual shared-lane accessibility is
        # limited below, after through flow has passed real receiving limits.
        full=cfg.simulation.T_u_h*ufa._uqm._movement_capacity_flow(control,cfg,movement,cfg.network.urban_movements[movement])
        return old_intended(state,control,cfg,movement,available,step,min(available,full))
    def limits(state,cfg,requests,step):
        actual=old_limits(state,cfg,requests,step)
        spec=getattr(cfg.network,ATTR,None)
        if spec is None:return actual
        tag=getattr(state,ATTR)
        if tag['last_step']==step:raise ValueError('Shared label updated twice')
        q=state.urban_movement_queue[THROUGH];arrivals=q-tag['after_through']
        if arrivals<-1e-7:raise ValueError('Untracked through-queue debit')
        lane=tag['lane_queue']+max(0.,arrivals)*spec['future_lane_share']
        if lane>q+1e-7:raise ValueError('Shared lane label exceeds its sole owner')
        accepted=actual.get(THROUGH,0.)
        if accepted>q+1e-7:raise ValueError('Through debit exceeds current stock')
        # Capacity fields are the existing fixed service rates in this case.
        rates=cfg.network.movement_capacity_by_movement_veh_h;dt=cfg.simulation.T_u_h
        fullr=dt*rates[RIGHT];fullt=dt*rates[THROUGH]
        allowed,coverage,progress=access_limit(state.urban_movement_queue[RIGHT],lane,spec['pocket_veh'],fullr,fullt,accepted)
        got=min(actual.get(RIGHT,0.),allowed);result=dict(actual);result[RIGHT]=got
        after=lane*(1.-accepted/q) if q>0 else 0.
        if after< -1e-7 or after>q-accepted+1e-7:raise ValueError('Lane partition lost conservation')
        tag.update(lane_queue=after,after_through=q-accepted,last_step=step)
        ledger=ufa.get_ledger(state)
        if ledger is not None and ledger.captures_response:
            ledger.record_resource_allocation('shared_prehead342',RIGHT,allowed,{'movement:'+RIGHT:got})
            tag['history'].append(dict(step=step,through_queue=q,lane_queue=lane,arrivals=arrivals,
                pocket=spec['pocket_veh'],coverage=coverage,progress=progress,through_accepted=accepted,
                right_request=actual.get(RIGHT,0.),right_allowed=allowed,right_accepted=got,lane_after=after))
        return result
    ufa._corridor_intended=intended;rc.known_entry_lane_limits=limits
    try:yield
    finally:ufa._corridor_intended=old_intended;rc.known_entry_lane_limits=old_limits
