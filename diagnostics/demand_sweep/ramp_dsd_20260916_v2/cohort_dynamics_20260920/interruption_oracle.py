"""Diagnostic future lane-entry loss, with optional future desired-speed mean.

No deployment path. Tests whether this response law can explain benefit even
when lane-changing exposure is known. Stocks and traffic speeds stay predicted.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
from src.models import metanet as mn
from contextlib import contextmanager
from collections import Counter
import csv

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'


def moments(seed,arm):
    return {(r['time_s'],r['cell'],r['lane']):r for r in e.load(HERE/f'moments_v1/s{seed}_{arm}.json')['rows']}


def shocks(seed,arm):
    with (HERE/f'lateral_v1/s{seed}_{arm}_shock.csv').open(encoding='utf-8',newline='') as stream:
        return {(int(r['time_s']),int(r['cell']),int(r['lane'])):float(r['closing_speed_sum_kmh']) for r in csv.DictReader(stream)}


@contextmanager
def oracle(seed,arm,gamma,use_mean):
    old_advance=PhysicalLaneGroups.advance;old_update=mn.metanet_speed_update_kmh;old_desired=mn.effective_desired_speed_kmh
    reference=moments(seed,'none');treatment=moments(seed,arm);shock=shocks(seed,arm)
    context={};audit=[]
    def lanes(plant,c,g):
        if len(plant.widths[c])==1:return list(range(1,int(sum(plant.widths[c]))+1))
        return [g+1] if g<2 else list(range(3,int(sum(plant.widths[c]))+1))
    def mean(data,t,c,ls):
        while t>=900:
            values=[data[t,c,str(l)] for l in ls if (t,c,str(l)) in data]
            if values:return sum(r['n']*r['desired_mean'] for r in values)/sum(r['n'] for r in values)
            t-=10
        raise ValueError('No prior desired-speed group support')
    def advance(plant,state,*args,**kwargs):
        assert not context and plant.road=='FW_E'
        context.update(plant=plant,t=int(state.time_sec),index=0,
            order=[(c,g) for c,ws in enumerate(plant.widths) for g in range(len(ws))])
        try:
            result=old_advance(plant,state,*args,**kwargs)
            assert context['index']==len(context['order'])
            return result
        finally:context.clear()
    def desired(*args,**kwargs):
        if not context or not use_mean:return old_desired(*args,**kwargs)
        plant=context['plant'];c,g=context['order'][context['index']];t=context['t'];ls=lanes(plant,c,g)
        factor=mean(treatment,t,c,ls)/mean(reference,t,c,ls)
        values=list(args);values[5]=False
        return old_desired(*values)*factor
    def update(*args,**kwargs):
        value=old_update(*args,**kwargs)
        if not context:return value
        plant=context['plant'];c,g=context['order'][context['index']];t=context['t'];ls=lanes(plant,c,g)
        shock_mass=sum(shock.get((t,c,l),0.) for l in ls)
        loss=gamma*shock_mass/plant.n[c][g] if plant.n[c][g]>0 else 0.
        value=max(args[-1],value-loss)
        audit.append({'t':t,'cell':c,'group':g,'predicted_n':plant.n[c][g],
                      'observed_closing_speed_mass':shock_mass,'loss_kmh':loss})
        context['index']+=1
        return value
    PhysicalLaneGroups.advance=advance;mn.metanet_speed_update_kmh=update;mn.effective_desired_speed_kmh=desired
    try:yield audit
    finally:
        PhysicalLaneGroups.advance=old_advance;mn.metanet_speed_update_kmh=old_update;mn.effective_desired_speed_kmh=old_desired


def main():
    out=HERE/'interruption_oracle_v1';out.mkdir(exist_ok=False)
    params=e.load(LANE/'qualification_v6/parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    gamma=e.load(HERE/'interruption_fit_v1/fit.json')['gamma'];results={}
    for seed,arms in [(23,['none','vsl']),(33,['none','spread_only'])]:
        _,folder,bank,start=next(r for r in CASES if r[0]==seed)
        data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        model=e.load_base_model(data.geometry,LANE/'qualification_v6/config.json')
        results[seed]={}
        for use_mean in [False,True]:
            mode='loss_and_mean' if use_mean else 'loss_only';parts_by={}
            for arm in arms:
                command=(lambda _: ({},{d:100 for d in range(51,59)})) if arm=='vsl' else (lambda _: ({},{}))
                w=e.window(data,model,start,'history_forecast',profile,command)
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
                with oracle(seed,arm,gamma,use_mean) as audit:pred=e.simulate(model,w,params)
                assert not e.score_rollout(data,start,pred,'FW_E')['invalid']
                p=parts(pred);p['total']=sum(p.values());parts_by[arm]=p
                e.save(out/f'prediction_s{seed}_{mode}_{arm}.json',pred)
                e.save(out/f'audit_s{seed}_{mode}_{arm}.json',audit)
            delta={a:{k:v-parts_by['none'][k] for k,v in p.items()} for a,p in parts_by.items() if a!='none'}
            results[seed][mode]={'parts':parts_by,'delta':delta}
            print(seed,mode,delta,flush=True)
    e.save(out/'results.json',{'status':'DIAGNOSTIC_ONLY_FUTURE_EXPOSURE',
        'gamma':gamma,'results':results,'interpretation':'Measured lane-entry follower exposure; optionally actual desired-speed means. No causal prediction claim. FD may already embody average interruption; absolute-state effects must be requalified if developed.'})


if __name__=='__main__':main()
