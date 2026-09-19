"""Calibrate ramp transit/receiving with mainline parameters frozen.

Local replay conditions on observed arrivals and mainline states ONLY to identify
the ramp equations. It is not an online forecast. Coupled forecasts are separate.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, gap_acceptance_supply_vph
import copy
import json
import statistics
import hashlib
from collections import Counter

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=e.ROOT
BASE=H/'spatial_calibration_20260919/combined_v3/model'
TARGETS=['RM_C10490','RM_C10484']
STARTS=[900,1350,1800,2250,2700,3150,3600,4050]

def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')

def prepare_data(folder):
    d=e.ObservationData(folder)
    d.events=e.rows(folder/'port_events.csv')
    d.heads=e.rows(folder/'head_crossings.csv')
    d.headstocks={(int(r['time_s']),r['ramp']):r for r in e.rows(folder/'head_stock_1s.csv')}
    d.arrivals=Counter((int(r['time_s']),r['connector']) for r in d.events if r['kind']=='arrival')
    d.head_counts=Counter((int(r['time_s']),r['ramp']) for r in d.heads)
    d.departures=Counter((int(r['time_s']),r['connector']) for r in d.events if r['kind']=='departure')
    return d

def travel_fit(d):
    hpos=e.load(H/'controller_response_v1/heads.json');result={};evidence={}
    for mid in TARGETS:
        c=mid[4:];b=next(x for x in d.definitions.values() if x['id']==mid)
        head=min(hpos[c].values())
        arrivals={r['vehicle']:r for r in d.events if r['connector']==c and r['kind']=='arrival'}
        heads={r['vehicle']:r for r in d.heads if r['ramp']==c};samples=[]
        for r in d.events:
            if r['connector']!=c or r['kind']!='departure' or float(r['time_s'])>900:continue
            vehicle=r['vehicle']
            if vehicle not in arrivals or vehicle not in heads:continue
            a=arrivals[vehicle];h=heads[vehicle]
            before=float(h['time_s'])-float(a['time_s']);after=float(r['time_s'])-float(h['time_s'])
            if before>0 and after>0:
                samples.append({'vehicle':vehicle,'upstream_kmh':(head-float(a['position_m']))*3.6/before,
                    'posthead_kmh':(b['length_m']-head)*3.6/after})
        if not samples:raise ValueError('No pre-control ramp travel samples')
        result[mid]={k:statistics.median(x[k] for x in samples) for k in ['upstream_kmh','posthead_kmh']}
        evidence[mid]={'samples':len(samples),'latest_s':900,'values':samples,
            'meaning':'Median complete pre-control transit; queue-free speed only approximately identified.'}
    return result,evidence

def local_case(d,model,start,mid,commands):
    w=e.window(d,model,start,'history_forecast',e.load(BASE/'port_profile.json'),commands)
    c=mid[4:];spec=w['ramp_dynamics']['ramps'][mid];b=model.ramps[mid]
    road=b['road'];upstream=int(b['to_cell'])-1
    q=[]
    for sec in range(start,start+450):
        stamp=sec//30*30
        cell=next(r for r in d.cells[stamp] if r['road']==road and r['cell']==upstream)
        flow=d.flows[stamp,road,upstream]
        out=float(flow['downstream_crossings']);off=float(flow['off_departures'])
        split=off/(off+out) if off+out else 0.
        q.append(cell['rho_veh_per_km_lane']*(cell['v_kmh'] or 0.)*(1-split))
    observed={k:sum(float(d.headstocks[t,c][source]) for t in range(start+1,start+451))/3600
        for k,source in [('pre','prehead_n'),('post','posthead_n')]}
    observed.update(head=sum(d.head_counts[t,c] for t in range(start+1,start+451)),
        merge=sum(d.departures[t,c] for t in range(start+1,start+451)),
        end=len(d.port_cohorts[str(start+450)][c]))
    return {'spec':spec,'start':start,'arrivals':[d.arrivals[t,c] for t in range(start+1,start+451)],
        'q':q,'commands':w['boundary_steps'],'observed':observed,'ramp':mid,
        'capacity':model._config(road,{}).network.ramp_capacity_veh_h[mid]}

def replay(case,speeds,gap):
    spec=copy.deepcopy(case['spec']);spec.pop('lane_arrival_shares',None)
    if speeds:
        spec.update(travel_speed_kmh=speeds['upstream_kmh'],posthead_travel_speed_kmh=speeds['posthead_kmh'])
    buf=PhysicalRampBoundary(**spec);pre=post=0.
    for i,arrival in enumerate(case['arrivals']):
        t=case['start']+i;state=buf.snapshot()
        pre+=(state['upstream_travelling_veh']+state['head_ready_veh'])/3600
        post+=(state['downstream_travelling_veh']+state['merge_ready_veh'])/3600
        ready=buf.begin_interval(t,1.)['eligible_merge_veh']
        cap=case['capacity']
        if gap:cap=min(cap,gap_acceptance_supply_vph(case['q'][i],*gap))
        buf.commit_merge(min(ready,cap/3600))
        head=case['commands'][i//10]['ramp_head_service'][case['ramp']]
        g=head['green_sec'];active=g is None or t%10<g
        mode='OFF' if g is None else 'GREEN' if active else 'RED'
        service=head['service_veh']/(10 if g is None else g) if active else 0.
        buf.apply_head_service(service,mode=mode,green_sec=None if g is None else g if active else 0,
            posthead_capacity_veh=(buf.length_m-buf.head_position_m)*buf.lanes/buf.spacing_m)
        buf.finish_interval(arrival)
    end=buf.snapshot()
    pred={'pre':pre,'post':post,'head':end['cumulative_head_service_veh'],'merge':end['cumulative_merge_veh'],'end':end['connector_veh']}
    scales={'pre':.5,'post':.25,'head':10.,'merge':10.,'end':10.}
    return {'predicted':pred,'actual':case['observed'],
        'loss':sum(((pred[k]-case['observed'][k])/scale)**2 for k,scale in scales.items()),
        'conservation':end['conservation_residual_veh']}

def main():
    out=HERE/'local_v1';out.mkdir(exist_ok=False)
    train=prepare_data(H/'controller_response_4500_v1/none')
    model=e.load_base_model(train.geometry,BASE/'config.json')
    speeds,evidence=travel_fit(train)
    write(out/'travel_evidence.json',evidence)
    pairs=prepare_data(H/'response_pairs_v1/observations/rm_ramp')
    protocol=e.load(H/'response_pairs_v1/protocol.json')
    seq=protocol['candidate_bank']['rm_ramp']['green']
    command=lambda t: ({'RM_C10490':seq[int((t-1650)//150)]},{})
    cases={m:[local_case(train,model,t,m,lambda t: ({},{})) for t in STARTS]+
        [local_case(pairs,model,1650,m,command)] for m in TARGETS}
    candidates=[None]+[(tc,tf) for tf in [1.5,2.,2.5] for tc in [2.5,3.,3.5,4.,4.5,5.,6.] if tc>=tf]
    results={};selected={}
    for m in TARGETS:
        rows=[]
        for travel in [None,speeds[m]]:
            for gap in candidates:
                rs=[replay(c,travel,gap) for c in cases[m]]
                row={'speeds':travel,'gap':gap,'loss':statistics.mean(r['loss'] for r in rs),'records':rs}
                rows.append(row)
        best=min(rows,key=lambda x:x['loss']);selected[m]=best;results[m]=rows
        print(m,'baseline',rows[0]['loss'],'selected',best['loss'],best['speeds'],best['gap'],flush=True)
    write(out/'fit_results.json',results)
    write(out/'selected.json',selected)
    config=e.load(BASE/'config.json')
    config['freeway']['physical_ramp_travel_speeds']={m:r['speeds'] for m,r in selected.items() if r['speeds']}
    for m,r in selected.items():
        if r['gap']:
            config['freeway']['physical_ramp_receiving_nodes'][m]={'critical_gap_sec':r['gap'][0],
                'followup_sec':r['gap'][1],'lane_arrival_history_sec':150}
    dest=out/'model';dest.mkdir();write(dest/'config.json',config)
    for filename in ['selected_parameters.json','port_profile.json']:write(dest/filename,e.load(BASE/filename))
    write(out/'protocol.json',{'training_seed':13,'training_starts':STARTS,'one_paired_rm_start':1650,
        'identification':'Conditional replay: observed arrivals and mainline states; NOT causal forecast',
        'mainline_coefficients_frozen':True,'scales':{'pre_ttt':.5,'post_ttt':.25,'head_merge_end_veh':10},
        'gap_candidates':candidates,'fixed_head_service':True,'no_reward_or_benefit_fit':True,
        'baseline_config_sha256':hashlib.sha256((BASE/'config.json').read_bytes()).hexdigest()})

if __name__=='__main__':main()
