"""One coefficient-free convection-closure ablation in the existing plant."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
B=HERE.parent
I=B.parent
ROOT=I.parents[2]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    p=HERE/name
    if p.exists():
        assert read(p)==json.loads(json.dumps(value,allow_nan=False))
        return
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def assess(summary):
    rr=summary['results'];base=next(r for r in rr if r['arm']==('none' if any(x['arm']=='none' for x in rr) else 'hold'))
    score=0.;deltas=[]
    for r in rr:
        if r is base:continue
        p=r['predicted_component_ttt']-base['predicted_component_ttt']
        a=r['actual_component_ttt']-base['actual_component_ttt']
        pe=sum(r['flows']['predicted'][k]-base['flows']['predicted'][k] for k in ('off_departures','terminal_exits'))
        ae=sum(r['flows']['actual'][k]-base['flows']['actual'][k] for k in ('off_departures','terminal_exits_inferred'))
        pm=sum(r['predicted_merge'].values())-sum(base['predicted_merge'].values())
        am=sum(r['actual_merge'].values())-sum(base['actual_merge'].values())
        score+=((p-a)/.5)**2+((pe-ae)/50)**2+((pm-am)/50)**2
        deltas.append(dict(arm=r['arm'],predicted=p,actual=a,exit_predicted=pe,exit_actual=ae,merge_predicted=pm,merge_actual=am))
    return dict(response=score/(len(rr)-1),stock_rmse=sum(r['score']['cell_n']['rmse'] for r in rr)/len(rr),
                flow_rmse=sum(r['score']['flow_vph']['rmse'] for r in rr)/len(rr),
                maximum_mass=max(r['conservation_max'] for r in rr),deltas=deltas)


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    original=CanonicalFreewayModel._config
    before=read(HERE/'before_sources.json')
    executed={}
    extra=['diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py',
           'diagnostics/sdmpc_n31_20260924/integration_20260926/replay_congested_component.py']
    for name in list(before)+extra:
        p=HERE/'executed_sources'/Path(name).name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes());executed[name]=sha(ROOT/name)
    save('executed_sources.json',executed)
    manifest=I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    call_counts={}
    try:
        ctx=lpr.load_sources(manifest);model=ctx['component']
        source=B/'component2220_s29_inputs_v2'
        rec=next(r for r in read(source/'capture.json')['records'] if r['arm']=='none')
        args,kwargs=replay.read_primitive_capture(source/rec['input'],rec['sha256'])
        default=model.rollout(*args,**kwargs)
        saved=json.loads(gzip.decompress((B/'component2220_s29_current_v2/none_prediction.json.gz').read_bytes()))
        plain=json.loads(json.dumps(default))
        exact={k:plain[k]==saved[k] for k in ('cells','flows','ports','ramps')}
        save('default_regression.json',dict(exact=exact,new_default450=1))
        assert all(exact.values())
        def configured(self,road,parameters):
            cfg=original(self,road,parameters)
            cfg.network._component_flux_convection=road=='FW_E'
            call_counts[road]=call_counts.get(road,0)+1
            return cfg
        CanonicalFreewayModel._config=configured
        replay.audit_observed_state_pressure(integrate_five=True,variant='flux')
        replay.predict(manifest_path=manifest,output=HERE/'training',input_dir=source)
        prior=assess(read(B/'component2220_s29_current_v2/summary.json'))
        after=assess(read(HERE/'training/summary.json'))
        passed=after['response']<=.8*prior['response'] and after['stock_rmse']<=1.1*prior['stock_rmse'] and after['flow_rmse']<=1.1*prior['flow_rmse']
        decision=dict(training_passed=passed,before=prior,after=after,response_improvement=1-after['response']/prior['response'],
            new_candidate450=4,new_default450=1,new_native=0,new_fit=0,production_adopted=False,gain_qualified=False)
        save('training_decision.json',decision)
        print(json.dumps(decision),flush=True)
        if passed:
            replay.predict(manifest_path=manifest,output=HERE/'check43',input_dir=B/'component2220_s43_inputs_v2')
            replay.predict(manifest_path=manifest,output=HERE/'check29_late',input_dir=I/'congested_replay')
            save('checks.json',dict(check43=assess(read(HERE/'check43/summary.json')),check29_late=assess(read(HERE/'check29_late/summary.json'))))
        save('binding.json',dict(configured=call_counts,scope='all FW_E cells, existing parameters unchanged',runtime_hook='CanonicalFreewayModel._config sets _component_flux_convection only during this ablation'))
    finally:
        CanonicalFreewayModel._config=original
        # Trial source belongs only to this finite experiment. Preserve dirty
        # baseline exactly even on failure; never overwrite concurrent edits.
        for name,pin in before.items():
            p=ROOT/name;old=HERE/'before_sources'/name
            assert sha(p)==executed[name], 'Concurrent edit, do not restore: '+name
            assert sha(old)==pin
            p.write_bytes(old.read_bytes())
            assert sha(p)==pin
        save('source_restoration.json',dict(exact=before,reason='Experimental closure is not qualified for the full plant or SDMPC.'))


if __name__=='__main__':main()
