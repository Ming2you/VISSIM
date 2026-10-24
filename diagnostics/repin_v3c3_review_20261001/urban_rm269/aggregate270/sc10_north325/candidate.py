"""Aggregate SC6->SC12 fixed intermediate gate; explicit diagnostic only.

Current vehicles are read once at assimilation. Rollout holds aggregate amounts
in the EXISTING source storage, split by due step, downstream delay and known turn.
"""
from evaluation.controllers.calibrated_initial_projection import verify_speed as _repair_verify_speed, own_head as _repair_own_head, move_passed as _repair_move_passed
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager
import copy,hashlib,json,math,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import step_gate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import membership
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import steps

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
TARGET='SC6_to_SC12';ATTR='_sc10_north325'
TERMINAL='1220015000';GATE='1210018202'
PRE={'1220018202','10208',GATE};POST={'1220018201',TERMINAL}
MOVS={'SC12_N_SC6_to_S_SC16':'10235','SC12_N_SC6_to_W_SC11':'10236','SC12_N_SC6_to_E_SC106':'10237'}
SHARED=['1220018202','10208',GATE,'10218','1220018201','10223',TERMINAL]
NETWORK_SHA='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'

def require(ok,msg):
    if not ok:raise ValueError(msg)

def measure(path,links,start,stop):
    from evaluation.controllers.route_choice_corridor import _length,_validate_path,_travel_segments
    _validate_path(path,links)
    pieces=_travel_segments(path,links,{k:_length(links[k]) for k in path},stop)
    require(0<=start<=pieces[0]['stop']+1e-6,'Current position is after requested boundary')
    pieces[0]['start']=start
    n=math.fsum(x['stop']-x['start'] for x in pieces)
    require(n>=-1e-6,'Negative current distance')
    return max(n,0.)

def current_route(row,root):
    if all(v is None for v in row[6:10]):return None,None
    require(all(v is not None for v in row[6:9]) and row[8]=='STATIC','Partial or unsupported route')
    d=root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{int(row[6])}']")
    r=None if d is None else d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(row[7])}']")
    require(r is not None,'Current route absent from pinned network')
    path=[d.get('link'),*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
    link=str(row[1]);require(path.count(link)==1 and path.count(TERMINAL)==1,'Ambiguous current path')
    i=path.index(link);j=path.index(TERMINAL)
    require(i<=j and j+1<len(path),'Current path does not reach terminal turn')
    require(row[9] is None or str(int(row[9]))==path[i+1],'Route and next connector disagree')
    movement=next((m for m,c in MOVS.items() if c==path[j+1]),None)
    require(movement is not None,'Current known turn outside movement catalog')
    return movement,path[i:j+1]

def schedule(state,due,n,movement=None):
    from src.models import urban_queue_model as uqm
    require(n>=0 and int(due)==due,'Invalid aggregate reservation')
    if not n:return
    uqm._schedule(state.urban_arrival_buffer,TARGET,int(due),n)
    uqm._schedule(state.urban_storage_release_buffer,TARGET,int(due),n)
    if movement is not None:
        row=state.gate_initial_route_tags.setdefault(TARGET,{}).setdefault(int(due),{})
        row[movement]=row.get(movement,0.)+n

def register(local,due,post,n,movement=None):
    require(due>local['last_step'] and post>=1 and n>=0,'Invalid gate arrival')
    key=(int(due),(int(post),movement))
    local['pending'][key]=local['pending'].get(key,0.)+n
    local['received']+=n


def current_owned_stock(cfg, raw, owners, provenance):
    """Retain the existing source share; exact native partitions take precedence.

    Fractional shared-link attribution is the existing aggregate ownership, not
    a claim about individual identity. Other source stock is never reassigned.
    """
    from evaluation.controllers.native_internal_input import record_partition, _signal_authority
    partitions, proof = record_partition(cfg, raw)
    relevant = {'storage:'+TARGET, *('movement:'+m for m in MOVS)}
    physical, weights, evidence = [], {}, {}
    for link in sorted(owners):
        rows = [v for v in raw['vehicle_records']['records'] if str(v['link_no']) == link]
        support = provenance[link]
        require(all(math.isfinite(n) and n >= 0 for n in support.values()) and
                abs(sum(support.values())-len(rows)) < 1e-8, 'Current physical stock differs')
        count = sum(support.get(k,0.) for k in relevant)
        other = {k:n for k,n in support.items() if k not in relevant and n}
        if not other:
            selected, rule = [(v,1.) for v in rows], 'whole_source'
        elif link in partitions:
            _, authority = _signal_authority(cfg, proof[link]['input_no'])
            require(not any(n for k,n in support.items() if k.startswith('movement:')),
                    'Shared native source has ambiguous ready stock')
            selected = []
            for v in rows:
                head = authority['head_position_by_lane_m'][str(v['lane_no'])]
                target = authority['pre_head_storage'] if v['position_m'] <= head else authority['post_head_storage']
                if target == TARGET: selected.append((v,1.))
            rule = 'exact_current_native_head_partition'
        else:
            require(not any(n for k,n in support.items() if k.startswith('movement:')),
                    'Shared source has ambiguous ready stock')
            require(rows and 0 < count <= len(rows), 'Invalid shared source fraction')
            selected, rule = [(v,count/len(rows)) for v in rows], 'retained_aggregate_ownership_fraction'
        require(abs(sum(n for _,n in selected)-count) < 1e-8, 'Current source partition differs')
        for v,n in selected:
            require(v['veh_no'] not in weights, 'Duplicate current vehicle')
            physical.append(v); weights[v['veh_no']] = n
        evidence[link] = dict(source_vehicles=count, other_owners=other, rule=rule)
    return physical, weights, evidence

def install(cfg,state,raw,frame,network,lanes):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.urban_queue_model import approach_routing
    from plant.src.vissim_strict.signal_program import parse_sig
    require(cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10,'Reviewed clocks required')
    require(not hasattr(state,ATTR) and not hasattr(cfg.network,ATTR),'Duplicate gate')
    require(not getattr(state,'_omega_travel_reservations',None),'Distance objective needs separate provider')
    require(TARGET not in getattr(state,'gate_initial_route_tags',{}) and TARGET not in getattr(cfg.network,'physical_gate_travel',{}),'Existing owner')
    require(hasattr(cfg.network,'physical_ramp_branches'),'Aggregate current-route consumer required')
    require(hashlib.sha256(network).hexdigest()==NETWORK_SHA,'Unreviewed geometry')
    rs=raw['vehicle_records'];now=state.time_sec;dt=cfg.simulation.T_u_sec
    require(rs.get('complete') and frame.get('complete') and frame.get('schema')=='lane-plant-frame/v1','Complete current records required')
    require(raw['sim_sec']==frame['time_s']==now and all(rs[k]==now for k in ('capture_sim_sec_before','capture_sim_sec_after','paused_at_sim_sec')),'Stale observation')
    ledger=get_ledger(state)
    require(ledger.event_count==0 and ledger.ttt_veh_h==0 and not ledger.captures_response,'Initial assimilation only')
    routing=dict(approach_routing(cfg)[TARGET]);require(set(routing)==set(MOVS),'Movement catalog changed')
    root=ET.fromstring(network);links={x.get('no'):x for x in root.findall('./links/link')}
    heads=root.findall('./signalHeads/signalHead')
    gates=[h for h in heads if h.get('sg')=='10 4']
    require(len(gates)==3 and {h.get('lane').split()[0] for h in gates}=={GATE},'Gate geometry changed')
    gp=min(float(h.get('pos')) for h in gates)
    stop=min(float(h.get('pos')) for h in heads if h.get('lane').split()[0]==TERMINAL)
    controller=root.find("./signalControllers/signalController[@no='10']")
    require(controller.get('active')=='true' and controller.get('type')=='FIXEDTIME','Gate is not fixed')
    np=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    sig=np.parent/controller.get('supplyFile2').removeprefix('#data#')
    program=parse_sig(sig,int(controller.get('progNo')))
    factor_path=ROOT/'outputs/storage_effective_lanes_20260904.json'
    factor=json.loads(factor_path.read_bytes())['storage_effective_lanes'][TARGET]
    speed_receipt=_repair_verify_speed(state,cfg,TARGET,factor)
    require(not any(v['target_storage']==TARGET for v in cfg.network.native_internal_inputs['inputs'].values()),'Uncovered internal input')
    sources={}
    for m,s in cfg.network.urban_movements.items():
        if s.get('receiving_link')!=TARGET:continue
        turns=cfg.network.control_area_routes['movement:'+m]['physical_turns']
        require(len(turns)==1 and turns[0]['to_link']==SHARED[0],'Incoming physical path ambiguous')
        tr=turns[0];connector=links[tr['connector']];fr=connector.find('fromLinkEndPt')
        first=int(fr.get('lane').split()[1]);allowed=range(first,first+len(connector.findall('./lanes/lane')))
        source_heads=[h for h in heads if h.get('lane').split()[0]==tr['from_link'] and int(h.get('lane').split()[1]) in allowed]
        require(source_heads,'Source head missing')
        start=min(float(h.get('pos')) for h in source_heads)
        path=[tr['from_link'],tr['connector'],*SHARED]
        j=path.index(GATE)
        sources[m]=dict(pre_m=measure(path[:j+1],links,start,gp),post_m=measure(path[j:],links,gp,stop))
    require(len(sources)==3,'Source catalog changed')
    prov=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    require(TERMINAL in prov or not any(str(v['link_no'])==TERMINAL for v in rs['records']),
            'Nonempty terminal is missing physical provenance')
    owners={k for k,v in prov.items() if v.get('storage:'+TARGET,0)>0 or any(v.get('movement:'+m,0)>0 for m in MOVS)}
    require(owners<=PRE|POST,'Uncovered source-owned current link')
    physical,weights,ownership=current_owned_stock(cfg,raw,owners,prov)
    current={int(v[0]):v for v in frame['vehicles']}
    require(len({v['veh_no'] for v in physical})==len(physical),'Duplicate current vehicle')
    ready=set()
    for link in owners:
        vv=[v for v in physical if str(v['link_no'])==link];p=prov[link]
        require(abs(sum(p.get(k,0.) for k in {'storage:'+TARGET,*('movement:'+m for m in MOVS)})-sum(weights[v['veh_no']] for v in vv))<1e-8,'Current owner differs')
        q=sum(p.get('movement:'+m,0) for m in MOVS)
        if q:
            require(link==TERMINAL,'Unexpected upstream ready owner')
            for lane in {v['lane_no'] for v in vv}:
                n=lanes.get((link,str(lane)),0.)
                front=sorted((v for v in vv if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
                require(n==int(n) and len(front)==n and all(v['stopped'] for v in front),'Queue identity differs')
                ready.update(v['veh_no'] for v in front)
        require(q==sum(v['veh_no'] in ready for v in vv),'Queue count differs')
    old=state.urban_arrival_buffer.get(TARGET,{})
    require(old==state.urban_storage_release_buffer.get(TARGET,{}) and abs(sum(old.values())-sum(weights.values())+len(ready))<1e-8,'Paired initial reservations differ')
    require(all(k*dt>now for k in old),'Past reservation')
    result=copy.deepcopy(state);local=dict(pending={},ready={},received=0.,discharged=0.,last_step=int(now/dt)-1,history=[])
    result.urban_arrival_buffer[TARGET]={};result.urban_storage_release_buffer[TARGET]={}
    assigned=dict.fromkeys(MOVS,0.);detail=[];passed=[]
    for v in physical:
        row=current[v['veh_no']];link=str(v['link_no']);n=weights[v['veh_no']]
        require(row[1]==v['link_no'] and row[2]==v['lane_no'] and abs(row[3]-v['position_m'])<1e-8 and abs(row[4]-v['speed_kph'])<1e-8,'Frame and stock differ')
        movement,path=current_route(row,root)
        if link==TERMINAL and v['veh_no'] in ready and v['position_m']>_repair_own_head(root,v):
            raise ValueError('Passed-head stopped-ready reassignment is not yet qualified')
        if v['veh_no'] in ready:
            require(n==1.,'Ready vehicle has fractional owner')
            turn_weights={movement:1.} if movement else routing
            for m,b in turn_weights.items():assigned[m]+=b
            detail.append(dict(vehicle=v['veh_no'],ready=True,movement=movement));continue
        if path is None:
            require(link in POST,'Unknown route before middle signal needs explicit feasible path coverage')
            path=[TERMINAL] if link==TERMINAL else ['1220018201','10223',TERMINAL]
        speed=max(20.,v['speed_kph'])
        if link==TERMINAL and v['position_m']>_repair_own_head(root,v):
            require(n==1.,'Passed-head vehicle has fractional owner')
            item=_repair_move_passed(result,cfg,v,movement,root,TARGET)
            passed.append(item);detail.append(dict(item,already_passed_terminal_head=True));continue
        if link==GATE and v['position_m']>_repair_own_head(root,v):
            distance=measure(path,links,v['position_m'],stop)
            due=int(now/dt)+steps(max(distance,1e-8),speed,20.,dt)
            schedule(result,due,n,movement)
            detail.append(dict(vehicle=v['veh_no'],ready=False,pre_signal=False,
                already_passed_intermediate_head=True,movement=movement,arrival_sec=due*dt));continue
        if link in PRE:
            j=path.index(GATE);pre=measure(path[:j+1],links,v['position_m'],gp);post=measure(path[j:],links,gp,stop)
            due=int(now/dt)+steps(pre,speed,20.,dt);post_steps=steps(post,speed,20.,dt)
            register(local,due,post_steps,n,movement)
            detail.append(dict(vehicle=v['veh_no'],ready=False,pre_signal=True,movement=movement,gate_due_sec=due*dt,post_sec=post_steps*dt))
        else:
            distance=measure(path,links,v['position_m'],stop)
            due=int(now/dt)+steps(max(distance,1e-8),speed,20.,dt)
            schedule(result,due,n,movement)
            detail.append(dict(vehicle=v['veh_no'],ready=False,pre_signal=False,movement=movement,arrival_sec=due*dt))
    for item in detail:item['owned_vehicles']=weights[item['vehicle']]
    sides,mp=membership();require(type(sides.get(TERMINAL)) is bool,'Area membership absent')
    side='inside' if sides[TERMINAL] else 'outside'
    support=result.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].setdefault(TERMINAL,{})
    for m,n in assigned.items():
        delta=n-prov.get(TERMINAL,{}).get('movement:'+m,0.)
        result.urban_movement_queue[m]+=delta;result.local_observation_summary['urban_movement_queue'][m]+=delta
        support['movement:'+m]=n;get_ledger(result).stocks['movement:'+m][side]+=delta
        require(get_ledger(result).stocks['movement:'+m][side]>=-1e-8,'Negative current owner')
    require(abs(local['received']+sum(result.urban_arrival_buffer[TARGET].values())+len(passed)-sum(old.values()))<1e-8,'Reservation conservation failed')
    get_ledger(result).assert_stocks(model_inventory(result,cfg))
    geom=dict(source=TARGET,sources=sources,lane_factor=factor,rate_veh_h=3*float(cfg.network.movement_capacity_veh_h),
        rate_support='3 physical lanes times existing nominal rate, not fitted saturation',sig=str(sig),sig_sha=hashlib.sha256(sig.read_bytes()).hexdigest(),
        prog_no=int(controller.get('progNo')),offset=float(controller.get('offset')),cycle_sec=program.cycle_length_sec,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (np,sig,factor_path,mp)})
    local['initial_post_head']=passed
    setattr(result,ATTR,local);setattr(cfg.network,ATTR,geom)
    receipt=dict(time_sec=now,current_ownership=ownership,current_initial=detail,initial_post_head=passed,speed_receipt=speed_receipt,old_calendar=old,direct_post_calendar=result.urban_arrival_buffer[TARGET],
        initial_gate_veh=local['received'],ready_before={m:state.urban_movement_queue[m] for m in MOVS},ready_after=assigned,
        source_pins=geom['source_pins'],future_observation_inputs=False,source_stock_unchanged=True,production_adopted=False)
    return result,receipt

@contextmanager
def enabled():
    from evaluation.controllers import urban_flow_accounting as ufa,route_choice_corridor as rc
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
    from plant.src.vissim_strict.signal_program import parse_sig
    old_receive,old_advance=ufa._receive_corridor,rc.advance;programs={};records=[]
    def receive(state,cfg,movement,vehicles,step,*,entry_step=None):
        geom=getattr(cfg.network,ATTR,None)
        if geom is None or cfg.network.urban_movements[movement].get('receiving_link')!=TARGET:
            return old_receive(state,cfg,movement,vehicles,step,entry_step=entry_step)
        require(not old_receive(state,cfg,movement,vehicles,step,entry_step=entry_step),'Another corridor owns transfer')
        dt=cfg.simulation.T_u_sec;g=geom['sources'][movement]
        speed=state.urban_link_speed_kph[TARGET]/geom['lane_factor'];nominal=cfg.network.urban_avg_speed_km_h
        pre=steps(g['pre_m'],speed,nominal,dt);post=steps(g['post_m'],speed,nominal,dt)
        entry=step if entry_step is None else entry_step
        register(getattr(state,ATTR),entry+pre,post,vehicles)
        records.append(dict(source=movement,entry_sec=entry*dt,gate_due_sec=(entry+pre)*dt,post_sec=post*dt,vehicles=float(vehicles)))
        return True
    def advance(state,control,demand,cfg,step):
        result=old_advance(state,control,demand,cfg,step)
        geom=getattr(cfg.network,ATTR,None)
        if geom is None:return result
        key=geom['sig'],geom['sig_sha'],geom['prog_no']
        if key not in programs:
            require(hashlib.sha256(Path(key[0]).read_bytes()).hexdigest()==key[1],'Fixed program changed')
            programs[key]=parse_sig(Path(key[0]),key[2])
        dt=cfg.simulation.T_u_sec;local=getattr(state,ATTR)
        green=_union_green_overlap(programs[key],('4',),step*dt,(step+1)*dt,geom['offset'])
        release,row=step_gate(local,step,green,geom['rate_veh_h'],dt)
        for (post,movement),n in release.items():schedule(state,step+1+post,n,movement)
        occupied=cfg.network.urban_link_storage_veh[TARGET]-state.urban_link_storage[TARGET]
        tracked=row['remaining_transit']+row['remaining_ready']
        require(tracked<=occupied+1e-7,'Gate stock exceeds its physical parent')
        row.update(sec=step*dt,parent_occupied=occupied);local['history'].append(row)
        ledger=get_ledger(state)
        if ledger and ledger.captures_response:
            used={'storage:'+TARGET:row['discharged']}
            ledger.record_resource_allocation('diagnostic_SC10N_ready','SC10:SG4',row['ready_before'],used)
            ledger.record_resource_allocation('diagnostic_SC10N_green','SC10:SG4',row['budget'],used)
        return result
    ufa._receive_corridor=receive;rc.advance=advance
    try:yield records
    finally:ufa._receive_corridor=old_receive;rc.advance=old_advance
