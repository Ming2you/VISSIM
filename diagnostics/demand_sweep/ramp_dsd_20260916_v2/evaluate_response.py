"""New-geometry, eight-port response calibration and held-action predictions.

Uses the canonical plant. Component residence is explicitly not Omega residence.
Training uses completed rule experiments; the new paired bank is not read by fit.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
import pickle
import re
import time
from collections import defaultdict
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CAL=HERE.parent/'user_native_20260914/metanet_calibration_v1'
TERMS=CAL.parent/'metanet_terms_implementation_v2'
sys.path[:0]=[str(ROOT/'.review-deps'),str(CAL),str(ROOT)]
from canonical_harness import load_base_model,DEFAULT_CONFIG
from boundary_factory import ObservationData,build_window,upstream_origin_split,PROTOCOL as BOUNDARY_PROTOCOL
from scoring import score_rollout

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,x):
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False)


def travel_profile(data):
    """Median complete native traversals before control, not congested future speeds."""
    samples={str(x['connector']):[] for x in data.definitions.values() if x['kind'] in ('ramp','offramp')}
    lengths={str(x['connector']):x['length_m'] for x in data.definitions.values() if x['kind'] in ('ramp','offramp')}
    for r in rows(data.folder/'port_events.csv'):
        if r['kind']=='departure' and float(r['time_s'])<=900 and r['residence_s'] and float(r['residence_s'])>0:
            samples[r['connector']].append(lengths[r['connector']]*3.6/float(r['residence_s']))
    if any(not x for x in samples.values()):raise ValueError('Missing pre-control connector travel sample')
    return {'occupancy_lane_loss':False,
        'travel_speed_kmh':{c:statistics.median(v) for c,v in samples.items()},
        'sample_counts':{c:len(v) for c,v in samples.items()},'latest_training_sec':900,
        'limits':'One constant speed per connector; complete-traversal median is a transit proxy, not saturation or startup-loss calibration.'}


def physical_dsds(geometry):
    chain={int(r['link']):(road,r['offset_m']) for road,rs in geometry['chains'].items() for r in rs}
    result=[]
    for d in ET.parse(HERE/'source_dsd/baseline.inpx').findall('./desSpeedDecisions/desSpeedDecision'):
        link=int(d.get('lane').split()[0])
        if link in chain:
            road,offset=chain[link]
            vals={int(x.get('desSpeedDistr')) for x in d.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}
            if vals!={120}:raise ValueError('Nonuniform baseline mainline desired speed')
            result.append((road,offset+float(d.get('pos')),int(d.get('no'))))
    return sorted(result)


def refresh_free_speed(data,out):
    """Update only measured cell free speeds; retain FD family and capacity rules."""
    config=load(DEFAULT_CONFIG)
    original=ROOT/config['freeway']['segment_params']
    document=load(original);evidence=[]
    for cell in data.geometry['cells']:
        road,i=cell['road'],cell['cell']
        sample=[r['v_kmh'] for t,rs in data.cells.items() if 0<t<=900 for r in rs
            if r['road']==road and r['cell']==i and r['n_veh']>=5 and r['rho_veh_per_km_lane']<10 and r['v_kmh'] is not None]
        row=document['segments'][f'{road}_S{i}'];before=row['v_free']
        if len(sample)>=3:
            ordered=sorted(sample);at=.85*(len(sample)-1);lo=int(at)
            row['v_free']=ordered[lo]+(at-lo)*(ordered[min(lo+1,len(ordered)-1)]-ordered[lo])
            row['v_free_source']='Current network pre900s N>=5,rho<10; sample p85; no controlled data'
            row['q_cap_veh_h_lane']=row['v_free']*row['rho_crit']*math.exp(-1/row['metanet_a_m'])
        evidence.append({'road':road,'cell':i,'samples':len(sample),'before':before,'after':row['v_free'],
            'status':'reestimated' if len(sample)>=3 else 'insufficient_samples_retained_previous'})
    document['source_calibration']={'network_sha256':data.geometry['network']['sha256'],
        'latest_sec':900,'previous_file':str(original),'previous_sha256':hashlib.sha256(original.read_bytes()).hexdigest()}
    document['arm']='New geometry: free speed refresh only; shape/dynamics calibrated separately'
    save(out/'segment_params.json',document);save(out/'free_speed_evidence.json',evidence)
    config['freeway']['segment_params']=str((out/'segment_params.json').relative_to(ROOT)).replace('\\','/')
    save(out/'config.json',config)
    return out/'config.json'


def refine_boundary_steps(steps,seconds):
    """Refine numerical integration, preserving the original command timeline."""
    if isinstance(seconds,bool) or seconds<1 or int(seconds)!=seconds or 10%seconds:
        raise ValueError('Refinement needs an integer-second divisor of10s')
    if seconds==10:return steps
    seconds=int(seconds);result=[]
    for parent in steps:
        start,end=parent['window_start_s'],parent['window_end_s']
        if int(start)!=start or end-start!=10:raise ValueError('Expected original10s boundary windows')
        for ramp,profile in parent.get('ramp_arrival_profile',{}).items():
            if len(profile)!=10 or abs(sum(profile)-parent['ramp_arrival_vph'][ramp]*10/3600)>1e-7:
                raise ValueError('Arrival profile and configured requests disagree')
        for t in range(int(start),int(end),seconds):
            child=copy.deepcopy(parent);child.update(window_start_s=t,window_end_s=t+seconds)
            for ramp,profile in parent.get('ramp_arrival_profile',{}).items():
                values=profile[t-int(start):t-int(start)+seconds]
                child['ramp_arrival_profile'][ramp]=values
                child['ramp_arrival_vph'][ramp]=sum(values)*3600/seconds
            result.append(child)
    return result


def window(data,model,cutoff,mode,profile,commands,*,port_origin_counts=None):
    w=build_window(data,cutoff,mode,profile)
    if model.port_origin_split:
        if mode!='history_forecast' or port_origin_counts is None:
            raise ValueError('Origin-conditioned split needs explicit cutoff-only origin observations')
        history=int(BOUNDARY_PROTOCOL['history_sec']);before=port_origin_counts[str(cutoff-history)];after=port_origin_counts[str(cutoff)]
        audit=[]
        for off,p in model.offramps.items():
            if p['road']!='FW_E':continue
            cell=p['from_cell'];ramps=[r for r,spec in model.ramps.items() if spec['road']=='FW_E' and spec['to_cell']==cell]
            history_flows=[data.flows[t,'FW_E',cell] for t in range(cutoff-history+30,cutoff+1,30)]
            departed=sum(float(r['off_departures']) for r in history_flows)
            downstream=sum(float(r['downstream_crossings']) for r in history_flows)
            merged=sum(float(r['ramp_merges']) for r in history_flows)
            if sum(p2['road']=='FW_E' and p2['from_cell']==cell for p2 in model.offramps.values())!=1:
                raise ValueError('Historical origin split needs one off-ramp per physical cell')
            ratio,bypass=upstream_origin_split(departed,downstream,merged,
                sum(sum(before[r]) for r in ramps),sum(sum(after[r]) for r in ramps))
            audit.append({'off':off,'history_start_s':cutoff-history,'history_end_s':cutoff,
                'before_ratio':w['boundary_steps'][0]['off_split_ratio'][off],'origin_conditioned_ratio':ratio,
                'observed_bypass_exits_veh':bypass})
            for step in w['boundary_steps']:step['off_split_ratio'][off]=ratio
        w['meta']['origin_conditioned_branch_splits']=audit
    if model.offramp_lanes:
        if mode != 'history_forecast':
            raise ValueError('Lane off-ramp candidate currently requires causal history boundaries')
        if not hasattr(data, 'port_events'):
            data.port_events = rows(data.folder/'port_events.csv')
        w['port_dynamics']['lane_exchange_rates_per_sec'] = {}
        lane_service = {}
        for off, spec in model.offramp_lanes.items():
            history = spec['history_sec']
            events = [r for r in data.port_events if str(r['connector']) == off
                      and cutoff-history < float(r['time_s']) <= cutoff]
            lane_service[off] = [sum(r['kind']=='departure' and int(r['lane'])==i for r in events)
                                 *3600/history for i in (1,2)]
            exposure = [0.,0.]; transfers = [[0.,0.],[0.,0.]]
            for end in range(cutoff-history+30,cutoff+1,30):
                before = [sum(row[2]==i for row in data.port_cohorts[str(end-30)][off]) for i in (1,2)]
                after = [sum(row[2]==i for row in data.port_cohorts[str(end)][off]) for i in (1,2)]
                observed = [r for r in events if end-30 < float(r['time_s']) <= end]
                net = [after[i-1]-before[i-1]-sum(r['kind']=='arrival' and int(r['lane'])==i for r in observed)
                       +sum(r['kind']=='departure' and int(r['lane'])==i for r in observed) for i in (1,2)]
                if sum(net) != 0:
                    raise ValueError('Lane exchange cannot absorb unexplained off-ramp vehicle loss')
                for i in range(2):
                    exposure[i] += 15*(before[i]+after[i])
                    transfers[1-i][i] += max(0.,net[i])
            rates = [[x/exposure[i] if exposure[i] else 0. for x in row] for i,row in enumerate(transfers)]
            if any(sum(transfers[i]) and not exposure[i] for i in range(2)):
                raise ValueError('Off-ramp lane transfer without source exposure')
            w['port_dynamics']['lane_exchange_rates_per_sec'][off] = rates
        for step in w['boundary_steps']:
            step['off_lane_drain_vph'] = copy.deepcopy(lane_service)
            if any(abs(sum(lane_service[off])-step['off_drain_vph'][off])>1e-7 for off in lane_service):
                raise ValueError('Lane events disagree with aggregate off-ramp drainage')
        w['meta']['offramp_lanes'] = {'history_end_s':cutoff,
            'exchange':'Net30s lane residuals / past lane vehicle-seconds; opposing within-bin changes unresolved'}
    heads=load(HERE/'controller_response_v1/heads.json')
    meter=load(DEFAULT_CONFIG)['actuation']['real_world_ramp_metering']
    w['ramp_dynamics']={'schema':'physical-ramp-boundary/v1','local_step_sec':1,'meter_cycle_sec':10,'ramps':{}}
    for mid,r in model.ramps.items():
        c=str(r['connector'])
        w['ramp_dynamics']['ramps'][mid]={'connector_id':c,'length_m':r['length_m'],
            'head_position_m':min(heads[c].values()),'lanes':r['lanes'],
            'spacing_m':model.base.network.urban_avg_vehicle_length_m,
            'travel_speed_kmh':profile['travel_speed_kmh'][c],'time_sec':cutoff,
            'initial_cohorts':data.port_cohorts[str(cutoff)][c],'initial_backlog_veh':0.}
        if mid in model.ramp_travel_speeds:
            travel=model.ramp_travel_speeds[mid]
            w['ramp_dynamics']['ramps'][mid].update(travel_speed_kmh=travel['upstream_kmh'],
                posthead_travel_speed_kmh=travel['posthead_kmh'])
    zero_lane_history = set()
    if model.ramp_receiving_nodes or model.ramp_arrival_profile:
        if not hasattr(data, 'port_events'):
            data.port_events = rows(data.folder/'port_events.csv')
        for mid, spec in model.ramp_receiving_nodes.items():
            c = str(model.ramps[mid]['connector'])
            arrivals = [r for r in data.port_events if str(r['connector']) == c and r['kind'] == 'arrival'
                        and cutoff-spec['lane_arrival_history_sec'] < float(r['time_s']) <= cutoff]
            lanes = model.ramps[mid]['lanes']
            if arrivals:
                counts = [sum(int(r['lane']) == i for r in arrivals) for i in range(1, lanes+1)]
                if sum(counts) != len(arrivals):
                    raise ValueError('Arrival lane outside physical ramp')
                shares = [n/len(arrivals) for n in counts]
            else:
                # No observed arrivals means zero forecast requests in the
                # causal model. Do not invent a destination/lane split.
                zero_lane_history.add(mid)
                shares = [1./lanes]*lanes
            w['ramp_dynamics']['ramps'][mid]['lane_arrival_shares'] = shares
    dsds=physical_dsds(data.geometry)
    w['vsl_zone_heads']={road:list(range(21)) for road in model.roads}
    for step in w['boundary_steps']:
        t=step['window_start_s']
        ends=[(t//30+1)*30] if mode=='conditioned_diagnostic' else list(range(cutoff-120,cutoff+1,30))
        greens,ids=commands(t)
        step['ramp_arrival_vph']={};step['ramp_head_service']={}
        for mid,r in model.ramps.items():
            c=str(r['connector']);selected=[data.ports[e,c] for e in ends]
            if any(float(x['unresolved_absences_veh']) for x in selected):raise ValueError('Unresolved ramp loss')
            step['ramp_arrival_vph'][mid]=sum(float(x['arrivals_veh']) for x in selected)*3600/(30*len(selected))
            if mid in zero_lane_history and step['ramp_arrival_vph'][mid] > 0:
                raise ValueError('Positive ramp arrival forecast without lane arrival history')
            g=greens.get(mid)
            curve=model.ramp_head_service_veh_per_cycle.get(mid)
            service=curve[str(g)] if curve and g is not None else r['lanes']*meter['per_lane_veh_per_cycle'][str(10 if g is None else g)]
            step['ramp_head_service'][mid]={'service_veh':service,
                'mode':'OFF' if g is None else 'GREEN','green_sec':g}
        step['vsl_commands']={}
        for cell in data.geometry['cells']:
            center=(cell['start_m']+cell['end_m'])/2
            upstream=[x for x in dsds if x[0]==cell['road'] and x[1]<=center]
            no=upstream[-1][2] if upstream else None
            step['vsl_commands'][f"{cell['road']}__seg{cell['cell']}"]=ids.get(no,120)
    if model.ramp_arrival_profile:
        # Repeat the observed temporal pattern, not a universal native signal
        # period. Each 150s/450s request total is exactly the old forecast total.
        # It remains an empirical arrival predictor and must be validated.
        history=model.ramp_arrival_profile['history_sec']
        targets=model.ramp_arrival_profile['ramps']
        counts=defaultdict(float)
        for r in data.port_events:
            stamp=float(r['time_s'])
            if r['kind']=='arrival' and (cutoff-history<stamp<=cutoff if mode=='history_forecast' else cutoff<stamp<=cutoff+450):
                counts[int(stamp),str(r['connector'])]+=1.
        for step in w['boundary_steps']:
            step['ramp_arrival_profile']={}
            for mid in targets:
                c=str(model.ramps[mid]['connector']);profile=[]
                for t in range(step['window_start_s']+1,step['window_end_s']+1):
                    observed_t=cutoff-history+1+(t-cutoff-1)%history if mode=='history_forecast' else t
                    profile.append(counts[observed_t,c])
                step['ramp_arrival_profile'][mid]=profile
                step['ramp_arrival_vph'][mid]=sum(profile)*3600/(step['window_end_s']-step['window_start_s'])
        w['meta']['ramp_arrival_profile']={'history_sec':history,'ramps':targets,
            'mode':'past empirical pattern repeated' if mode=='history_forecast' else 'future observed arrivals; diagnostic only'}
    w['boundary_steps']=refine_boundary_steps(w['boundary_steps'],model.base.simulation.T_f_sec)
    if model.base.simulation.T_f_sec!=10:
        w['meta']['numerical_refinement']={'original_step_sec':10,'step_sec':model.base.simulation.T_f_sec,
            'commands_and_request_totals_preserved':True}
    return w


def simulate(model,w,params):
    prediction=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],
        port_dynamics=w['port_dynamics'],ramp_dynamics=w['ramp_dynamics'],vsl_zone_heads=w['vsl_zone_heads'],
        residence_audit=model.component_residence,
        lane_group_dynamics=w.get('lane_group_dynamics'))
    checks=0
    for row in prediction['ramps']:
        if abs(row['conservation_residual_veh'])>1e-7:raise ArithmeticError('Ramp conservation')
        if row['accepted_merge_veh']>row['receiving_budget_veh']+1e-7:raise ArithmeticError('Ramp receiving budget')
        for local in row['local_receipts']:
            before=local['start']['downstream_travelling_veh']+local['start']['merge_ready_veh']
            after=local['end']['downstream_travelling_veh']+local['end']['merge_ready_veh']
            if after>max(before,row['nominal_posthead_storage_veh'])+1e-7:raise ArithmeticError('Posthead storage')
            if abs(local['conservation_residual_veh'])>1e-7:raise ArithmeticError('Local ramp conservation')
            checks+=1
        # Keep10s receipts and aggregate checks; avoid redundant nested1s JSON.
        del row['local_receipts']
    prediction['local_ramp_audit']={'checks':checks,'passed':True,'step_sec':1}
    return prediction


def component(data,model,cutoff,pred=None):
    if model.component_residence and pred is None:
        raise ValueError('Native component residence needs1s stock/event records;30s snapshots are insufficient. Use the native residence audit.')
    result={'freeway_ttt_veh_h':0.,'off_ttt_veh_h':0.,'ramp_ttt_veh_h':0.}
    last=None
    for t in ([] if model.component_residence else range(cutoff,cutoff+451,30)):
        if pred is None or t==cutoff:
            cohorts=data.port_cohorts[str(t)]
            current=[sum(x['n_veh'] for x in data.cells[t]),sum(len(cohorts[c]) for c in model.offramps),
                sum(len(cohorts[str(r['connector'])]) for r in model.ramps.values())]
        else:
            current=[sum(x['n_veh'] for x in pred['cells'] if x['time_s']==t),
                sum(x['n_veh'] for x in pred['ports'] if x['time_s']==t),
                sum(x['end']['connector_veh'] for x in pred['ramps'] if x['end_sec']==t)]
        if last is not None:
            for key,a,b in zip(result,last,current):result[key]+=(a+b)*30/7200
        last=current
    if pred is None:
        merged={mid:sum(float(data.ports[t,str(r['connector'])]['departures_veh']) for t in range(cutoff+30,cutoff+451,30)) for mid,r in model.ramps.items()}
        heads=rows(data.folder/'head_crossings.csv')
        served={mid:sum(cutoff<float(x['time_s'])<=cutoff+450 and x['ramp']==str(r['connector']) for x in heads) for mid,r in model.ramps.items()}
        backlog=None
    else:
        end={x['ramp']:x['end'] for x in pred['ramps'] if x['end_sec']==cutoff+450}
        merged={k:v['cumulative_merge_veh'] for k,v in end.items()}
        served={k:v['cumulative_head_service_veh'] for k,v in end.items()}
        backlog={k:v['outside_component_backlog_veh'] for k,v in end.items()}
    definition={}
    if model.component_residence:
        roads=pred['diagnostics']['roads']
        if {r['road'] for r in roads} != set(model.roads):
            raise ValueError('Incomplete directional residence ledger')
        result={'freeway_ttt_veh_h':sum(r['model_residence_10s_veh_h'] for r in roads),
            'off_ttt_veh_h':sum(r['off_connector_residence_event_veh_h'] for r in roads),
            'ramp_ttt_veh_h':sum(r['ramp_connector_residence_local_1s_veh_h'] for r in roads)}
        definition={'time_resolution':'Canonical10s mainline + local1s on-ramp + event-integrated off-ramp residence'}
    return {**result,**definition,'component_ttt_veh_h':sum(result.values()),'merges':merged,'head_service':served,
        'outside_component_backlog_end_veh':backlog,'scope':'42mainline cells +8on connectors +8off connectors; not Omega'}


def rule_commands(arm,runs=None,terminal=3000):
    runs=Path(runs) if runs else HERE/'rules_v1'
    records=[load(runs/f'run_{arm}/decision_{s}.json') for s in range(900,terminal,150)]
    def command(t):
        history=next((x['history'] for x in reversed(records) if x['sec']<=t),{})
        return (history.get('greens',{}) if arm in ('rm','both') else {},
            {int(k):v for k,v in history.get('vsl',{}).items()})
    return command


def late_calibration():
    """Bounded calibration on completed late congestion, with untouched arm holdouts."""
    folder=HERE/'controller_response_4500_v1'
    out=folder/'model_v3';out.mkdir(exist_ok=False)
    data={a:ObservationData(folder/a) for a in ('none','rm','vsl','both')}
    prior=HERE/'controller_response_v1/model_v2'
    config=load(prior/'config.json')
    old_model=load_base_model(data['none'].geometry,prior/'config.json')
    # Correct only the inherited single-ramp cap's lane count. This is a physical
    # upper bound, not a claim that observed demand is saturation capacity.
    caps={mid:old_model.base.network.ramp_capacity_veh_h[r['group']]*r['lanes']
          for mid,r in old_model.ramps.items()}
    config['freeway']['physical_ramp_capacity_vph']=caps
    save(out/'config.json',config)
    model=load_base_model(data['none'].geometry,out/'config.json')
    profile=travel_profile(data['none']);save(out/'port_profile.json',profile)
    old=load(prior/'selected_parameters.json')['parameters']
    training=[('none',2250),('none',3150),('rm',2700),('rm',3600)]
    holdout=[('none',4050),('rm',4050),('vsl',2700),('vsl',3600),('both',2700),('both',3600)]
    controls={a:rule_commands(a,HERE/'rules_4500_v1',4500) for a in data}
    windows={(a,t,mode):window(data[a],model,t,mode,profile,controls[a])
             for a,t in training+holdout for mode in ('conditioned_diagnostic','history_forecast')}
    actual={(a,t):component(data[a],model,t) for a,t in training+holdout}
    axes=[('rho_crit_multiplier',[.7,1.,1.3]),('tau_sec',[12.,24.,40.]),
          ('nu_km2_h',[12.,35.,65.]),('delta_merge',[0.,.5,1.]),('lane_drop_phi',[0.,3.,6.])]
    save(out/'protocol.json',{'training':training,'holdout':holdout,'axes':axes,
        'physical_capacity_vph':caps,'capacity_basis':'Previous per-ramp cap times actual physical lane count; no fitted capacity drop',
        'fit_mode':'conditioned_diagnostic; future boundary flows used only to isolate dynamics',
        'validation_modes':['conditioned_diagnostic','history_forecast'],
        'search':'One coordinate pass per direction, 3 values per axis; current incumbent always included',
        'loss':'direction mean of (speed RMSE/20)^2+(density RMSE/10)^2+(flow RMSE/1000)^2',
        'scope':'42 mainline cells +16 connectors; not coupled urban Omega; known recorded command replay',
        'native_holdout_seed':23,'canonical_defaults_changed':False})
    trace=[]
    def assess(target,params,items,mode,road=None,keep=False):
        records=[];loss=[]
        for a,t in items:
            w=windows[a,t,mode]
            prediction=simulate(target,w,params)
            scores={r:score_rollout(data[a],t,prediction,r) for r in target.roads}
            selected=[v for r,v in scores.items() if road is None or r==road]
            if any(v['invalid'] for v in selected):
                return {'loss':1e12,'invalid':True,'scores':scores}
            loss.append(statistics.mean(v['objective'] for v in selected))
            if keep:
                records.append({'arm':a,'cutoff':t,'mode':mode,'scores':scores,
                    'actual':actual[a,t],'prediction':component(data[a],target,t,prediction)})
        return {'loss':statistics.mean(loss),'records':records}
    baseline=assess(old_model,old,training,'conditioned_diagnostic',keep=True)
    capacity_only=assess(model,old,training,'conditioned_diagnostic',keep=True)
    save(out/'baseline_training.json',baseline);save(out/'capacity_only_training.json',capacity_only)
    best=copy.deepcopy(old)
    for road in model.roads:
        incumbent=assess(model,best,training,'conditioned_diagnostic',road)['loss']
        for key,values in axes:
            candidates=[]
            for value in values:
                trial=copy.deepcopy(best);trial['by_direction'][road][key]=value
                result=assess(model,trial,training,'conditioned_diagnostic',road)
                trace.append({'road':road,'key':key,'value':value,'loss':result['loss']})
                candidates.append((result['loss'],trial))
            score,trial=min(candidates,key=lambda x:x[0])
            if score<incumbent:
                incumbent=score;best=trial
            (out/'search_progress.json').write_text(json.dumps({'trace':trace,'incumbent':best},indent=2))
            print(f'{road} {key}: loss={incumbent:.5f}',flush=True)
    save(out/'selected_parameters.json',{'parameters':best,'adoption':'Experimental frozen candidate; evaluate history forecasts and new seed before adoption'})
    result={}
    for name,target,params in [('previous',old_model,old),('capacity_only',model,old),('calibrated',model,best)]:
        result[name]={}
        for label,items in [('training',training),('holdout',holdout)]:
            for mode in ('conditioned_diagnostic','history_forecast'):
                key=label+'_'+mode
                result[name][key]=assess(target,params,items,mode,keep=True)
        print(name+' evaluation complete',flush=True)
    save(out/'comparison.json',result);save(out/'provenance.json',model.provenance)
    print('Late calibration and reserved-arm evaluation complete',flush=True)


def online_data(prepared,output,sec,contract):
    """Incremental past native frames plus a current, paused COM snapshot.

    Native file's final frame may be buffered: never count it as complete.
    Only the exact decision snapshot closes that frame; gaps fail explicitly.
    These observations feed the controller, not a live validation dashboard.
    """
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer,PortObserver
    cache_path=output/'mpc_observer_cache.pkl'
    if cache_path.exists():
        with cache_path.open('rb') as f:cache=pickle.load(f)
    else:
        geometry=load(contract['geometry'])
        cache={'observer':Observer(geometry),'ports':PortObserver(geometry),
               'offset':0,'frame':{},'time':None,'fields':None}
    observer,ports=cache['observer'],cache['ports']
    def advance(t,frame):
        if t>observer.sec:
            observer.advance(t,frame);ports.advance(t,frame)
    path=output/'vissim_eval/baseline_001.fzp'
    byte_start=cache['offset']
    with path.open('rb') as f:
        f.seek(byte_start)
        while True:
            offset=f.tell();raw=f.readline()
            if not raw or not raw.endswith(b'\n'):
                cache['offset']=offset;break
            if raw.startswith(b'$VEHICLE:'):
                names=raw.decode('ascii').strip().split(':',1)[1].split(';')
                cache['fields']={k:names.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED')}
                continue
            if cache['fields'] is None:continue
            parts=raw.rstrip(b'\r\n').split(b';');ix=cache['fields']
            t=int(float(parts[ix['SIMSEC']]))
            if t>sec:raise ValueError('Future native frame in paused MPC observation')
            if cache['time'] is not None and t!=cache['time']:
                advance(cache['time'],cache['frame']);cache['frame']={}
            cache['time']=t
            cache['frame'][int(parts[ix['NO']])]=(int(parts[ix['LANE\\LINK\\NO']]),int(parts[ix['LANE\\INDEX']]),
                float(parts[ix['POS']]),float(parts[ix['SPEED']]))
    current={}
    for row in rows(output/f'mpc_vehicles_{sec}.csv'):
        lane=re.findall(r'\d+',row['lane'])
        if len(lane)!=2:raise ValueError('Unknown native lane address '+row['lane'])
        vehicle=int(row['vehicle'])
        if vehicle in current:raise ValueError('Duplicate COM vehicle')
        current[vehicle]=(int(lane[0]),int(lane[1]),round(float(row['position_m']),2),round(float(row['speed_kmh']),2))
    if observer.sec!=sec-1:
        raise ValueError(f'Native history not closed through {sec-1}; last complete={observer.sec}; no stale substitution')
    # Validate already-flushed rows of the decision frame against live snapshot.
    post_record_exits=[]
    if cache['time']==sec:
        for no,row in cache['frame'].items():
            if no not in current:
                # VISSIM records the final terminal position before removing the
                # vehicle; paused COM is after that removal. Never invent a live
                # vehicle to make the two observation phases numerically equal.
                location=observer.locate(row)
                if row[0] in ports.ports:
                    raise ValueError('Port vehicle absent between native and COM phases')
                if location:
                    road=location[0]
                    if row[0]!=observer.geometry['chains'][road][-1]['link'] or abs(observer.bounds[road][-1]-location[2])>row[3]/3.6+11.5:
                        raise ValueError('Nonterminal model vehicle absent between native and COM phases')
                post_record_exits.append({'vehicle':no,'link':row[0],'model_terminal':bool(location)})
                continue
            if row[:2]!=current[no][:2] or any(abs(a-b)>.011 for a,b in zip(row[2:],current[no][2:])):
                raise ValueError('Native and current COM decision snapshot disagree')
    advance(sec,current)
    data=ObservationData.__new__(ObservationData)
    data.folder=output;data.geometry=observer.geometry
    data.cells=defaultdict(list)
    for row in observer.cells:
        if row['time_s']>=sec-150:data.cells[row['time_s']].append(row)
    data.flows={(int(r['window_end_s']),r['road'],r['cell']):r for r in observer.flows if r['window_end_s']>=sec-150}
    data.boundaries={(int(r['window_end_s']),r['id']):r for r in observer.boundary_rows if r['window_end_s']>=sec-150}
    data.definitions=observer.boundaries;data.cell_geometry=observer.cell_geometry
    data.ports={(r['window_end_s'],str(r['connector'])):r for r in ports.rows if r['window_end_s']>=sec-150}
    data.port_cohorts={str(sec):ports.snapshots[str(sec)]}
    data.port_events = [dict(r) for r in ports.events if sec-150 < float(r['time_s']) <= sec]
    evidence={'sec':sec,'native_complete_through':sec-1,'com_snapshot_sec':sec,'com_bulk_calls':4,
        'snapshot_vehicles':len(current),'new_native_bytes':cache['offset']-byte_start,
        'native_frame_rows_crosschecked':len(cache['frame']) if cache['time']==sec else 0,
        'native_final_frame_to_COM_absences':post_record_exits,
        'current_state_phase':'Paused COM after native final-position recording and terminal removal',
        'features_latest_realized_sec':sec,'future_traffic_used':False}
    # Retain only the history needed by the next prediction, plus cumulative counts.
    observer.cells=[r for r in observer.cells if r['time_s']>=sec-150]
    observer.flows=[r for r in observer.flows if r['window_end_s']>=sec-150]
    observer.boundary_rows=[r for r in observer.boundary_rows if r['window_end_s']>=sec-150]
    ports.rows=[r for r in ports.rows if r['window_end_s']>=sec-150]
    ports.events=[];ports.snapshots={str(sec):ports.snapshots[str(sec)]}
    observer.evidence=[]
    with cache_path.open('wb') as f:pickle.dump(cache,f)
    save(output/f'mpc_observation_{sec}.json',evidence)
    return data,evidence


def mpc_choice(prepared,output,sec,history,policy):
    """Small centralized three-move MPC using the existing physical plant."""
    started=time.perf_counter();contract=load(prepared/'mpc_policy.json')
    for name,digest in contract['model_pins'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Pinned MPC plant changed during native run')
    data,observation=online_data(prepared,output,sec,contract)
    observed_at=time.perf_counter()
    folder=Path(contract['model_directory'])
    model=load_base_model(data.geometry,folder/'config.json')
    params=load(folder/'selected_parameters.json')['parameters'];profile=load(folder/'port_profile.json')
    arm=policy['rule']['arm'];greens=dict(history['greens'])
    zones={z:history['vsl'].get(str(ids[0]),120) for z,ids in policy['zone_dsds'].items()}
    if any(len({history['vsl'].get(str(i),120) for i in ids})!=1 for ids in policy['zone_dsds'].values()):
        raise ValueError('MPC zone contains differing applied commands')
    candidates=[('hold',greens,zones)]
    if arm in ('rm','both'):
        for mid,g in greens.items():
            if g>2:candidates.append(('restrict_'+mid,{**greens,mid:max(2,g-2)},zones))
        release={m:min(10,g+2) for m,g in greens.items()}
        if release!=greens:candidates.append(('release_meters',release,zones))
    if arm in ('vsl','both'):
        for z,v in zones.items():
            if v>60:candidates.append(('restrict_'+z,greens,{**zones,z:max(60,v-20)}))
        release={z:min(120,v+20) for z,v in zones.items()}
        if release!=zones:candidates.append(('release_vsl',greens,release))
    assessed=[]
    def evaluate(name,gs,zs):
        schedule=[]
        for k in range(3):
            future_g={m:max(2,min(10,greens[m]+(k+1)*(g-greens[m]))) for m,g in gs.items()}
            future_z={z:max(60,min(120,zones[z]+(k+1)*(v-zones[z]))) for z,v in zs.items()}
            schedule.append({'sec':sec+150*k,'greens':future_g,'zones':future_z})
        # Before a first restriction use native OFF; an opened activated meter
        # remains GREEN, matching the writer's persistent COM ownership.
        def command(t):
            move=schedule[min(2,int((t-sec)//150))]
            active_g={m:g for m,g in move['greens'].items() if g<10 or m in history['states']}
            ids={d:move['zones'][z] for z,values in policy['zone_dsds'].items() for d in values}
            return active_g,ids
        w=window(data,model,sec,'history_forecast',profile,command)
        prediction=simulate(model,w,params)
        for r in prediction['diagnostics']['roads']:
            if r['density_projection_count'] or r['jam_density_exceedance_count'] or r['negative_density_count'] or r['continuity_residual_max_veh']>1e-6:
                raise ArithmeticError('Invalid MPC candidate physical rollout')
        parts=component(data,model,sec,prediction)
        ramp_wait=sum((r['start']['outside_component_backlog_veh']+r['end']['outside_component_backlog_veh'])*10/7200 for r in prediction['ramps'])
        source_wait=0.
        for road in model.roads:
            backlog=0.
            for end in range(sec+30,sec+451,30):
                requested=sum(s['source_demand_vph'][road]*10/3600 for s in w['boundary_steps'] if end-30<=s['window_start_s']<end)
                admitted=sum(f['source_admissions'] for f in prediction['flows'] if f['road']==road and f['window_end_s']==end)
                after=max(0.,backlog+requested-admitted)
                source_wait+=(backlog+after)*30/7200;backlog=after
        return {'name':name,'greens':dict(gs),'zones':dict(zs),
            'planned_controls':schedule,
            'cost_veh_h':parts['component_ttt_veh_h']+ramp_wait+source_wait,
            'components':parts,'extra_ramp_wait_veh_h':ramp_wait,'extra_source_wait_veh_h':source_wait,
            'local_conservation_checks':prediction['local_ramp_audit']['checks']}
    initialized_at=time.perf_counter()
    for candidate in candidates:
        if assessed and (len(assessed)>=contract['candidate_budget'] or time.perf_counter()-initialized_at>contract['soft_budget_sec']):break
        assessed.append(evaluate(*candidate))
    if arm=='both' and len(assessed)<contract['candidate_budget'] and time.perf_counter()-initialized_at<contract['soft_budget_sec']:
        rm=min((r for r in assessed if r['zones']==zones),key=lambda r:r['cost_veh_h'])
        vs=min((r for r in assessed if r['greens']==greens),key=lambda r:r['cost_veh_h'])
        if rm['greens']!=greens and vs['zones']!=zones:
            assessed.append(evaluate('joint_best_single_levers',rm['greens'],vs['zones']))
    selected=min(assessed,key=lambda r:r['cost_veh_h'])
    save(output/f'mpc_candidates_{sec}.json',{'cutoff':sec,'observation':observation,'candidates':assessed,
        'selected':selected['name'],'scope':contract['scope'],'objective':contract['objective'],
        'unexamined_candidates':max(0,len(candidates)-len(assessed)),
        'observation_sec':observed_at-started,'model_initialization_sec':initialized_at-observed_at,
        'control_calculation_sec':time.perf_counter()-initialized_at})
    return {'greens':selected['greens'],'zones':selected['zones'],'selected':selected['name'],
        'planned_controls':selected['planned_controls'],
        'predicted_cost_veh_h':selected['cost_veh_h'],'hold_cost_veh_h':assessed[0]['cost_veh_h'],
        'candidate_count':len(assessed),'scope':contract['scope']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fit',action='store_true')
    parser.add_argument('--refresh-free-speed',action='store_true')
    parser.add_argument('--late-calibration',action='store_true');args=parser.parse_args()
    if args.late_calibration:
        late_calibration();return
    out=HERE/'controller_response_v1'/('model_v2' if args.refresh_free_speed else 'model_v1');out.mkdir(exist_ok=False)
    data={a:ObservationData(HERE/'controller_response_v1'/a) for a in ('none','rm','vsl','both')}
    config=refresh_free_speed(data['none'],out) if args.refresh_free_speed else DEFAULT_CONFIG
    model=load_base_model(data['none'].geometry,config)
    profile=travel_profile(data['none']);save(out/'port_profile.json',profile)
    old=load(TERMS/'fit_dynamic_v1/parameters.json')['parameters']
    # Small response-oriented training set, exclusively pre-existing experiments.
    training=[('none',900),('none',1350),('rm',1800)]
    windows=[(a,t,window(data[a],model,t,'history_forecast',profile,rule_commands(a))) for a,t in training]
    observed={(a,t):component(data[a],model,t) for a,t in training}
    candidates=[('previous',old)]
    if args.fit:
        if args.refresh_free_speed:
            for critical in (1.,1.2,1.4):
                for delta in (0.,.5,1.):
                    p=copy.deepcopy(old)
                    for r in model.roads:p['by_direction'][r]['v_free_multiplier']=1.
                    p['by_direction']['FW_E'].update(rho_crit_multiplier=critical,delta_merge=delta)
                    candidates.append((f'critical_{critical}_delta_{delta}',p))
        else:
            for delta in (0.,.3,.6,1.):
                p=copy.deepcopy(old);p['by_direction']['FW_E']['delta_merge']=delta
                candidates.append(('delta_'+str(delta),p))
    save(out/'protocol.json',{'training':training,'candidates':candidates,'evaluation_horizon_sec':450,
        'fixed_except':('Pre900 measured cell free speeds, FW_E critical density multiplier and merge coefficient' if args.refresh_free_speed else 'FW_E merge coefficient; new geometry and pre900 travel medians shared'),
        'loss':'mean(speed_RMSE/20)^2 + mean(relative component TTT error)^2 + mean(eight merge count error/10)^2',
        'not_claimed':'No causal ranking training from different initial states; no Omega cost or full controller certification.',
        'validation':'New same-state paired bank excluded from fitting. Rule schedules are known command replay, not forecast future feedback actions.'})
    fit=[]
    for name,params in candidates:
        values=[];details=[]
        for arm,t,w in windows:
            prediction=simulate(model,w,params)
            actual=observed[arm,t];estimate=component(data[arm],model,t,prediction)
            scores={r:score_rollout(data[arm],t,prediction,r) for r in model.roads}
            if any(x['invalid'] for x in scores.values()):raise ArithmeticError('Invalid conservation/density prediction')
            loss=sum((x['speed']['rmse']/20)**2 for x in scores.values())/2
            loss+=((estimate['component_ttt_veh_h']-actual['component_ttt_veh_h'])/max(1.,actual['component_ttt_veh_h']))**2
            loss+=sum(((estimate['merges'][k]-actual['merges'][k])/10)**2 for k in model.ramps)/8
            values.append(loss);details.append({'arm':arm,'cutoff':t,'prediction':estimate,'actual':actual,'scores':scores})
        fit.append({'name':name,'parameters':params,'loss':statistics.mean(values),'records':details})
        print(name+' training complete',flush=True)
    selected=min(fit,key=lambda x:x['loss'])
    save(out/'fit.json',fit);save(out/'selected_parameters.json',{'name':selected['name'],'parameters':selected['parameters'],
        'adoption':'Experimental, pending response ranking/holdout; canonical defaults unchanged'})
    # Freeze predictions before opening the new VISSIM outcomes.
    protocol=load(HERE/'response_pairs_v1/protocol.json')
    forecasts={}
    for arm,seq in {'none':{'green':[],'vsl':[]},**protocol['candidate_bank']}.items():
        def command(t):
            index=min(3,max(0,(t-1650)//150))
            return ({'RM_C10490':seq['green'][index]} if seq['green'] else {},
                {d:seq['vsl'][index] for d in (59,60,61,62)} if seq['vsl'] else {})
        w=window(data['none'],model,1650,'history_forecast',profile,command)
        save(out/('paired_window_'+arm+'.json'),w)
        prediction=simulate(model,w,selected['parameters'])
        save(out/('paired_prediction_'+arm+'.json'),prediction)
        forecasts[arm]=component(data['none'],model,1650,prediction)
    save(out/'paired_forecasts.json',forecasts)
    save(out/'provenance.json',model.provenance)
    print(json.dumps({'selected':selected['name'],'forecasts':forecasts},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
