"""Diagnostic-only FD mean scaling from actual future desired-speed cohorts.

This is deliberately NOT an online predictor. It asks whether the response law
can use even perfect desired-speed mean transport before implementing transport.
No state N/v or measured future physical flow is fed back into the rollout.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,MODEL,H
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from src.models import metanet as mn
from contextlib import contextmanager
import json

HERE=Path(__file__).resolve().parent


@contextmanager
def mean_transport_oracle(reference,treatment,start=2400):
    baseline={(r['time_s'],r['cell']):r for r in reference['rows'] if r['lane']=='all'}
    observed={(r['time_s'],r['cell']):r for r in treatment['rows'] if r['lane']=='all'}
    old_sv,old_desired,old_update=mn.segment_vsl,mn.effective_desired_speed_kmh,mn.metanet_speed_update_kmh
    context={'road':None,'cell':None,'completed_speed_updates':0};audit=[]
    def segment(control,road,cell,cfg):
        context.update(road=road,cell=cell)
        return old_sv(control,road,cell,cfg)
    def desired(*args,**kwargs):
        if context['road']!='FW_E':return old_desired(*args,**kwargs)
        assert not kwargs and len(args)==10
        step=context['completed_speed_updates']//21;sec=start+10*step;cell=context['cell']
        # Empty observed cells have no desired-speed mean. Use the most recent
        # jointly nonempty snapshot at/before this diagnostic step, never a later one.
        t=sec
        while (t,cell) not in baseline or (t,cell) not in observed:
            t-=10
            if t<900:raise ValueError(('No observed desired-speed support',sec,cell))
        factor=observed[t,cell]['desired_mean']/baseline[t,cell]['desired_mean']
        values=list(args);values[5]=False
        base=old_desired(*values)
        value=base*factor
        audit.append({'time_s':sec,'cell':cell,'factor':factor,'desired':value})
        return value
    def update(*args,**kwargs):
        result=old_update(*args,**kwargs)
        if context['road']=='FW_E':context['completed_speed_updates']+=1
        return result
    mn.segment_vsl=segment;mn.effective_desired_speed_kmh=desired;mn.metanet_speed_update_kmh=update
    try:
        yield audit
        assert context['completed_speed_updates']==45*21,context
    finally:
        mn.segment_vsl=old_sv;mn.effective_desired_speed_kmh=old_desired;mn.metanet_speed_update_kmh=old_update


def main():
    out=HERE/'mean_oracle_v1';out.mkdir(exist_ok=False)
    params=e.load(MODEL/'selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    result={}
    for seed,arms in [(23,['none','vsl','mean_only','spread_only','affine_both']),(33,['none','spread_only'])]:
        folder=(H/'controller_response_s23_v1/none' if seed==23 else H/'state_response_20260919/native_s33_v1/observations/none')
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,MODEL/'config.json')
        reference=e.load(HERE/f'moments_v1/s{seed}_none.json');results={}
        w=e.window(data,model,2400,'history_forecast',profile,lambda _: ({},{}))
        baseline=e.simulate(model,w,params)
        for arm in arms:
            treatment=e.load(HERE/f'moments_v1/s{seed}_{arm}.json')
            with mean_transport_oracle(reference,treatment) as audit:
                pred=e.simulate(model,w,params)
            if arm=='none':assert json.loads(json.dumps(pred))==json.loads(json.dumps(baseline)),'Identity diagnostic changes baseline'
            results[arm]=parts(pred);results[arm]['total']=sum(results[arm].values())
            assert not e.score_rollout(data,2400,pred,'FW_E')['invalid']
            e.save(out/f'prediction_s{seed}_{arm}.json',pred)
            e.save(out/f'audit_s{seed}_{arm}.json',audit)
        delta={arm:{k:value-results['none'][k] for k,value in r.items()} for arm,r in results.items() if arm!='none'}
        result[seed]={'parts':results,'delta':delta};print(seed,delta,flush=True)
    e.save(out/'results.json',{'status':'DIAGNOSTIC_ONLY_FUTURE_DESIRED_SPEED_INPUT','results':result,
        'claim':'Not causal prediction, not deployed; fixed existing FD shape times measured treatment/baseline desired-speed mean; N/v/physical flows remain model-generated.'})


if __name__=='__main__':main()
