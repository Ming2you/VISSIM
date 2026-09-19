"""Frozen same-state predictions and post-run response diagnosis for this bank."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import copy
import statistics

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent


def predict():
    protocol=e.load(HERE/'protocol.json')
    data=e.ObservationData(Path(protocol['baseline_observations']))
    out=HERE/'frozen_predictions';out.mkdir(exist_ok=False)
    result={}
    for name,folder in [('previous',PARENT/'controller_response_v1/model_v2'),
                        ('calibrated',PARENT/'controller_response_4500_v1/model_v4')]:
        model=e.load_base_model(data.geometry,folder/'config.json')
        params=e.load(folder/'selected_parameters.json')['parameters']
        profile=e.load(folder/'port_profile.json')
        result[name]={}
        for arm,sequence in {'none':{'green':[],'vsl':[]},**protocol['candidate_bank']}.items():
            def command(t):
                index=min(len(protocol['command_times'])-1,int((t-protocol['start_s'])//150))
                return ({protocol['meter_id']:sequence['green'][index]} if sequence['green'] else {},
                        {d:sequence['vsl'][index] for d in protocol['dsd_ids']} if sequence['vsl'] else {})
            w=e.window(data,model,protocol['start_s'],'history_forecast',profile,command)
            prediction=e.simulate(model,w,params)
            result[name][arm]=e.component(data,model,protocol['start_s'],prediction)
            e.save(out/f'{name}_{arm}_window.json',w)
            e.save(out/f'{name}_{arm}_prediction.json',prediction)
        e.save(out/f'{name}_parameters.json',params)
        e.save(out/f'{name}_provenance.json',model.provenance)
    e.save(out/'summary.json',result)
    sources=[Path(e.__file__),folder/'config.json',folder/'selected_parameters.json',folder/'port_profile.json',
             ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    e.save(out/'source_pins.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    for name,arms in result.items():
        print(name,{a:{'delta_ttt':r['component_ttt_veh_h']-arms['none']['component_ttt_veh_h'],
                       'merge10490':r['merges']['RM_C10490']} for a,r in arms.items()},flush=True)


def analyze():
    protocol=e.load(HERE/'protocol.json');start=protocol['start_s'];end=start+450
    data={'none':e.ObservationData(Path(protocol['baseline_observations']))}
    data.update({a:e.ObservationData(HERE/'observations'/a) for a in protocol['candidate_bank']})
    folder=PARENT/'controller_response_4500_v1/model_v4'
    model=e.load_base_model(data['none'].geometry,folder/'config.json')
    params=e.load(folder/'selected_parameters.json')['parameters'];profile=e.load(folder/'port_profile.json')
    out=HERE/'response_analysis';out.mkdir(exist_ok=False)
    result={}
    for arm,d in data.items():
        seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
        def command(t):
            i=min(len(protocol['command_times'])-1,int((t-start)//150))
            return ({protocol['meter_id']:seq['green'][i]} if seq['green'] else {},
                    {no:seq['vsl'][i] for no in protocol['dsd_ids']} if seq['vsl'] else {})
        actual=e.component(d,model,start)
        r={'actual_component':actual,'conditioned':{}}
        for mode in ('physical_ports','observed_merges'):
            w=e.window(d,model,start,'conditioned_diagnostic',profile,command)
            if mode=='physical_ports':
                pred=e.simulate(model,w,params)
                parts=e.component(d,model,start,pred)
            else:
                pred=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],
                    port_dynamics=w['port_dynamics'],ramp_dynamics=None,vsl_zone_heads=w['vsl_zone_heads'])
                parts=None
            scores={road:e.score_rollout(d,start,pred,road) for road in model.roads}
            r['conditioned'][mode]={'scores':scores,'component':parts,
                'future_traffic_used':True,'meaning':'Known future boundary diagnostic, not online forecast'}
            r['conditioned'][mode]['boundary_interface_residual_veh']={
                road:{key:sum(float(f[key]) for f in pred['flows'] if f['road']==road)
                          -sum(float(d.flows[t,road,c][key]) for t in range(start+30,end+1,30) for c in range(21))
                      for key in ('source_admissions','ramp_merges','off_departures')}
                for road in model.roads}
            e.save(out/f'{arm}_{mode}.json',pred)
        baseline=Path(protocol['baseline_run']).parent/'analysis/none'
        area=e.rows((baseline if arm=='none' else HERE/f'analysis/{arm}')/'area_timeseries.csv')
        r['omega_windows']={}
        for a,b in protocol['actual_windows']:
            x,y=area[a-1],area[b-1]
            r['omega_windows'][f'{a}_{b}']={'ttt_veh_h':float(y['ttt_veh_h_cumulative'])-float(x['ttt_veh_h_cumulative']),
                'ttd':int(y['ttd_observed_plus_terminal_cumulative'])-int(x['ttd_observed_plus_terminal_cumulative']),
                'loss':sum(int(row['unresolved_inside_disappearances']) for row in area[a:b])}
        r['actual_flows']={}
        for road in model.roads:
            boundary={kind:sum(float(d.boundaries[t,b['id']]['crossings']) for b in d.definitions.values()
                        if b['road']==road and b['kind']==kind for t in range(start+30,end+1,30))
                      for kind in ('source','ramp','offramp')}
            boundary['terminal']=sum(float(d.flows[t,road,20]['terminal_exits_inferred']) for t in range(start+30,end+1,30))
            r['actual_flows'][road]=boundary
        result[arm]=r
    e.save(out/'comparison.json',result)
    print('Same-state response and conditioned diagnostics complete',flush=True)


def fit_response():
    """Small seed13-only fit, with new late seed23 outcomes kept unopened."""
    out=HERE/'response_fit_seed13';out.mkdir(exist_ok=False)
    source=PARENT/'controller_response_4500_v1/model_v4'
    data=e.ObservationData(PARENT/'controller_response_v1/none')
    model=e.load_base_model(data.geometry,source/'config.json')
    base=e.load(source/'selected_parameters.json')['parameters']
    profile=e.load(source/'port_profile.json')
    old_protocol=e.load(PARENT/'response_pairs_v1/protocol.json')
    actual=e.load(PARENT/'response_pairs_v1/component_actual.json')
    observed={'none':data,**{a:e.ObservationData(PARENT/'response_pairs_v1/observations'/a) for a in ('rm_ramp','vsl','both')}}
    windows={}
    for arm in observed:
        seq=old_protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
        def command(t):
            i=min(3,int((t-1650)//150))
            return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in (59,60,61,62)} if seq['vsl'] else {})
        windows[arm]=e.window(data,model,1650,'history_forecast',profile,command)
    candidates=[('incumbent',base)]
    for vf in (.91,1.,1.1):
        for critical in (1.,1.16,1.3):
            p=copy.deepcopy(base);p['by_direction']['FW_E'].update(v_free_multiplier=vf,rho_crit_multiplier=critical)
            if p!=base:candidates.append((f'vf{vf}_critical{critical}',p))
    e.save(out/'protocol.json',{'training_seed':13,'training_start':1650,'horizon':450,
        'arms':list(observed),'candidate_count':len(candidates),
        'fixed':'Other dynamics, capacity rules, physical ports, commands, source and destination demands',
        'loss':'Mean controlled delta-TTT error squared /0.5vehh squared + delta10490merge error squared /10veh squared; plus NC component relative TTT error squared /5% squared; plus mean FW_E speed RMSE squared /30kmh squared',
        'limits':'rm8 excluded from fitting as a nominally nonbinding/noise control. Previously seen seed13 diagnostic data, not holdout. No late seed23 outcome used.'})
    records=[]
    for name,p in candidates:
        estimates={};speeds=[];invalid=False
        for arm,w in windows.items():
            pred=e.simulate(model,w,p)
            scores={r:e.score_rollout(observed[arm],1650,pred,r) for r in model.roads}
            invalid|=any(s['invalid'] for s in scores.values())
            estimates[arm]=e.component(data,model,1650,pred)
            speeds.append((scores['FW_E']['speed']['rmse']/30)**2)
        delta_loss=statistics.mean(
            (((estimates[a]['component_ttt_veh_h']-estimates['none']['component_ttt_veh_h'])
              -(actual[a]['component_ttt_veh_h']-actual['none']['component_ttt_veh_h']))/.5)**2
            +(((estimates[a]['merges']['RM_C10490']-estimates['none']['merges']['RM_C10490'])
               -(actual[a]['merges']['RM_C10490']-actual['none']['merges']['RM_C10490']))/10)**2
            for a in ('rm_ramp','vsl','both'))
        baseline_loss=((estimates['none']['component_ttt_veh_h']/actual['none']['component_ttt_veh_h']-1)/.05)**2
        loss=delta_loss+baseline_loss+statistics.mean(speeds)
        records.append({'name':name,'parameters':p,'loss':loss,'invalid':invalid,
                        'delta_loss':delta_loss,'baseline_loss':baseline_loss,'speed_loss':statistics.mean(speeds),'estimates':estimates})
        print(name,loss,invalid,flush=True)
    valid=[r for r in records if not r['invalid']]
    if not valid:raise ValueError('No physically valid response-fit candidate')
    chosen=min(valid,key=lambda r:r['loss'])
    e.save(out/'fit.json',records)
    e.save(out/'selected_parameters.json',{'parameters':chosen['parameters'],'name':chosen['name'],
        'adoption':'Experimental response fit; pending late seed23 validation'})
    e.save(out/'config.json',e.load(source/'config.json'))
    e.save(out/'port_profile.json',profile)
    # Freeze this candidate's late-state forecasts without reading native outcomes.
    protocol=e.load(HERE/'protocol.json')
    late=e.ObservationData(Path(protocol['baseline_observations']))
    forecast={}
    for arm,seq in {'none':{'green':[],'vsl':[]},**protocol['candidate_bank']}.items():
        def command(t):
            i=min(len(protocol['command_times'])-1,int((t-protocol['start_s'])//150))
            return ({protocol['meter_id']:seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
        w=e.window(late,model,protocol['start_s'],'history_forecast',profile,command)
        pred=e.simulate(model,w,chosen['parameters'])
        forecast[arm]=e.component(late,model,protocol['start_s'],pred)
        e.save(out/f'late_prediction_{arm}.json',pred)
    e.save(out/'late_forecasts.json',forecast)
    print('Response-fit candidate frozen:',chosen['name'],flush=True)



if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--predict',action='store_true');parser.add_argument('--analyze',action='store_true');parser.add_argument('--fit-response',action='store_true')
    args=parser.parse_args()
    if args.predict:predict()
    if args.analyze:analyze()
    if args.fit_response:fit_response()
