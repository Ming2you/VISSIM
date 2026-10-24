"""Finite calibration of the bounded speed equation; no native execution."""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np

HERE=Path(__file__).resolve().parent
B=HERE.parent
I=B.parent
ROOT=I.parents[2]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def properties():
    from evaluation.controllers.freeway_fd import bounded_virtual_density as virtual
    rng=np.random.default_rng(290929);largest=0.
    for j in range(400):
        r,d=rng.uniform(0,180,2);v=rng.uniform(0,150);cap=float(rng.choice([0,1800,3600]))
        q=rng.uniform(0,cap);loss=float(rng.choice([0,1]));lanes=3
        spec=dict(eta_ge=.6,eta_lt=.3,kappa=20.,merge=.4,lane_drop=.7)
        z=virtual(r,d,180,v,120,q,cap,loss,lanes,spec)
        assert 0<=z<=180+1e-9
        eta=.6 if d>=r else .3
        base=r+eta*20/(r+20)*(d-r)
        weights=[]
        if cap:weights.append(.4*20/(r+20)*q/cap)
        if loss:weights.append(.7*loss/lanes*r/180)
        expected=base+(sum(weights)/len(weights) if weights else 0)*min(v/120,1)*(180-base)
        assert abs(expected-z)<1e-10
        largest=max(largest,abs(expected-z))
        # Accepted merge amount monotonically increases virtual density within
        # the same geometrical feature, never changes the physical stock.
        hi=virtual(r,d,180,v,120,cap,cap,loss,lanes,spec)
        assert hi>=z-1e-10
    assert virtual(50,50,180,100,120,0,0,0,3,spec)==50
    zero=dict(spec,eta_ge=0,eta_lt=0,merge=0,lane_drop=0)
    assert virtual(50,100,180,130,120,800,1800,1,3,zero)==50
    for q,cap in [(1,0),(1801,1800),(-1,1800)]:
        try:virtual(30,40,180,80,120,q,cap,0,3,spec)
        except ValueError:pass
        else:raise AssertionError('Invalid accepted merge allowed')
    save('equation_checks.json',dict(random_convexity_and_eq14_17_checks=400,max_algebra_error=largest,
        zero_effect_identity=True,invalid_merge_rejected=3,not_full_AD_validation=True))


def main():
    from scipy.optimize import least_squares
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    assert not (HERE/'status.json').exists(), 'Do not restart a started calibration'
    before=read(HERE/'before_sources.json');executed={}
    for name in before:
        p=HERE/'executed_sources'/Path(name).name;p.parent.mkdir(exist_ok=True);p.write_bytes((ROOT/name).read_bytes());executed[name]=sha(ROOT/name)
    save('executed_sources.json',executed)
    original=CanonicalFreewayModel._config
    started=time.perf_counter();active=[None];evaluations=[];best=[None,None];cache={}
    protocol=read(HERE/'protocol.json')
    variables=protocol['variables'];lo=np.array([v['lower'] for v in variables]);hi=np.array([v['upper'] for v in variables])
    initial=np.array([v['initial'] for v in variables]);z0=(initial-lo)/(hi-lo)
    try:
        properties()
        loss_protocol=read(B/'cellwise_calibration/protocol.json')
        for name,pin in loss_protocol['truth_file_pins'].items():assert sha(Path(name))==pin,name
        catalog=read(B/'cellwise_calibration/data_catalog.json')['checked_records']
        train=[r for r in catalog if r['role']=='train'];check=[r for r in catalog if r['case']=='s43_early']
        assert len(train)==8 and len(check)==4
        records=train+check;payloads={};observations={}
        ctx=lpr.load_sources(I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json');model=ctx['component']
        for r in records:
            key=r['case'],r['arm'];payloads[key]=replay.read_primitive_capture(r['input'],r['sha256'])
            assert payloads[key][0][2]==ctx['parameters']
            observations[key]=ObservationData(r['truth'])
        # Current normal path must still reproduce both initial states.
        exact={}
        for case,arm in [('s29_early','none'),('s29_late','hold')]:
            pred=model.rollout(*copy.deepcopy(payloads[case,arm][0]),**copy.deepcopy(payloads[case,arm][1]))
            prior=read_gzip(Path(loss_protocol['baseline_prediction_folders'][case])/(arm+'_prediction.json.gz'))
            plain=json.loads(json.dumps(pred));exact[case]={k:plain[k]==prior[k] for k in ('cells','flows','ports','ramps')}
            assert all(exact[case].values())
        save('default_regression.json',dict(exact=exact,new_default450=2))
        def configured(self,road,parameters):
            cfg=original(self,road,parameters)
            if active[0] is not None and road=='FW_E':
                cfg.network._component_bounded_response=dict(active[0])
                for row in cfg.network.freeway_segment_params[road]:
                    row['rho_crit']*=active[0]['rho_scale'];row['metanet_a_m']*=active[0]['shape_scale']
                    assert row['rho_crit']<cfg.network.rho_max and row['metanet_a_m']>1
            return cfg
        CanonicalFreewayModel._config=configured
        old_rows=read(B/'cellwise_calibration/state/eval_000/result.json')['rows']
        prior_loss=replay._cellwise_losses(old_rows,[0.]*9,loss_protocol)
        save('prior_loss.json',prior_loss)
        def evaluate(z):
            key=tuple(np.asarray(z,dtype=float))
            if key in cache:return cache[key]
            assert len(evaluations)<50, 'Finite evaluation budget exhausted'
            vals=lo+np.asarray(z)*(hi-lo);active[0]={r['name']:float(v) for r,v in zip(variables,vals)}
            rows=[];predictions={};wall=time.perf_counter();error=None
            for rec in train:
                case=rec['case'],rec['arm'];args,kwargs=copy.deepcopy(payloads[case])
                try:
                    pred=model.rollout(*args,**kwargs)
                    rows.append(replay._cellwise_measure(model,pred,rec,observations[case]));predictions[case]=pred
                except (ValueError,AssertionError,ArithmeticError) as exc:
                    error=type(exc).__name__+': '+str(exc);break
            rel=np.asarray(z)-z0
            if error:
                item=dict(index=len(evaluations),values=active[0],invalid=error,completed_rollouts=len(rows),rows=rows)
                save(f'eval_{len(evaluations):03d}.json',item);evaluations.append(item)
                if best[0] is None:raise ValueError('Initial bounded candidate invalid: '+error)
                res=np.full_like(best[0]['residual'],1000.)
            else:
                res=replay._cellwise_residuals(train,predictions,observations,rows,rel,loss_protocol)
                loss=replay._cellwise_losses(rows,rel,loss_protocol)
                item=dict(index=len(evaluations),normalized_values=list(map(float,z)),values=active[0],loss=loss,rows=rows,
                    invalid=None,completed_rollouts=8,wall_sec=time.perf_counter()-wall)
                save(f'eval_{len(evaluations):03d}.json',item);evaluations.append(item)
                if best[0] is None or loss['response_objective']<best[0]['loss']['response_objective']:
                    best[0]=dict(item,residual=res);best[1]=predictions
            cache[key]=res
            save('status.json',dict(stage='calibration',evaluations=len(evaluations),completed_rollouts=sum(r['completed_rollouts'] for r in evaluations),
                best_index=None if best[0] is None else best[0]['index'],best_loss=None if best[0] is None else best[0]['loss']['response_objective'],elapsed_sec=time.perf_counter()-started))
            print(json.dumps(dict(evaluation=len(evaluations),invalid=error,best=None if best[0] is None else best[0]['loss']['response_objective'])),flush=True)
            return res
        fit=least_squares(evaluate,z0,bounds=(np.zeros(9),np.ones(9)),diff_step=.03,max_nfev=5,
                          ftol=1e-3,xtol=1e-3,gtol=1e-3,method='trf')
        chosen={k:v for k,v in best[0].items() if k!='residual'}
        active[0]=dict(chosen['values'])
        after=chosen['loss']
        passed=(after['response']<=.8*prior_loss['response'] and after['meaningful_signs_pass']
                and after['mean_n_rmse']<=1.1*prior_loss['mean_n_rmse'] and after['mean_q_rmse']<=1.1*prior_loss['mean_q_rmse'])
        save('selection.json',dict(selected=chosen,training_passed=passed,prior=prior_loss,
            optimizer=dict(success=bool(fit.success),message=str(fit.message),nfev=fit.nfev,njev=fit.njev),
            actual_evaluations=len(evaluations),new_training450=sum(r['completed_rollouts'] for r in evaluations)))
        (HERE/'selected_predictions').mkdir()
        for (case,arm),pred in best[1].items():
            with gzip.open(HERE/'selected_predictions'/f'{case}_{arm}.json.gz','wt',encoding='utf8') as f:json.dump(pred,f,allow_nan=False)
        checks=None
        if passed:
            check_rows=[]
            for rec in check:
                key=rec['case'],rec['arm'];args,kwargs=copy.deepcopy(payloads[key])
                pred=model.rollout(*args,**kwargs);row=replay._cellwise_measure(model,pred,rec,observations[key]);check_rows.append(row)
                with gzip.open(HERE/'selected_predictions'/f'{key[0]}_{key[1]}.json.gz','wt',encoding='utf8') as f:json.dump(pred,f,allow_nan=False)
            checks=dict(rows=check_rows,loss=replay._cellwise_losses(check_rows,np.asarray(chosen['normalized_values'])-z0,loss_protocol))
            save('check43.json',checks)
        save('summary.json',dict(training_passed=passed,check43=checks,selected_values=chosen['values'],selected_loss=after,
            new_candidate450=sum(r['completed_rollouts'] for r in evaluations)+(4 if passed else 0),new_default450=2,
            new_native=0,new_fit=True,production_adopted=False,gain_qualified=False,wall_sec=time.perf_counter()-started))
        save('status.json',dict(stage='complete',training_passed=passed,evaluations=len(evaluations),production_adopted=False))
    finally:
        CanonicalFreewayModel._config=original
        for name,pin in before.items():
            p=ROOT/name;old=HERE/'before_sources'/Path(name).name
            assert sha(p)==executed[name], 'Concurrent source edit; do not overwrite'
            assert sha(old)==pin
            p.write_bytes(old.read_bytes());assert sha(p)==pin
        save('source_restoration.json',dict(exact=before,reason='Candidate comparison only; fullOmega,AD,SDMPC/native qualification still required.'))


def read_gzip(p):
    with gzip.open(p,'rt',encoding='utf8') as f:return json.load(f)


if __name__=='__main__':main()
