"""Keep known current SC109 turns in the existing aggregate queue/ETA owner."""
from collections import Counter,defaultdict
from pathlib import Path
import copy,hashlib,json,math,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320.candidate import TARGET,LINKS,NETWORK_SHA

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
MOVEMENTS={'SC109_W_SC108_to_E':'10285','SC109_W_SC108_to_N_SC16':'10286'}


def membership():
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    tuning=json.loads((A/'flow279/config_10686_free.json').read_bytes())
    path=ROOT/tuning['control_area_objective']['membership_path']
    return physical_membership_from_ledger(json.loads(path.read_bytes())),path


def current_weights(row,vehicle,root,routing):
    """Unknown routes retain the prior; known intent overrides current lane."""
    if all(x is None for x in row[6:10]):return dict(routing),False,None
    if any(x is None for x in row[6:9]) or row[8]!='STATIC':
        raise ValueError('Partial or unsupported current route cannot be redrawn')
    dec,rid=str(int(row[6])),str(int(row[7]))
    d=root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{dec}']")
    n=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{rid}']") if d is not None else None
    if n is None:raise ValueError('Known route absent from the current network')
    path=[d.get('link'),*[x.get('key') for x in n.findall('./linkSeq/intObjectRef')],n.get('destLink')]
    link=str(vehicle['link_no'])
    if path.count('173')!=1 or path.count(link)!=1:
        raise ValueError('Current route position is ambiguous')
    index=path.index(link)
    if index+1>=len(path) or (row[9] is not None and str(int(row[9]))!=path[index+1]):
        raise ValueError('Current route and next connector disagree')
    connector=path[path.index('173')+1]
    selected=next((m for m,c in MOVEMENTS.items() if c==connector),None)
    if selected is None:raise ValueError('Current turn is outside the existing movement catalog')
    return {selected:1.},True,path


def install(cfg,state,raw,frame,network,timing):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.urban_queue_model import approach_routing
    if (not frame.get('complete') or not raw['vehicle_records'].get('complete')
            or raw['sim_sec']!=frame['time_s'] or raw['sim_sec']!=state.time_sec
            or timing['time_sec']!=state.time_sec or timing['source']!=TARGET
            or hashlib.sha256(network).hexdigest()!=NETWORK_SHA):
        raise ValueError('Current same-time observation and reviewed geometry required')
    if TARGET in getattr(state,'gate_initial_route_tags',{}) or TARGET in getattr(cfg.network,'physical_gate_travel',{}):
        raise ValueError('Initial source already has a tag or competing owner')
    if not hasattr(cfg.network,'physical_ramp_branches'):
        raise ValueError('Existing aggregate tag consumer is required')
    ledger=get_ledger(state)
    if ledger.event_count or ledger.ttt_veh_h or ledger.captures_response:
        raise ValueError('Only initial assimilation may relabel stocks')
    routing=dict(approach_routing(cfg)[TARGET])
    if set(routing)!=set(MOVEMENTS) or abs(sum(routing.values())-1)>1e-10:
        raise ValueError('Existing source routing changed')
    expected_calendar={int(k):v for k,v in timing['new_calendar'].items()}
    if state.urban_arrival_buffer[TARGET]!=expected_calendar or state.urban_storage_release_buffer[TARGET]!=expected_calendar:
        raise ValueError('Current ETA and paired release must remain unchanged')
    records=[v for v in raw['vehicle_records']['records'] if str(v['link_no']) in LINKS]
    current={int(r[0]):r for r in frame['vehicles']}
    residual={r['vehicle']:r for r in timing['vehicles']}
    if len(residual)!=len(timing['vehicles']) or not set(residual)<={v['veh_no'] for v in records}:
        raise ValueError('ETA cohort differs from physical records')
    root=ET.fromstring(network);sides,side_path=membership()
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    assigned={};tags={};details=[];unknown=0
    for link in sorted(LINKS):
        physical=[v for v in records if str(v['link_no'])==link]
        support=provenance.get(link,{})
        if set(support)-{'storage:'+TARGET,*('movement:'+m for m in MOVEMENTS)} or abs(sum(support.values())-len(physical))>1e-8:
            raise ValueError('Physical provenance differs from the supported corridor')
        ready=[v for v in physical if v['veh_no'] not in residual]
        expected=sum(support.get('movement:'+m,0) for m in MOVEMENTS)
        if len(ready)!=expected or len(physical)-len(ready)!=support.get('storage:'+TARGET,0):
            raise ValueError('Existing queue and residual cohort identity differs')
        assigned[link]=dict.fromkeys(MOVEMENTS,0.)
        for v in physical:
            r=current[v['veh_no']]
            if r[1]!=int(link) or r[2]!=v['lane_no'] or abs(r[3]-v['position_m'])>1e-8 or abs(r[4]-v['speed_kph'])>1e-8:
                raise ValueError('Current route and physical state differ')
            weights,known,path=current_weights(r,v,root,routing)
            ready_vehicle=v['veh_no'] not in residual
            if ready_vehicle:
                for m,b in weights.items():assigned[link][m]+=b
            elif known:
                due=residual[v['veh_no']]['new_due_sec']/cfg.simulation.T_u_sec
                if due!=int(due):raise ValueError('Invalid existing arrival boundary')
                row=tags.setdefault(int(due),{})
                for m,b in weights.items():row[m]=row.get(m,0.)+b
            else:unknown+=1
            details.append(dict(vehicle=v['veh_no'],link=link,lane=v['lane_no'],ready=ready_vehicle,
                                known=known,weights=weights,current_route=r[6:9],physical_path=path))
        if abs(sum(assigned[link].values())-expected)>1e-8:
            raise ValueError('Queue relabeling changed the vehicle count')
    if abs(sum(sum(v.values()) for v in tags.values())+unknown-len(residual))>1e-8:
        raise ValueError('Named and unnamed initial arrivals do not conserve mass')
    if any(sum(row.values())>expected_calendar.get(step,0)+1e-8 for step,row in tags.items()):
        raise ValueError('Known route tags exceed their parent reservation')
    before={m:state.urban_movement_queue[m] for m in MOVEMENTS}
    result=copy.deepcopy(state)
    for link,queues in assigned.items():
        if not sum(queues.values()):continue
        if sides.get(link) not in (True,False):raise ValueError('Missing physical area membership')
        side='inside' if sides[link] else 'outside'
        target=result.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][link]
        for m,n in queues.items():
            delta=n-provenance[link].get('movement:'+m,0.)
            result.urban_movement_queue[m]+=delta
            result.local_observation_summary['urban_movement_queue'][m]+=delta
            target['movement:'+m]=n
            account=get_ledger(result).stocks['movement:'+m]
            if account[side]+delta < -1e-8:raise ValueError('Insufficient owned stock to relabel')
            account[side]+=delta
    result.gate_initial_route_tags[TARGET]=tags
    get_ledger(result).assert_stocks(model_inventory(result,cfg))
    for side in ('inside','outside'):
        if abs(sum(v[side] for v in ledger.stocks.values())-sum(v[side] for v in get_ledger(result).stocks.values()))>1e-8:
            raise ValueError('Area ownership changed')
    receipt=dict(source=TARGET,time_sec=state.time_sec,queue_before=before,
                 queue_after={m:result.urban_movement_queue[m] for m in MOVEMENTS},
                 tagged_arrivals=tags,known_initial_residual_veh=sum(sum(v.values()) for v in tags.values()),
                 untagged_residual_veh=unknown,vehicles=details,unknown_prior=routing,
                 known_ready_veh=sum(x['known'] and x['ready'] for x in details),
                 arrival_and_release_unchanged=True,future_observation_inputs=False,
                 source_pins={str(side_path):hashlib.sha256(side_path.read_bytes()).hexdigest()},
                 limits=['Unknown current routes retain beta; not claimed as inferred destinations.',
                         'Original post-head10285 source ownership/ETA remain; no stock is deleted.'])
    return result,receipt
