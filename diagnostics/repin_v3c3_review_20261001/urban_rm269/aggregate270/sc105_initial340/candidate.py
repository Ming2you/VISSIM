"""Current SC105 north composition and physical arrival projection.

Upstream stopped vehicles remain source storage until their current-position
arrival. No service rate, demand, command or future trajectory is fitted.
"""
from collections import defaultdict
from copy import deepcopy
import hashlib, math, xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import measure, require
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320.candidate import arrival_step, NETWORK_SHA
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import validate

TARGET='SC1002_to_SC105'
TERMINAL='1220007200'
SHARED=['420','10659',TERMINAL]
MOVES={'SC105_N_SC1002_to_S_SC1005':'10661',
       'SC105_N_SC1002_to_E_SC1':'10662',
       'SC105_N_SC1002_to_W_SC1003':'10663'}


def path_catalog(cfg,links):
    """Both physical lane connectors to the same receiving signal."""
    trunks=[]
    for key,node in links.items():
        start,end=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
        if start is not None and end is not None and start.get('lane').split()[0]==SHARED[0] and end.get('lane').split()[0]==TERMINAL:
            trunks.append([SHARED[0],key,TERMINAL])
    require(SHARED in trunks,'Reviewed original SC105 corridor missing')
    # Keep the existing path first for genuinely unresolved paths, then filter
    # with current native route and lane. A second connector is not a new turn.
    trunks.sort(key=lambda p:(p!=SHARED,p))
    paths={}
    def add(path):
        for i,key in enumerate(path):
            if path[i:] not in paths.setdefault(key,[]):paths[key].append(path[i:])
    for path in trunks:add(path)
    for m,spec in cfg.network.urban_movements.items():
        if spec.get('receiving_link')!=TARGET:continue
        turns=cfg.network.control_area_routes['movement:'+m]['physical_turns']
        require(len(turns)==1 and turns[0]['to_link']==SHARED[0],'Ambiguous incoming path')
        for path in trunks:add([turns[0]['connector'],*path])
    return paths


def choose_path(options,vehicle,links,suffix=None):
    options=[p for p in options if suffix is None or p[:len(suffix)]==suffix]
    if str(vehicle['link_no'])==SHARED[0]:
        allowed=[]
        for p in options:
            node=links[p[1]];start=node.find('fromLinkEndPt');first=int(start.get('lane').split()[1])
            if vehicle['lane_no'] in range(first,first+len(node.findall('./lanes/lane'))):allowed.append(p)
        # Known intent may require a later lane change; do not overwrite it
        # with the present lane. Unknown routes use only lane-feasible paths.
        if suffix is None or len(suffix)<2:options=allowed
    require(options,'Current route or lane leaves reviewed SC105 corridor')
    return options[0]


def replace_cohort(total,before,after):
    """Keep other physical cohorts; tolerate only subtraction roundoff at zero."""
    remainder=total-before
    require(remainder>=-1e-8 and after>=0,'Insufficient current stock to replace physical cohort')
    return max(0.,remainder)+after


def install(cfg,state,raw,frame,network,lane_queues):
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.models.urban_queue_model import approach_routing
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import membership
    validate(raw,frame,state.time_sec)
    require(hashlib.sha256(network).hexdigest()==NETWORK_SHA,'Unreviewed geometry')
    require(cfg.simulation.T_u_sec==10 and cfg.simulation.T_f_sec==5,'Reviewed clocks required')
    require(TARGET not in getattr(state,'gate_initial_route_tags',{}),'Duplicate route owner')
    require(TARGET not in getattr(cfg.network,'physical_gate_travel',{}),'Another transport owner')
    ledger=get_ledger(state)
    require(ledger.event_count==0 and ledger.ttt_veh_h==0 and not ledger.captures_response,'Initial assimilation only')
    root=ET.fromstring(network);links={n.get('no'):n for n in root.findall('./links/link')}
    heads=root.findall('./signalHeads/signalHead')
    stop=min(float(h.get('pos')) for h in heads if h.get('lane').split()[0]==TERMINAL)
    paths=path_catalog(cfg,links)
    for key,options in paths.items():
        for path in options:measure(path,links,0.,stop)
        if key!=TERMINAL:
            require(not any(h.get('lane').split()[0]==key for h in heads),'Upstream fixed gate needs its own service')
    beta=dict(approach_routing(cfg)[TARGET]);require(set(beta)==set(MOVES),'Changed movement catalog')
    assignments=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    keys={'storage:'+TARGET,*('movement:'+m for m in MOVES)}
    owners={k for k,v in assignments.items() if any(v.get(p,0)>0 for p in keys)}
    require(owners<=set(paths),'Uncovered current source owner')
    records=[v for v in raw['vehicle_records']['records'] if str(v['link_no']) in owners]
    rows={r[0]:r for r in frame['vehicles']}
    old_calendar=state.urban_arrival_buffer.get(TARGET,{})
    old_release=state.urban_storage_release_buffer.get(TARGET,{})
    if TARGET not in state.urban_arrival_buffer or TARGET not in state.urban_storage_release_buffer:
        owned=sum(v.get(k,0.) for v in assignments.values() for k in keys)
        stock=sum(ledger.stocks.get(k,{}).get(side,0.) for k in keys for side in ('inside','outside'))
        native=sum(str(v['link_no']) in set(SHARED) for v in raw['vehicle_records']['records'])
        require(raw['vehicle_records']['complete'] and owned==stock==native==model_inventory(state,cfg).get('storage:'+TARGET,0.)==0,
                'Missing SC105 calendar without independently empty stock')
        require(not old_calendar and not old_release,'Missing SC105 calendar with outstanding reservation')
    require(old_calendar==old_release,'Unpaired initial reservation')
    ready=set();old_ready=0.;means={};shares={};source_vehicles=0.
    for key in owners:
        vv=[v for v in records if str(v['link_no'])==key];support=assignments[key]
        require(abs(sum(support.values())-len(vv))<1e-8,'Physical ownership does not cover records')
        owned=sum(support.get(k,0.) for k in keys)
        shares[key]=owned/len(vv);source_vehicles+=owned
        means[key]=math.fsum(v['speed_kph'] for v in vv)/len(vv)
        q=sum(support.get('movement:'+m,0) for m in MOVES);old_ready+=q
        require(shares[key]==1 or (key!=TERMINAL and q==0 and
                all(k.startswith('storage:') for k in support)), 'Mixed ready ownership needs explicit partition')
        if key==TERMINAL:
            for lane in {v['lane_no'] for v in vv}:
                n=lane_queues.get((key,str(lane)),0.)
                require(n==int(n),'Fractional native queue membership')
                front=sorted((v for v in vv if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
                require(len(front)==n and all(v['stopped'] for v in front),'Current terminal queue differs')
                ready.update(v['veh_no'] for v in front)
            require(len(ready)==q,'Terminal queue count changed')
    require(abs(sum(old_calendar.values())-(source_vehicles-old_ready))<1e-8,'Initial source reservation mismatch')
    result=deepcopy(state);new_support={k:{**{p:v for p,v in assignments[k].items() if p not in keys},
                                           'storage:'+TARGET:0.,**{'movement:'+m:0. for m in MOVES}} for k in owners}
    calendar=defaultdict(float);tags=defaultdict(lambda:defaultdict(float));detail=[]
    dt=cfg.simulation.T_u_sec;now=state.time_sec
    for v in records:
        key=str(v['link_no']);r=rows[v['veh_no']];selected=None;amount=shares[key];current_prefix=None
        if not all(x is None for x in r[6:10]):
            require(all(x is not None for x in r[6:9]) and r[8]=='STATIC','Unsupported current route')
            dec=root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{int(r[6])}']")
            route=None if dec is None else dec.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(r[7])}']")
            require(route is not None,'Unknown current route')
            path=[dec.get('link'),*[n.get('key') for n in route.findall('./linkSeq/intObjectRef')],route.get('destLink')]
            require(path.count(key)==1,'Ambiguous native current position')
            suffix=path[path.index(key):]
            require(r[9] is None or (len(suffix)>1 and str(int(r[9]))==suffix[1]),'Current next link disagrees')
            if TERMINAL in suffix and suffix.index(TERMINAL)+1<len(suffix):
                j=suffix.index(TERMINAL)
                current_prefix=suffix[:j+1]
                selected=next((m for m,c in MOVES.items() if c==suffix[j+1]),None)
                require(selected is not None,'Native destination outside target catalog')
            else:
                current_prefix=suffix
        path=choose_path(paths[key],v,links,current_prefix)
        weights={selected:1.} if selected else beta
        if v['veh_no'] in ready:
            for m,w in weights.items():new_support[key]['movement:'+m]+=w*amount
            detail.append(dict(vehicle=v['veh_no'],link=key,lane=v['lane_no'],ready=True,weights=weights));continue
        post_head=key==TERMINAL and v['position_m']>stop
        if post_head:
            due=int(round(now/dt))+math.ceil((105 if v['stopped'] else 15)/dt)
            distance=None
        else:
            distance=measure(path,links,v['position_m'],stop)
            due=arrival_step(distance,v['speed_kph'],means[key],now,dt)
        calendar[due]+=amount;new_support[key]['storage:'+TARGET]+=amount
        if selected:
            tags[due][selected]+=amount
        detail.append(dict(vehicle=v['veh_no'],link=key,lane=v['lane_no'],ready=False,weights=weights,
                           owned_vehicles=amount,due_sec=due*dt,distance_m=distance,post_head_owner_retained=post_head,physical_path=path))
    sides,_=membership();old_stored=sum(assignments[k].get('storage:'+TARGET,0) for k in owners)
    new_stored=sum(v['storage:'+TARGET] for v in new_support.values());delta_stored=new_stored-old_stored
    require(result.urban_link_storage[TARGET]>=delta_stored-1e-8,'Insufficient source storage for spatial queue')
    result.urban_link_storage[TARGET]-=delta_stored
    for key,updated in new_support.items():
        side='inside' if sides[key] else 'outside'
        for owner in keys:
            old=assignments[key].get(owner,0.)
            account=get_ledger(result).stocks[owner]
            account[side]=replace_cohort(account[side],old,updated[owner])
            if owner.startswith('movement:'):
                m=owner.removeprefix('movement:')
                result.urban_movement_queue[m]=replace_cohort(result.urban_movement_queue[m],old,updated[owner])
                summary=result.local_observation_summary['urban_movement_queue']
                summary[m]=replace_cohort(summary[m],old,updated[owner])
            require(get_ledger(result).stocks[owner][side]>=-1e-8,'Negative owner stock')
        result.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][key]=updated
    result.urban_arrival_buffer[TARGET]=dict(calendar);result.urban_storage_release_buffer[TARGET]=dict(calendar)
    result.gate_initial_route_tags[TARGET]={t:dict(v) for t,v in tags.items()}
    require(abs(sum(calendar.values())+len(ready)-source_vehicles)<1e-8,'Current cohort conservation')
    get_ledger(result).assert_stocks(model_inventory(result,cfg))
    for side in ('inside','outside'):
        require(abs(sum(v[side] for v in ledger.stocks.values())-sum(v[side] for v in get_ledger(result).stocks.values()))<1e-8,'Area ownership changed')
    receipt=dict(time_sec=now,physical_vehicles=len(records),source_vehicles=source_vehicles,ownership_shares=shares,
                 ready_before=old_ready,ready_after=len(ready),
                 moved_queue_to_storage=delta_stored,old_calendar=old_calendar,new_calendar=dict(calendar),
                 old_support={k:assignments[k] for k in owners},new_support=new_support,vehicles=detail,
                 retained_posthead=sum(x.get('post_head_owner_retained',False) for x in detail),
                 future_inputs=False,new_fit=False,service_unchanged=True,
                 limitation='Finite ETA approximation has no explicit within-lane FIFO/start-wave. Unknown later turns keep baseline beta.')
    return result,receipt
