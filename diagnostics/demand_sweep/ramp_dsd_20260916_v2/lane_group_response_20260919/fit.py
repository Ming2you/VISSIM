"""Bounded recalibration after changing state resolution; no native gain fitting."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.run import HERE
import copy
import statistics
import time
import argparse


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=MODEL/'config.json')
    parser.add_argument('--output',type=Path,default=HERE/'calibration_v1')
    parser.add_argument('--initial-parameters',type=Path,default=MODEL/'selected_parameters.json')
    parser.add_argument('--ramp-origin',type=Path)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=False)
    config=e.load(args.config);config['freeway']['physical_mainline_lane_groups']=True
    e.save(out/'config.json',config)
    original=e.load(args.initial_parameters)['parameters'];profile=e.load(MODEL/'port_profile.json')
    cases=[]
    for seed,folder,_,_ in CASES:
        if seed==33:continue
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,out/'config.json')
        lane=e.load(HERE/f'observations_v1/s{seed}.json')
        origins=e.load(args.ramp_origin/f's{seed}.json')['counts'] if args.ramp_origin else None
        for t in [900,1650,2400,3600]:
            w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
            if origins is not None:w['lane_group_dynamics']['FW_E']['initial_ramp_origin']=origins[str(t)]
            cases.append((seed,data,model,t,w))
    axes={'rho_crit_multiplier':[1.,1.2,1.4], 'delta_merge':[0.,.5,1.],
          'nu_km2_h':[12.,35.,70.], 'tau_sec':[12.,24.,40.], 'v_free_multiplier':[.91,1.,1.09]}
    e.save(out/'protocol.json',{'training':'Seed13/23 NC450s forecasts at900,1650,2400,3600; seed33 excluded',
        'criterion':'Mean existing density/speed/flow state score, no control cost differences used',
        'axes':axes,'passes':1,'capacity_drop_bonus':False,'new_lane_parameters_fitted':False,
        'reason':'Aggregate-density calibration need not transfer to lane densities; check state calibration before gain validation'})
    cache={};trace=[];begun=time.perf_counter()
    def evaluate(p):
        key=tuple(sorted(p['by_direction']['FW_E'].items()))
        if key in cache:return cache[key]
        scores=[]
        for seed,data,model,t,w in cases:
            pred=e.simulate(model,w,p);score=e.score_rollout(data,t,pred,'FW_E')
            if score['invalid']:raise ArithmeticError(score)
            scores.append({'seed':seed,'cutoff':t,'objective':score['objective']})
        result={'parameters':copy.deepcopy(p),'loss':statistics.mean(x['objective'] for x in scores),'scores':scores}
        cache[key]=result;trace.append(result)
        e.save(out/f'candidate_{len(trace):02}.json',result)
        return result
    best=evaluate(original)
    for name,values in axes.items():
        candidates=[best]
        for value in values:
            p=copy.deepcopy(best['parameters']);p['by_direction']['FW_E'][name]=value
            candidates.append(evaluate(p))
        best=min(candidates,key=lambda x:x['loss'])
        print('CALIBRATION',name,'loss',round(best['loss'],5),'evaluations',len(trace),flush=True)
    e.save(out/'selected_parameters.json',{'parameters':best['parameters'],'status':'NC-calibrated lane-group candidate; gain validation pending'})
    e.save(out/'results.json',{'baseline':trace[0],'selected':best,'candidates':len(trace),'elapsed_sec':time.perf_counter()-begun})


if __name__=='__main__':main()
