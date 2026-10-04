"""One frozen joint pressure candidate, existing predictor and finite gate."""
import copy
import gzip
import itertools
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
B=HERE.parent
I=B.parent
ROOT=I.parents[2]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    p=HERE/name
    if p.exists():
        assert read(p)==json.loads(json.dumps(value,allow_nan=False)), 'Preserve differing existing result: '+str(p)
        return
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers import freeway_fd as fd
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from src.models import state as st
    terms_path=B/'observed_state_pressure/summary.json'
    terms=read(terms_path)
    sample=[r for r in terms['rows'] if r['basis']=='native' and 17<=r['cell']<=20]
    def matrix(seed):
        rr=[r for r in sample if r['seed']==seed]
        assert len(rr)==56
        x=np.array([[r['anticipation'] if r['downstream_rho']>=r['rho'] else 0,
                     r['anticipation'] if r['downstream_rho']<r['rho'] else 0,-r['lane_drop_raw']] for r in rr])
        y=np.array([r['next5_native_mean_trend_kmh_per_s']-r['relaxation']-r['convection']-r['post_equation_change'] for r in rr])
        assert max(abs(r['equation_increment_kmh']-(r['relaxation']+r['convection']+r['anticipation']-r['lane_drop_raw']+r['post_equation_change'])) for r in rr)<1e-10
        return x,y
    x,y=matrix(29);best=None
    for choice in itertools.product(('free',0.,2.),repeat=3):
        free=[k for k,v in enumerate(choice) if v=='free']
        c=np.array([0. if v=='free' else v for v in choice])
        if free:c[free]=np.linalg.lstsq(x[:,free],y-x@c,rcond=None)[0]
        if np.any(c<0) or np.any(c>2):continue
        loss=float(np.mean((x@c-y)**2))
        if best is None or loss<best[0]:best=loss,c
    scales=best[1]
    scores={}
    for seed in (29,43):
        xx,yy=matrix(seed)
        scores[seed]=dict(before_rmse=float(np.sqrt(np.mean((xx@np.ones(3)-yy)**2))),after_rmse=float(np.sqrt(np.mean((xx@scales-yy)**2))))
    save('frozen_fit.json',dict(scales=scales.tolist(),native_state_trend=scores,training_seed=29,
        rank=int(np.linalg.matrix_rank(x)),labels_pin={str(terms_path):sha(terms_path)},
        forecast_validation=False,fit_scope='14 observed native NC states percell, next5s cell-mean trend, NOT vehicle acceleration.'))
    base_manifest=I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    manifest=read(base_manifest)
    cfg=read(ROOT/manifest['sources']['reference_config']['path'])
    before=copy.deepcopy(cfg)
    context=lpr.load_sources(base_manifest)
    model=context['component'];net=model._config('FW_E',context['parameters']['by_direction']['FW_E']).network
    existing=copy.deepcopy(net.freeway_state_response)
    for cell in range(17,21):
        response=copy.deepcopy(fd.cell_state_response(net,'FW_E',cell))
        response.pop('cell_overrides',None)
        nu=response.get('anticipation',dict(downstream_ge_local=net.metanet_nu_km2_h,downstream_lt_local=net.metanet_nu_km2_h))
        cfg['freeway']['state_response']['FW_E']['cell_overrides'][str(cell)]={**response,
            'anticipation':dict(downstream_ge_local=float(nu['downstream_ge_local']*scales[0]),downstream_lt_local=float(nu['downstream_lt_local']*scales[1])),
            'lane_drop_phi':float(net.freeway_lane_drop_phi*scales[2])}
    save('reference_config.json',cfg)
    manifest['sources']['reference_config']=dict(path=(HERE/'reference_config.json').relative_to(ROOT).as_posix(),sha256=sha(HERE/'reference_config.json'))
    manifest['qualification']='Single local pressure calibration, not gain qualified or production adopted.'
    save('manifest.json',manifest)
    candidate=lpr.load_sources(HERE/'manifest.json')
    n=candidate['component']._config('FW_E',candidate['parameters']['by_direction']['FW_E']).network
    checks={}
    adapter._FW_SEG_CTX_STATE['profile']=None
    physical_cfg=candidate['component']._config('FW_E',candidate['parameters']['by_direction']['FW_E'])
    for cell in range(31):
        st.segment_vsl(st.ControlAction(vsl={'FW_E':110.}),'FW_E',cell,physical_cfg)
        expected=float(net.freeway_lane_drop_phi*scales[2]) if 17<=cell<=20 else net.freeway_lane_drop_phi
        assert adapter._FW_SEG_CTX['phi']==expected
        assert n.freeway_segment_params['FW_E'][cell]==net.freeway_segment_params['FW_E'][cell]
        local=lambda network:{k:v for k,v in fd.cell_state_response(network,'FW_E',cell).items() if k!='cell_overrides'}
        if not 17<=cell<=20:
            assert local(n)==local(net)
        checks[cell]=dict(phi=adapter._FW_SEG_CTX['phi'],state_response=local(n))
    for invalid in (-1.,True,float('nan'),float('inf')):
        test=SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E']),simulation=SimpleNamespace(T_f_h=1/3600))
        try:fd.configure_state_response(test,{'freeway':{'state_response':{'FW_E':{'lane_drop_phi':invalid}}}})
        except ValueError:pass
        else:raise AssertionError('Invalid local phi accepted')
    # Zero is physically admissible and must override rather than fall back.
    z=copy.deepcopy(physical_cfg);z.network.freeway_state_response['FW_E']['cell_overrides']['18']['lane_drop_phi']=0.
    st.segment_vsl(st.ControlAction(vsl={'FW_E':110.}),'FW_E',18,z)
    assert adapter._FW_SEG_CTX['phi']==0. and adapter._FW_SEG_CTX['dlam']==0.
    save('binding_checks.json',dict(cells=checks,invalid_values_rejected=4,zero_override_applied=True,non_target_fd_response_unchanged=True))
    source=B/'component2220_s29_inputs_v2'
    rec=next(r for r in read(source/'capture.json')['records'] if r['arm']=='none')
    args,kwargs=replay.read_primitive_capture(source/rec['input'],rec['sha256'])
    default=model.rollout(*args,**kwargs)
    saved=json.loads(gzip.decompress((B/'component2220_s29_current_v2/none_prediction.json.gz').read_bytes()))
    serialized=json.loads(json.dumps(default,allow_nan=False))
    exact={k:serialized[k]==saved[k] for k in ('cells','flows','ports','ramps')}
    save('default_regression.json',dict(exact=exact,new_default_rollouts=1))
    assert all(exact.values()),exact
    replay.predict(manifest_path=HERE/'manifest.json',output=HERE/'training',input_dir=source)
    def assess(summary):
        rr=summary['results'];base=next(r for r in rr if r['arm']=='none');score=0.
        for r in rr:
            if r['arm']=='none':continue
            predicted=r['predicted_component_ttt']-base['predicted_component_ttt']
            actual=r['actual_component_ttt']-base['actual_component_ttt']
            pexit=sum(r['flows']['predicted'][k]-base['flows']['predicted'][k] for k in ('off_departures','terminal_exits'))
            aexit=sum(r['flows']['actual'][k]-base['flows']['actual'][k] for k in ('off_departures','terminal_exits_inferred'))
            pm=sum(r['predicted_merge'].values())-sum(base['predicted_merge'].values())
            am=sum(r['actual_merge'].values())-sum(base['actual_merge'].values())
            score+=((predicted-actual)/.5)**2+((pexit-aexit)/50)**2+((pm-am)/50)**2
        return dict(response=score/3,stock_rmse=sum(r['score']['cell_n']['rmse'] for r in rr)/4,
                    flow_rmse=sum(r['score']['flow_vph']['rmse'] for r in rr)/4,
                    maximum_mass=max(r['conservation_max'] for r in rr))
    prior=assess(read(B/'component2220_s29_current_v2/summary.json'))
    after=assess(read(HERE/'training/summary.json'))
    passed=after['response']<=.8*prior['response'] and after['stock_rmse']<=1.1*prior['stock_rmse'] and after['flow_rmse']<=1.1*prior['flow_rmse']
    decision=dict(training_passed=passed,before=prior,after=after,
        response_improvement=1-after['response']/prior['response'],new_candidate_rollouts=4,new_default_rollouts=1,
        production_adopted=False,gain_qualified=False,new_native=0)
    save('training_decision.json',decision)
    print(json.dumps(decision),flush=True)
    if passed:
        replay.predict(manifest_path=HERE/'manifest.json',output=HERE/'check43',input_dir=B/'component2220_s43_inputs_v2')
        replay.predict(manifest_path=HERE/'manifest.json',output=HERE/'check29_late',input_dir=I/'congested_replay')
    # Keep executed sources for reproducing the experimental configuration.
    before_sources=read(HERE/'before_sources.json')
    executed={}
    for name,old in before_sources.items():
        target=HERE/'executed_sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes());executed[name]=sha(ROOT/name)
    save('executed_sources.json',executed)
    if not passed:
        for name,old in before_sources.items():
            saved_source=HERE/'before_sources'/name
            assert sha(saved_source)==old
            assert sha(ROOT/name)==executed[name], 'Concurrent source edit; do not overwrite'
            (ROOT/name).write_bytes(saved_source.read_bytes())
            assert sha(ROOT/name)==old
        save('source_restoration.json',dict(exact=before_sources,reason='Training response gate failed; no further candidates or checks.'))


if __name__=='__main__':main()
