"""One internal-source subset retains a sequential head before its left turn.

Tags are subsets of existing storage/queues. W/N use their existing p3 service;
only the left subset additionally needs the upstream p3. Existing W/N actual
departures get priority in that shared physical head budget. No new stock or
boundary event is created by a tag's head crossing.
"""
from collections import defaultdict
from copy import deepcopy
import json
import math

from evaluation.controllers.control_area_objective import emit_transfer, get_ledger
from evaluation.controllers.projection_support import complete_records

EPS=1e-8


def configure_input(cfg,row,tree,links,physical,contract,raw):
    from evaluation.controllers.native_internal_input import _read,empirical_source_choice
    from evaluation.controllers.route_choice_corridor import _length,_travel_segments,_validate_path
    document=json.loads(_read(row['route_evidence']).read_text(encoding='utf-8-sig'))
    if document.get('schema')!='native-input-prehead/v1':raise ValueError('Unknown native pre-head contract')
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    _read(document['network'])
    if snapshot_network_sha256(raw)!=document['network']['sha256']:
        raise ValueError('Native pre-head network fingerprint differs')
    source=row['physical_source'];origin=row['target_storage'];path=document['input_path']
    if path!=row['approach_path'] or path[0]!=source or set(row['physical_projection_links'])!=set(path[:2]):
        raise ValueError('Native pre-head exclusive input partition differs')
    outgoing={k for k,x in links.items() if x.find('fromLinkEndPt') is not None
              and x.find('fromLinkEndPt').get('lane').split()[0]==source}
    if empirical_source_choice(document['empirical_first_connector'],source,outgoing,tree,links,raw)!={path[1]}:
        raise ValueError('Native pre-head empirical source receiver differs')
    _validate_path(path,links)
    decision=tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{document['decision']}']")
    if (decision is None or decision.get('link')!=path[-1] or decision.get('allVehTypes')!='true'
            or decision.get('routeChoiceMeth')!='STATIC' or float(decision.get('pos'))!=document['decision_position_m']):
        raise ValueError('Native pre-head downstream decision differs')
    if not all(physical.get(k) is True for k in path) or origin not in cfg.network.urban_link_storage_veh:
        raise ValueError('Native pre-head source is not inside its existing finite approach')
    if float(raw['demand']['urban_volume_vph_by_gate'].get(origin,0.))!=0.:
        raise ValueError('Native pre-head input duplicates external gate demand')
    lengths={k:_length(x) for k,x in links.items()}
    segments=_travel_segments(path,links,lengths,float(decision.get('pos')))
    heads={h.get('no'):h for h in tree.findall('./signalHeads/signalHead')}
    actual_heads={k:h.attrib for k,h in heads.items() if h.get('lane').split()[0]==path[-1]}
    if actual_heads!=document['first_heads'] or len(actual_heads)!=document['first_head_lanes']:
        raise ValueError('Native pre-head first physical heads differ')
    plan=json.loads(_read(document['selected_plan']).read_text(encoding='utf-8-sig'))
    first_phase=document['first_phase'];signal,phase=first_phase.rsplit('_',1)
    first_groups=set(map(str,plan['controllers'][signal.removeprefix('SC')]['phase_signal_groups'][phase]))
    if any(h['sg'].split()[0]!=signal.removeprefix('SC') or h['sg'].split()[1] not in first_groups
           or h['allVehTypes']!='true' or float(h['complRate'])!=1 for h in actual_heads.values()):
        raise ValueError('Native pre-head service lacks selected phase authority')
    first_stop=min(float(h['pos']) for h in actual_heads.values())
    if first_stop<=float(decision.get('pos')):raise ValueError('Native choice must precede its first head')
    native_routes={r.get('no'):r for r in decision.findall('./vehRoutSta/vehicleRouteStatic')}
    if set(native_routes)!=set(document['branches']):raise ValueError('Native pre-head branch set differs')
    branches={};weight_sum=0.
    for tag,branch in document['branches'].items():
        native=native_routes[tag];native_path=[path[-1]]+[x.get('key') for x in native.findall('./linkSeq/intObjectRef')]+[native.get('destLink')]
        if native_path!=branch['native_path'] or native.get('relFlow','')!=branch['rel_flow'] or native.get('formula'):
            raise ValueError('Native pre-head route path/weight differs')
        _validate_path(native_path,links)
        flow=native.get('relFlow','')
        parts=flow.split()
        if len(parts)!=2 or parts[0]!='2' or not parts[1].startswith('0:'):
            raise ValueError('Native pre-head prior supports only the reviewed constant interval')
        weight=float(parts[1][2:])
        if not math.isfinite(weight) or weight<=0:raise ValueError('Native pre-head branch weight is invalid')
        movement=branch['movement'];spec=cfg.network.urban_movements.get(movement,{})
        turn=contract.get('movement:'+movement,{}).get('physical_turns',[])
        if len(turn)!=1 or spec.get('origin')!=origin or spec.get('phase')!=branch['phase']:
            raise ValueError('Native pre-head movement/receiver contract differs')
        actual=turn[0];i=native_path.index(actual['connector'])
        if native_path[i-1:i+2]!=[actual['from_link'],actual['connector'],actual['to_link']]:
            raise ValueError('Native pre-head movement is not its actual native turn')
        if not all(physical.get(k) is True for k in native_path[:i+2]):
            raise ValueError('Native pre-head stage unexpectedly crosses Omega')
        if spec.get('receiving_link')!=branch['receiving_storage']:
            raise ValueError('Native pre-head canonical receiver differs')
        if movement!=document['left_movement'] and spec['phase']!=first_phase:
            raise ValueError('Native W/N must retain the same first phase')
        if movement==document['left_movement']:
            last_head=heads[document['left_head']]
            groups=set(map(str,plan['controllers'][signal.removeprefix('SC')]['phase_signal_groups'][spec['phase'].rsplit('_',1)[1]]))
            if (last_head.attrib!=document['left_head_attributes'] or last_head.get('lane').split()[0]!=actual['from_link']
                    or last_head.get('sg').split()[1] not in groups or spec['phase']==first_phase
                    or last_head.get('lane').split()[1]!=links[actual['connector']].find('fromLinkEndPt').get('lane').split()[1]):
                raise ValueError('Native left second-head authority differs')
            between=_travel_segments(native_path[:i],links,lengths,float(last_head.get('pos')))
            between[0]['start']=first_stop
            interhead=sum(s['stop']-s['start'] for s in between)
            if interhead<0:raise ValueError('Native second head precedes first head')
        branches[tag]={'movement':movement,'weight':weight,'phase':spec['phase']}
        weight_sum+=weight
    for branch in branches.values():branch['probability']=branch['weight']/weight_sum
    left=document['left_movement'];reference=document['capacity_reference_movement']
    if reference!=left or left not in {b['movement'] for b in branches.values()}:
        raise ValueError('Native head capacity reference is not the one-lane left movement')
    cap=float(cfg.network.movement_capacity_by_movement_veh_h[reference])
    if not math.isfinite(cap) or cap<=0:raise ValueError('Native head capacity reference is invalid')
    return {'source_contract_validated':True,'minimum_approach_distance_m':sum(s['stop']-s['start'] for s in segments)+first_stop-float(decision.get('pos')),
            'prehead_spec':{'origin':origin,'decision':document['decision'],'branches':branches,'segments_to_decision':segments,
                'decision_to_head_m':first_stop-float(decision.get('pos')),'left_movement':left,
                'wn_movements':[b['movement'] for b in branches.values() if b['movement']!=left],
                'first_phase':first_phase,'capacity_reference_movement':reference,'physical_head_lanes':document['first_head_lanes'],
                'interhead_distance_m':interhead,'scope':document['scope']}}


def _inputs(cfg):
    from evaluation.controllers.sdmpc_prediction_cache import input_catalog
    cached = input_catalog(cfg, 'native_choice_prehead')
    if cached is not None:
        return cached
    return {n:r for n,r in getattr(cfg.network,'native_internal_inputs',{}).get('inputs',{}).items() if r.get('kind')=='native_choice_prehead'}


def _due(state,cfg,origin,step,distance,speed=None):
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO
    speed=max(float(speed if speed is not None else state.urban_link_speed_kph.get(origin,cfg.network.urban_avg_speed_km_h)),
              cfg.network.urban_avg_speed_km_h/OBSERVED_SPEED_DELAY_CAP_RATIO)
    return step+max(1,math.ceil(max(0.,distance)/(speed/3.6)/cfg.simulation.T_u_sec))


def _check(state,cfg):
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_check(state,cfg)
    local=state.native_input_prehead_state;inputs=_inputs(cfg);grouped=defaultdict(float)
    for cohort in local['cohorts']:
        n=cohort['vehicles']
        if not math.isfinite(n) or n<0:raise ValueError('Native pre-head tag is invalid')
        spec=inputs[cohort['input']]['prehead_spec']
        key=('queue',spec['branches'][cohort['route']]['movement']) if cohort['stage']=='queue' else ('storage',spec['origin'])
        grouped[key]+=n
    for (kind,key),n in grouped.items():
        actual=state.urban_movement_queue.get(key,0.) if kind=='queue' else cfg.network.urban_link_storage_veh[key]-state.urban_link_storage[key]
        if n>actual+EPS:raise ValueError('Native pre-head subset exceeds actual '+kind+': '+key)
    if not math.isclose(sum(grouped.values()),local['initial_veh']+local['generated_veh']-local['departed_scope_veh'],abs_tol=EPS,rel_tol=0):
        raise ValueError('Native pre-head subset accounting does not close')


def initialize(state,cfg,raw):
    inputs=_inputs(cfg)
    if not inputs:return {}
    if hasattr(state,'native_input_prehead_state'):raise ValueError('Native pre-head initialized twice')
    step=int(round(state.time_sec/cfg.simulation.T_u_sec));cohorts=[];tagged=defaultdict(float)
    for no,row in inputs.items():
        spec=row['prehead_spec']
        for vehicle in complete_records(raw):
            link=str(vehicle['link_no'])
            if link not in row['physical_projection_links']:continue
            segments=spec['segments_to_decision'];index=next(i for i,s in enumerate(segments) if s['link']==link)
            distance=max(0.,segments[index]['stop']-vehicle['position_m'])+sum(s['stop']-s['start'] for s in segments[index+1:])
            cohorts.append({'input':no,'vehicles':1.,'stage':'decision','route':None,
                            'due':_due(state,cfg,spec['origin'],step,distance,vehicle['speed_kph'])})
            tagged[spec['origin']]+=1.
    for origin,n in tagged.items():
        occupied=cfg.network.urban_link_storage_veh[origin]-state.urban_link_storage[origin]
        if n>occupied+EPS:raise ValueError('Native exclusive source exceeds its observed storage')
        fraction=max(0.,1.-n/occupied) if occupied else 1.
        for buffer in (state.urban_arrival_buffer,state.urban_storage_release_buffer):
            if origin in buffer:buffer[origin]={step:n*fraction for step,n in buffer[origin].items()}
    state.native_input_prehead_state={'last_step':step-1,'finished_step':step-1,'cohorts':cohorts,'initial_veh':sum(tagged.values()),
        'generated_veh':0.,'departed_scope_veh':0.,'wn_actual':{},'first_head_service_veh':0.,'existing_wn_budget_overdraw_veh':0.}
    _check(state,cfg)
    return {'native_prehead_initial_tagged_veh':sum(tagged.values())}


def receive_generated(state,cfg,no,vehicles,step):
    inputs=_inputs(cfg)
    if no not in inputs:return False
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_generate(state,cfg,no,vehicles,step)
    local=state.native_input_prehead_state;spec=inputs[no]['prehead_spec']
    if local['last_step']!=step:raise ValueError('Native pre-head generation requires current advance')
    distance=sum(s['stop']-s['start'] for s in spec['segments_to_decision'])
    local['cohorts'].append({'input':no,'vehicles':vehicles,'stage':'decision','route':None,
                            'due':_due(state,cfg,spec['origin'],step,distance)})
    local['generated_veh']+=vehicles;_check(state,cfg);return True


def advance(state,cfg,step):
    inputs=_inputs(cfg)
    if not inputs:return {}
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_advance(state,cfg,step)
    from src.models import urban_queue_model as uqm
    local=state.native_input_prehead_state
    ledger=get_ledger(state)
    capture=ledger is not None and ledger.captures_response
    if step!=local['last_step']+1 or local['finished_step']!=local['last_step']:
        raise ValueError('Native pre-head requires sequential completed candidate steps')
    local['last_step']=step;local['wn_actual']={};additions=[]
    for cohort in local['cohorts']:
        if cohort['due']>step or cohort['stage']=='queue':continue
        spec=inputs[cohort['input']]['prehead_spec']
        if cohort['stage']=='decision':
            for tag,branch in spec['branches'].items():
                additions.append(dict(cohort,vehicles=cohort['vehicles']*branch['probability'],stage='approach',route=tag,
                    due=_due(state,cfg,spec['origin'],step,spec['decision_to_head_m'])))
            cohort['vehicles']=0.;continue
        movement=spec['branches'][cohort['route']]['movement'];queue=state.urban_movement_queue.get(movement,0.)
        available=max(0.,uqm._queue_max(cfg,movement,cfg.network.urban_movements[movement])-queue)
        n=min(cohort['vehicles'],available)
        if capture:
            ledger.record_resource_allocation('native_prehead_queue_receiving', 'movement:'+movement,
                available, {'input:'+cohort['input']+':route:'+str(cohort['route']):n})
        if not n:continue
        state.urban_link_storage[spec['origin']]+=n;state.urban_movement_queue[movement]=queue+n
        emit_transfer(state,cfg,'storage:'+spec['origin'],'movement:'+movement,n,preserve_area=True)
        cohort['vehicles']-=n;additions.append(dict(cohort,vehicles=n,stage='queue',passed_first=(movement!=spec['left_movement']),ready=step))
    local['cohorts']=[c for c in local['cohorts'] if c['vehicles']>0.]+additions
    _check(state,cfg);return {'native_prehead_tagged_veh':sum(c['vehicles'] for c in local['cohorts'])}


def _blocked(local,inputs,movement,step):
    return sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='queue'
        and inputs[c['input']]['prehead_spec']['branches'][c['route']]['movement']==movement
        and (not c['passed_first'] or c['ready']>step))


def limit_intended(state,cfg,movement,available,intended,step):
    inputs=_inputs(cfg)
    if not inputs:return intended
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_limit(state,cfg,movement,available,intended,step)
    blocked=_blocked(state.native_input_prehead_state,inputs,movement,step)
    return min(intended,max(0.,available-blocked))


def receive_accepted(state,cfg,movement,vehicles,step):
    inputs=_inputs(cfg)
    if not inputs:return
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_accept(state,cfg,movement,vehicles,step)
    local=state.native_input_prehead_state
    if local['last_step']!=step:raise ValueError('Native pre-head accepted service has wrong step')
    if any(movement in r['prehead_spec']['wn_movements'] for r in inputs.values()):
        local['wn_actual'][movement]=local['wn_actual'].get(movement,0.)+vehicles
    eligible_before=state.urban_movement_queue.get(movement,0.)+vehicles-_blocked(local,inputs,movement,step)
    if vehicles>eligible_before+EPS:
        raise ValueError('Native blocked first-head cohort was discharged early')
    for cohort in local['cohorts']:
        if (cohort['stage']!='queue' or not cohort['passed_first'] or cohort['ready']>step
                or inputs[cohort['input']]['prehead_spec']['branches'][cohort['route']]['movement']!=movement):continue
        accepted=vehicles*cohort['vehicles']/eligible_before if eligible_before>0 else 0.
        cohort['vehicles']-=accepted;local['departed_scope_veh']+=accepted
    local['cohorts']=[c for c in local['cohorts'] if c['vehicles']>0.]
    _check(state,cfg)


def finish_step(state,control,cfg,step):
    inputs=_inputs(cfg)
    if not inputs:return {}
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.prehead_finish(state,control,cfg,step)
    from src.models import urban_queue_model as uqm
    local=state.native_input_prehead_state;additions=[];served=overdraw=0.
    ledger=get_ledger(state)
    capture=ledger is not None and ledger.captures_response
    if local['last_step']!=step or local['finished_step']!=step-1:
        raise ValueError('Native first-head service requires one finish per step')
    for no,row in inputs.items():
        spec=row['prehead_spec'];reference=cfg.network.urban_movements[spec['capacity_reference_movement']]
        first=dict(reference,phase=spec['first_phase'])
        budget=uqm._phase_green_fraction(control,cfg,first,urban_step_index=step)*cfg.simulation.T_u_h*spec['physical_head_lanes']*uqm._movement_capacity_flow(control,cfg,spec['capacity_reference_movement'],reference)
        consumed=sum(local['wn_actual'].get(m,0.) for m in spec['wn_movements'])
        remaining=max(0.,budget-consumed);overdraw+=max(0.,consumed-budget)
        blocked=[c for c in local['cohorts'] if c['input']==no and c['stage']=='queue' and not c['passed_first']]
        total=sum(c['vehicles'] for c in blocked);accepted=min(total,remaining)
        accepted_sources = {} if capture else None
        for cohort in blocked:
            n=accepted*cohort['vehicles']/total if total else 0.
            if capture:
                key='input:'+no+':movement:'+spec['left_movement']
                accepted_sources[key]=accepted_sources.get(key,0.)+n
            if not n:continue
            cohort['vehicles']-=n;additions.append(dict(cohort,vehicles=n,passed_first=True,
                ready=_due(state,cfg,spec['origin'],step,spec['interhead_distance_m'])))
        served+=accepted
        if capture:
            # Only the left subset is constrained by this residual allocator.
            # W/N service was accepted elsewhere; its excess over the inherited
            # reference remains existing_wn_budget_overdraw_veh, not a certified
            # shared-head constraint (post-head stock/timing remain unresolved).
            ledger.record_resource_allocation('residual_tag_service',
                spec['origin']+':'+spec['first_phase'], remaining, accepted_sources)
    local['cohorts']=[c for c in local['cohorts'] if c['vehicles']>0.]+additions
    local['first_head_service_veh']+=served;local['existing_wn_budget_overdraw_veh']+=overdraw
    local['finished_step']=step
    _check(state,cfg)
    return {'native_prehead_first_service_veh':served,'native_prehead_existing_wn_budget_overdraw_veh':overdraw}
