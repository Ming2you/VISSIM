"""Current-observation SC6 residual geometry; diagnostic, no future labels.

Reuse sourcepath292 for future accepted vehicles. The initial queue and stock
owners are retained. Only initial residual reservations are redistributed.
"""
import copy,hashlib,importlib.util,math
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('source_path292_reused',HERE.parent/'sourcepath292/candidate.py')
prior=importlib.util.module_from_spec(loader);loader.loader.exec_module(prior)
geometry,installed=prior.geometry,prior.installed
ORIGIN='SC12_to_SC6'
MODE='current_residual_geometry_u7'
TERMINAL='1210018302'


def eta_steps(distance_m,speed_kph,mean_speed_kph,dt,floor=20.):
    if not all(math.isfinite(x) for x in (distance_m,speed_kph,mean_speed_kph,dt,floor)):
        raise ValueError('Nonfinite current observation')
    if distance_m < -1e-6 or min(speed_kph,mean_speed_kph)<0 or min(dt,floor)<=0:
        raise ValueError('Invalid current distance, speed or clock')
    return max(1,math.ceil(max(0.,distance_m)/(max(speed_kph,mean_speed_kph,floor)/3.6)/dt))


def initialize(adapter,state,cfg,raw,geom,option):
    if option is None:return {'enabled':False}
    if option!=MODE:raise ValueError('Unknown initial cohort option')
    from evaluation.controllers.route_choice_corridor import _length,_travel_segments,_validate_path
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.urban_queue_model import approach_routing
    assert abs(raw['sim_sec']-state.time_sec)<1e-7
    records=raw['vehicle_records'];assert records['complete']
    assert not getattr(state,'gate_initial_route_tags',{}).get(ORIGIN)
    old_inventory=model_inventory(state,cfg);old_ledger=copy.deepcopy(get_ledger(state).stocks)
    old_queue=copy.deepcopy(state.urban_movement_queue)
    net=Path(geom['network_path']).read_bytes()
    assert hashlib.sha256(net).hexdigest()==geom['network_sha256']
    nodes={n.get('no'):n for n in ET.fromstring(net).findall('./links/link')}
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    routing=dict(approach_routing(cfg)[ORIGIN])
    keys={'storage:'+ORIGIN,*('movement:'+m for m in routing)}
    support={k:v for k,v in provenance.items() if set(v)&keys}
    assert support and all(set(v)<=keys for v in support.values()),'Mixed physical owner'
    physical=[v for v in records['records'] if str(v['link_no']) in support]
    per_lane=adapter._contiguous_stopline_queue(raw,per_lane=True)
    ready=set()
    for link,assignment in support.items():
        vs=[v for v in physical if str(v['link_no'])==link]
        assert abs(sum(assignment.values())-len(vs))<1e-7,(link,assignment,len(vs))
        # A stopped group on an internal connector is still in storage.
        # Only reproduce queues that the canonical physical owner assigned.
        q_assigned=sum(assignment.get('movement:'+m,0) for m in routing)
        if q_assigned<1e-7:continue
        for lane in {v['lane_no'] for v in vs}:
            n=float(per_lane.get((link,str(lane)),0.))
            front=sorted((v for v in vs if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
            assert n==int(n) and len(front)==n and all(v['stopped'] for v in front)
            ready.update(v['veh_no'] for v in front)
        nready=sum(v['veh_no'] in ready for v in vs)
        assert abs(nready-sum(assignment.get('movement:'+m,0) for m in routing))<1e-7
    residual=[v for v in physical if v['veh_no'] not in ready]
    dt=cfg.simulation.T_u_sec;now=round(state.time_sec/dt)
    arrivals=dict(state.urban_arrival_buffer[ORIGIN])
    assert arrivals==state.urban_storage_release_buffer[ORIGIN]
    # Replace the whole CURRENT physical residual, retaining any unrelated reservation.
    for stopped,tau in ((False,adapter._ARRIVAL_TAU_MOVING_SEC),(True,adapter._ARRIVAL_TAU_STOPPED_SEC)):
        # Canonical 1s projection is coarsened with ceil by the urban10 clock.
        due=now+max(1,math.ceil(tau/dt));n=sum(bool(v['stopped'])==stopped for v in residual)
        left=arrivals.get(due,0)-n
        assert left>=-1e-7,(due,left)
        if left>1e-8:arrivals[due]=left
        else:arrivals.pop(due,None)
    suffixes={}
    for spec in geom['sources'].values():
        for path in spec['paths']:
            _validate_path(path,nodes)
            for i,key in enumerate(path):
                p=tuple(path[i:])
                if key in support and p not in suffixes.setdefault(key,[]):suffixes[key].append(p)
    assert set(support)<=set(suffixes)
    lengths={k:_length(nodes[k]) for paths in suffixes.values() for path in paths for k in path}
    means={k:sum(v['speed_kph'] for v in physical if str(v['link_no'])==k)/
           sum(str(v['link_no'])==k for v in physical) for k in support}
    connector={'SC6_S_SC12_to_N_SC103':'10205','SC6_S_SC12_to_E_SC104':'10207','SC6_S_SC12_to_W_SC5':'10206'}
    lanes={}
    for m,key in connector.items():
        c=nodes[key];a=c.find('fromLinkEndPt')
        assert a.get('lane').split()[0]==TERMINAL
        first=int(a.get('lane').split()[1])
        lanes[m]=set(range(first,first+len(c.findall('./lanes/lane'))))
    tags={};receipts=[]
    for v in residual:
        key=str(v['link_no']);distances=[]
        for path in suffixes[key]:
            rows=_travel_segments(path,nodes,lengths,geom['stop_position_m'])
            # Current position replaces only the source segment's entry.
            if v['position_m']>rows[0]['stop']+1e-6:continue
            distances.append(rows[0]['stop']-v['position_m']+sum(r['stop']-r['start'] for r in rows[1:]))
        assert distances,(key,v['position_m'])
        distance=min(distances)
        choices={m:b for m,b in routing.items() if key!=TERMINAL or v['lane_no'] in lanes[m]}
        assert choices
        total=sum(choices.values());due=now+eta_steps(distance,v['speed_kph'],means[key],dt)
        row=tags.setdefault(due,{})
        for m,b in choices.items():row[m]=row.get(m,0.)+b/total
        arrivals[due]=arrivals.get(due,0.)+1.
        receipts.append(dict(veh=v['veh_no'],link=key,lane=v['lane_no'],distance_m=distance,
            speed_kph=v['speed_kph'],current_link_mean_kph=means[key],delay_sec=(due-now)*dt,
            stopped=bool(v['stopped']),destination_mode='current_last_lane' if key==TERMINAL else 'existing_beta_unknown_upstream',
            movement_shares={m:b/total for m,b in choices.items()}))
    assert abs(sum(sum(v.values()) for v in tags.values())-len(residual))<1e-7
    assert abs(sum(arrivals.values())-sum(state.urban_arrival_buffer[ORIGIN].values()))<1e-7
    state.urban_arrival_buffer[ORIGIN]=dict(arrivals)
    state.urban_storage_release_buffer[ORIGIN]=dict(arrivals)
    if not hasattr(state,'gate_initial_route_tags'):state.gate_initial_route_tags={}
    state.gate_initial_route_tags[ORIGIN]=tags
    assert state.urban_movement_queue==old_queue
    assert model_inventory(state,cfg)==old_inventory and get_ledger(state).stocks==old_ledger
    get_ledger(state).assert_stocks(model_inventory(state,cfg))
    return dict(enabled=True,physical_vehicles=len(physical),unchanged_ready_vehicles=len(ready),
        residual_vehicles=len(residual),by_link={k:sum(r['link']==k for r in receipts) for k in support},
        tagged_by_movement={m:sum(r.get(m,0.) for r in tags.values()) for m in routing},
        pending_by_delay={str((step-now)*dt):n for step,n in arrivals.items()},receipts=receipts,
        initial_inventory_unchanged=True,initial_queue_unchanged=True,future_labels_used=False,
        floor_kph=20.,floor_source='Existing Claude U7 / observation_projection contract',
        unresolved='Upstream destinations unknown; existing beta retained. Fixed SC10 gate not dynamically represented.')
