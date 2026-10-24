"""No-fit conditional equation check before adding any spatial model state.

Only the equilibrium-speed aggregation changes; no future stop mask, fitted
capacity bonus or density multiplier. This uses measured START states at each
step and is explicitly not a450s causal rollout or a calibrated plant.
"""
from pathlib import Path
from collections import defaultdict
import sys, math, hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d


def bank(frames,geometry,cfg,scale):
    cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    shifts={r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    states={}
    for t,frame in frames.items():
        groups=defaultdict(list)
        for row in frame.values():
            x=shifts[row['link']]+row['pos']
            c=next((c for c,r in cells.items() if r['start_m']<=x<r['end_m']),20)
            assert c>=13
            groups[c].append((row,x))
        for c in range(13,21):
            geo=cells[c];vs=groups[c];n=len(vs)
            if not n:continue
            p=cfg.network.freeway_segment_params['FW_E'][c]
            length=geo['length_km'];width=geo['effective_lanes'];rho=n/(length*width)
            fd=lambda density: p['v_free']*math.exp(-((density/p['rho_crit'])**p['metanet_a_m'])/p['metanet_a_m'])
            count=math.ceil(length*1000/scale);step=length/count
            small=defaultdict(list)
            for v,x in vs:
                # Keep canonical final-stock accounting, but distinguish the
                # one-step overshoot from finite spatial-bin crowding.
                k=min(count-1,int((x-geo['start_m'])/(1000*step)))
                small[v['lane'],k].append(v)
            fine=sum(len(v)*fd(len(v)/step) for v in small.values())/n
            lane=defaultdict(list)
            for v,_ in vs:lane[v['lane']].append(v)
            lanes=sum(len(v)*fd(len(v)/length) for v in lane.values())/n
            states[t,c]=dict(n=n,v=sum(v['v'] for v,x in vs)/n,rho=rho,
                             coarse_eq=fd(rho),lane_eq=lanes,space_eq=fine,
                             overshoot=sum(x>=geo['end_m'] for v,x in vs))
    return states


def conditional(states,cfg,lo,hi):
    errors=defaultdict(list);target_rates=[];predicted_rates=defaultdict(list);examples=[]
    for t in range(lo,hi):
        for c in range(15,21):
            r=states[t,c];up=states[t,c-1];down=states[t,c+1] if c<20 else r
            p=cfg.network.freeway_segment_params['FW_E'][c]
            tau=p['metanet_tau_h']*3600;length=p['segment_length_km'];nu=p['metanet_nu_km2_h'];kappa=p['metanet_kappa_veh_km_lane']
            advection=r['v']*(up['v']-r['v'])/(3600*length)
            anticipation=-nu/tau/length*(down['rho']-r['rho'])/(r['rho']+kappa)
            target=states[t+1,c]['v'];obs=target-r['v'];target_rates.append(obs)
            candidates={'persistence':r['v']}
            for name in ('coarse','lane','space'):
                value=r['v']+(r[name+'_eq']-r['v'])/tau+advection+anticipation
                candidates[name]=max(cfg.network.v_min,value)
            for name,v in candidates.items():
                errors[name].append(v-target);predicted_rates[name].append(v-r['v'])
            if t in (2400,2490,2580,2700,2820):
                examples.append(dict(time_s=t,cell=c,current=r,target=target,predicted=candidates,
                                     advection=advection,anticipation=anticipation))
    def metric(values):return dict(n=len(values),rmse=math.sqrt(sum(x*x for x in values)/len(values)),bias=sum(values)/len(values))
    # Require a nontrivial0.5km/h one-step change when reporting sign skill;
    # it is an evaluation threshold, never a plant parameter.
    active=[i for i,v in enumerate(target_rates) if abs(v)>=.5]
    return dict(errors={k:metric(v) for k,v in errors.items()},
                direction={k:dict(n=len(active),correct=sum(v[i]*target_rates[i]>0 for i in active)) for k,v in predicted_rates.items()},
                examples=examples)


def main():
    out=d.HERE/'downstream_fd_resolution_v1';out.mkdir(exist_ok=False)
    geom_path=d.H/'controller_response_s23_v1/none/geometry.json';geom=d.e.load(geom_path)
    config=d.HERE/'transport_step1_exchange_off_v2/config.json'
    params_file=d.HERE/'port_travel_fit_v1/selected_parameters.json'
    model=d.e.load_base_model(geom,config);params=d.e.load(params_file)['parameters']
    cfg=model._config('FW_E',params['by_direction']['FW_E'])
    sources={
        'none':d.HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp',
        'rm_ramp':d.H/'response_late_s23_v1/run_rm_ramp/vissim_eval/baseline_001.fzp',
    }
    results={};receipts={}
    for arm,path in sources.items():
        frames,receipts[arm]=d.extract(path,arm=='none');results[arm]={}
        for scale in (75.,100.,150.):
            states=bank(frames,geom,cfg,scale)
            results[arm][str(scale)]={label:conditional(states,cfg,lo,hi) for label,lo,hi in (
                ('precontrol',2250,2400),('response',2400,2850))}
            print(arm,scale,{k:{m:round(v['rmse'],5) for m,v in s['errors'].items()} for k,s in results[arm][str(scale)].items()},flush=True)
    for scale in results['none']:
        assert results['none'][scale]['precontrol']==results['rm_ramp'][scale]['precontrol']
    paths=[Path(__file__),Path(d.__file__),geom_path,config,params_file]
    d.e.save(out/'result.json',dict(status='CONDITIONAL_EQUATION_DIAGNOSIS_ONLY',results=results,source_receipts=receipts,
        no_fitting=True,future_inputs_to_plant=False,qualified=False,new_native_runs=0,
        equation='Same1s coarse METANET relaxation/convection/anticipation, measured current state; vary only desired-speed spatial aggregation.',
        limitations=['Conditional forecasts reset to measured current state every second; no450s causal performance claim.',
            'Small-bin equilibrium averaging lacks within-bin car-following, lateral momentum and acceleration distribution.',
            'Final native one-step overshoot retains canonical cell accounting; last bin is therefore an approximation.'],
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))


if __name__=='__main__':main()
