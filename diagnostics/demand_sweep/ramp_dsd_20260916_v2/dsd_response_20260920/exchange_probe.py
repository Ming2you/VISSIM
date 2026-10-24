"""Oracle isolation: can observed lane exchange alone explain the VSL gain?

Future exchange observations are diagnostic inputs, never an online prediction
or a fitted/adopted controller. All demand, actuator and cost settings stay fixed.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import group
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from collections import defaultdict
import copy
import json
import argparse

HERE=Path(__file__).resolve().parent
LANE=H/'lane_group_response_20260919'


def extract(path,observer,widths,start):
    exposure=defaultdict(float);exchanges=defaultdict(float);previous={}
    with path.open('rb') as f:
        for line in f:
            if not line[:1].isdigit():continue
            p=line.rstrip(b'\r\n;').split(b';');t=int(float(p[0]))
            if t<start:continue
            if t>start+450:break
            vid=int(p[1]);link=int(p[2]);lane=int(p[3])
            loc=observer.locate((link,lane,float(p[4]),float(p[6])))
            if not loc or loc[0]!='FW_E':continue
            c=loc[1];g=group(c,lane);old=previous.get(vid)
            if t>start:
                exposure[c,g]+=1
                if old and old[0]==t-1 and old[1:3]==(link,c) and old[3]!=g:
                    exchanges[c,old[3],g]+=1
            previous[vid]=(t,link,c,g)
    rates=[[[exchanges[c,g,k]/exposure[c,g] if exposure[c,g] else 0.
             for k in range(len(ws))] for g in range(len(ws))] for c,ws in enumerate(widths)]
    return {'exchange_rates_per_sec':rates,
            'exposure_vehicle_seconds':[[exposure[c,g] for g in range(len(ws))] for c,ws in enumerate(widths)],
            'exchanges':[[[exchanges[c,g,k] for k in range(len(ws))] for g in range(len(ws))] for c,ws in enumerate(widths)]}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--reuse-extraction',type=Path)
    parser.add_argument('--seed',type=int,choices=[13,23,33],default=23)
    parser.add_argument('--arm',choices=['vsl','rm_ramp','both'],default='vsl')
    args=parser.parse_args()
    out=HERE/args.output;out.mkdir(exist_ok=False)
    seed,folder,bank,start=next(c for c in CASES if c[0]==args.seed)
    data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
    spec={**lane['geometry'],**lane['cutoffs'][str(start)]}
    observer=Observer(data.geometry)
    none_runs={13:H/'rules_4500_v1/run_none',23:H/'rules_4500_s23_v1/run_none',
               33:H/'state_response_20260919/native_s33_v1/run_none'}
    target=args.arm
    paths={'none':none_runs[seed]/'vissim_eval/baseline_001.fzp',
           target:(HERE/'native_v2/run_retry1' if seed==23 and target=='vsl' else bank/('run_'+target))/'vissim_eval/baseline_001.fzp'}
    future=e.load(args.reuse_extraction) if args.reuse_extraction else {}
    for arm,path in paths.items():
        if arm not in future:future[arm]=extract(path,observer,spec['widths'],start)
    future={arm:future[arm] for arm in paths}
    e.save(out/'future_exchange_observations.json',future)
    params=e.load(LANE/'qualification_v6/parameters.json')['parameters']
    profile=e.load(MODEL/'port_profile.json');protocol=e.load(bank/'protocol.json')
    model=e.load_base_model(data.geometry,LANE/'qualification_v6/config.json')
    results={}
    for arm,source in [('none','history'),(target,'history'),('none','future_none'),
                       (target,'future_none'),(target,'future_'+target)]:
        seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
        def command(t):
            i=int((t-start)//150)
            return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
        w=e.window(data,model,start,'history_forecast',profile,command)
        active=copy.deepcopy(spec)
        if source!='history':active['exchange_rates_per_sec']=future[source.removeprefix('future_')]['exchange_rates_per_sec']
        w['lane_group_dynamics']={'FW_E':active}
        prediction=json.loads(json.dumps(e.simulate(model,w,params)))
        if source=='history':
            assert prediction==e.load(LANE/f'qualification_v6/prediction_{seed}_{arm}.json'),'Historical baseline changed'
        name=f'{arm}_{source}';e.save(out/(name+'.json'),prediction)
        results[name]=parts(prediction);results[name]['total']=sum(results[name].values())
        print(name,results[name],flush=True)
    actual=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')[str(seed)]['delta_1s'][target]['FW_E']
    comparisons={}
    for label,a,b in [('history','none_history',target+'_history'),
                      ('future_same_exchange','none_future_none',target+'_future_none'),
                      ('future_arm_exchange','none_future_none',target+'_future_'+target)]:
        comparisons[label]={k:results[b][k]-results[a][k] for k in results[a]}
    e.save(out/'summary.json',{'seed':seed,'start_s':start,'arm':target,'results':results,'deltas':comparisons,'actual':actual,
        'qualification':'DIAGNOSTIC_ONLY_FUTURE_INPUTS','parameters_fitted':0,
        'warning':'Measured future450s average exchange hazards. They do not identify a causal hazard model or certify VSL gain.',
        'history_predictions_exact':True,'native_runs_started':0})
    print('DELTAS',comparisons,'ACTUAL',actual,flush=True)


if __name__=='__main__':main()
