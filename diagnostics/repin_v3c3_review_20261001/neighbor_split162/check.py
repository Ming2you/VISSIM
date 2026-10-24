"""Separate cell21 upstream-speed and downstream-density errors using160 inputs."""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists()
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    from src.models.state import ControlAction
    protected=h.read(h.R/'local_transition160/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS:160 reaction diagnosis and161 scalar20 fit/autonomous falsification completed.',
        scope='Reuse160 cell21lane1 seed67 release110 current states,2700.1..3120.1;148/158 coefficients.',
        experiment='Four combinations of native vs saved predicted20 upstream speed and22 downstream density. Own observed21N/v and conditioned5smerge identical;five canonical1s velocity-only updates.',
        budget=dict(new_full_rollouts=0,new_fits=0,new_native=0,new_FZP=0,max_probes=672),
        prior_checked=['160 same-time native/predicted neighbor local ODE','138/139 rejected22-only speed reduction',
                       '133 accepted-momentum transport failed','Claude P_PLANT and101 conditional downstream states','161 scalar20 fit failed'],
        limits='Frozen-density velocity-only probe,not vehicle-conserving traffic or causal attribution. Observed5smerge is future conditioning for diagnosis only. Native mean changes include population turnover. No operational future inputs or adoption.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))
    original=read(h.R/'local_transition160/rows.json')
    original=[r for r in original if r['cell']==21]
    by={(r['model'],round(r['time_s'],6),r['environment']):r for r in original}
    context,_,_=common.setup();mn=area._mn;control=ControlAction(vsl={'FW_E':110})
    speedctx=mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX'];statectx=mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX_STATE']
    saved_speed,saved_state=copy.deepcopy(speedctx),copy.deepcopy(statectx)
    rows=[];max_error=0.;parity_error=0.;calls=0
    try:
        statectx['profile']=None
        for model,manifest in [('148',h.R/'lane_state132/eval_01/manifest.json'),('158',h.R/'coupled_recovery153/candidate/manifest.json')]:
            read(manifest);cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
            net=cfg.network;p=net.freeway_segment_params['FW_E'][21];spec=cell_state_response(net,'FW_E',21)
            for native in [r for r in original if r['model']==model and r['environment']=='native_neighbors']:
                t=round(native['time_s'],6);predicted=by[model,t,'predicted_neighbors']
                assert native['v0']==predicted['v0'] and native['rho']==predicted['rho']
                for mask in range(4):
                    up=(native if mask&1 else predicted)['upstream_speed']
                    down=(native if mask&2 else predicted)['downstream_rho']
                    rho=native['rho'];target=native['terms'][0]['base_target'];merge=native['observed_merge_per_sec']
                    trajectory=[native['v0']];terms=[]
                    for _ in range(5):
                        v=trajectory[-1];command=mn.segment_vsl(control,'FW_E',21,cfg)
                        nu0=mn.select_anticipation_nu(rho,net,command)
                        tau,nu=state_response_coefficients(spec,v,target,rho,down,p['rho_crit'],p['metanet_tau_h'],nu0)
                        relaxation=(target-v)/(tau*3600)
                        convection=v*(up-v)/(p['segment_length_km']*3600)
                        anticipation=-nu*(down-rho)/(tau*p['segment_length_km']*3600*(rho+p['metanet_kappa_veh_km_lane']))
                        raw=v+relaxation+convection+anticipation
                        velocity=mn.metanet_speed_update_kmh(v,up,rho,down,target,1/3600,p['segment_length_km'],p['metanet_tau_h'],nu0,p['metanet_kappa_veh_km_lane'],net.v_min)
                        err=abs(velocity-max(net.v_min,raw));max_error=max(max_error,err);assert err<1e-8;calls+=1
                        merge_loss=spec.get('delta_merge',net.metanet_delta_merge)*merge*v/(p['segment_length_km']*(rho+p['metanet_kappa_veh_km_lane']))
                        final=max(net.v_min,velocity-merge_loss)
                        terms.append(dict(relaxation=relaxation,convection=convection,anticipation=anticipation,merge_loss=-merge_loss,
                            floor=final-raw+merge_loss))
                        assert abs(sum(terms[-1].values())-(final-v))<1e-8
                        trajectory.append(final)
                    if mask in (0,3):
                        expected=predicted if mask==0 else native
                        err=max(abs(a-b) for a,b in zip(trajectory,expected['trajectory']))
                        parity_error=max(parity_error,err);assert err<1e-8
                    rows.append(dict(model=model,time_s=t,mask=mask,native_upstream=bool(mask&1),native_downstream=bool(mask&2),
                        n=native['n'],rho=rho,upstream_speed=up,downstream_rho=down,downstream_ge=down>=rho,
                        v0=native['v0'],actual_final=native['v1'],predicted_final=trajectory[-1],trajectory=trajectory,terms=terms,
                        observed_rate=native['observed_rate'],predicted_rate=(trajectory[-1]-native['v0'])/5))
    finally:
        speedctx.clear();speedctx.update(saved_speed);statectx.clear();statectx.update(saved_state)
    summaries=[]
    for model in ('148','158'):
        for lo,hi in ((2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            for mask in range(4):
                z=[r for r in rows if r['model']==model and r['mask']==mask and lo-1e-6<=r['time_s']<hi-1e-6]
                assert z
                summaries.append(dict(model=model,lo=lo,hi=hi,mask=mask,samples=len(z),
                    observed_rate=sum(r['observed_rate'] for r in z)/len(z),predicted_rate=sum(r['predicted_rate'] for r in z)/len(z),
                    endpoint_rmse=math.sqrt(sum((r['predicted_final']-r['actual_final'])**2 for r in z)/len(z)),
                    downstream_ge=sum(r['downstream_ge'] for r in z),
                    mean_terms={k:sum(t[k] for r in z for t in r['terms'])/(5*len(z)) for k in z[0]['terms'][0]}))
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    assert len(rows)<=672 and calls==len(rows)*5
    h.save(HERE/'rows.json',rows);h.save(HERE/'summary.json',summaries)
    h.save(HERE/'verification.json',dict(probes=len(rows),canonical_calls=calls,max_term_error=max_error,
        parity160_error=parity_error,input_sha256=pins,core=True,STOP=True,hooks_restored=True))
    h.save(HERE/'status.json',dict(status='complete_conditional_only',new_rollouts=0,new_fits=0,native=0,FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    for r in summaries:
        if abs(r['lo']-2820.1)<1e-6:print(r)


if __name__=='__main__':main()
