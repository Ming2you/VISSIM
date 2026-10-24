"""Bounded local screen of Lu et al. (2011) equations 4.8 and 4.10.

Reuses current native states from160. This is neither a traffic rollout nor
autonomous validation. Future5s merge is diagnostic conditioning inherited160.
"""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
URL = 'https://horowitz.me.berkeley.edu/Publications_files/All_papers_numbered/Lu_Metanet_improvement_TC_IEEE_ITSC_2011.pdf'


def convection(mode, v, up, length):
    if mode == 'original':
        return v * (up-v) / (3600*length)
    if mode == 'lu48':
        return v * (math.sqrt(up*v)-v) / (3600*length)
    if mode == 'lu410':
        return up * (math.sqrt((up*up+v*v)/2)-v) / (3600*length)
    raise ValueError(mode)


def main():
    assert not (HERE/'protocol.json').exists()
    protected = h.read(h.R/'local_transition160/protocol.json')
    pins = {str(Path(__file__)):h.sha(__file__),
            str(h.ROOT/'tmp/pdfs/Lu_Metanet_improvement_TC_IEEE_ITSC_2011.pdf'):
                h.sha(h.ROOT/'tmp/pdfs/Lu_Metanet_improvement_TC_IEEE_ITSC_2011.pdf')}
    def read(path):
        pins[str(path)] = h.sha(path)
        return h.read(path)
    h.save(HERE/'protocol.json', dict(
        previous_goal_turn='NO_PROGRESS: explanation-only131/150;162--164 reports finalized this turn.',
        hypothesis='Upstream-speed influence in ordinary convection can be too strong when upstream speed is low; test two published parameter-free closures before any rollout or fit.',
        prior_checked=['133 accepted mass/momentum transport failed on132',
                       '162 upstream-speed plus downstream-density errors',
                       '163 joint pressure erases RM cost;164 restores RM sign but VSL wrong',
                       'Claude P_PLANT upstream boundary warning',
                       'native_distribution_split/attempt2 mean/shape not universal gain'],
        literature=dict(url=URL, page=4, equations=['4.8','4.10'],
                        scope='Convection term only; keep FD/relaxation/pressure/merge/caps. Not full Lu model or Lu field calibration.'),
        budget=dict(frozen_variants=2, baseline_local_probes=652, max_local_probes=1956,
                    max_canonical_calls=9780, fits=0, traffic_rollouts=0, native=0, FZP=0),
        gate='Screen only. Native-neighbor pooled endpoint RMSE must improve >=10% for both148 and158 coefficient sets; no cell/time window with >=10 samples may worsen >10%. Predicted-neighbor cases reported separately. Passing does not establish VSL/RM gain and would only justify one bounded autonomous follow-up.',
        limitations='Only67release110 states, frozen own density and neighbors for5s; includes native future5smerge and population turnover. Not a joint conservative trajectory, causal attribution, independent validation or usable future input.',
        protected_sha256=protected['protected_sha256'], STOP=protected['STOP']))
    h.save(HERE/'status.json', dict(status='running'))
    source = read(h.R/'local_transition160/rows.json')
    exits = {round(r['start'],6):r for r in read(h.R/'exit_sending131/attempt2/steps.json') if r['case']=='release'}
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr, area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients
    from src.models.state import ControlAction
    context, _, _ = common.setup()
    mn = area._mn
    control = ControlAction(vsl={'FW_E':110})
    speedctx = mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX']
    statectx = mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX_STATE']
    saved_speed, saved_state = copy.deepcopy(speedctx), copy.deepcopy(statectx)
    rows=[];calls=0;canonical_error=0.;parity=0.
    # Independent numerical anchors and asymptotes, without model state.
    assert convection('original',36,72,.1) == 3.6
    assert abs(convection('lu48',36,72,.1)-3.6*(math.sqrt(2)-1))<1e-12
    assert abs(convection('lu410',36,72,.1)-7.2*(math.sqrt(2.5)-1))<1e-12
    for mode in ('original','lu48','lu410'):
        assert convection(mode,36,36,.1)==0
    assert convection('lu410',36,0,.1)==0
    try:
        statectx['profile']=None
        for model,manifest in [('148',h.R/'lane_state132/eval_01/manifest.json'),
                               ('158',h.R/'coupled_recovery153/candidate/manifest.json')]:
            read(manifest)
            cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
            net=cfg.network
            for r in [r for r in source if r['model']==model]:
                cell=r['cell'];p=net.freeway_segment_params['FW_E'][cell]
                spec=cell_state_response(net,'FW_E',cell)
                for mode in ('original','lu48','lu410'):
                    v=r['v0'];trajectory=[v];terms=[]
                    for _ in range(5):
                        command=mn.segment_vsl(control,'FW_E',cell,cfg)
                        target=mn.effective_desired_speed_kmh(r['rho'],net.v_free,net.rho_crit,command,net.alpha_vsl,
                            False,net.metanet_a_m,False,net.rho_max,0.)
                        cap=None
                        if cell==20:
                            exit_n=exits[round(r['time_s'],6)]['n0']
                            if exit_n>0:
                                through=(r['n']-exit_n)*v/(p['segment_length_km']*3600)
                                factor=min(1.,max(0.,r['receiving21']-r['observed_merge_per_sec'])/through) if through>1e-12 else 1.
                                if factor<1-1e-9:cap=v*factor
                        if model=='158' and cap is not None:target=min(target,max(net.v_min,cap))
                        nu0=mn.select_anticipation_nu(r['rho'],net,command)
                        tau,nu=state_response_coefficients(spec,v,target,r['rho'],r['downstream_rho'],p['rho_crit'],p['metanet_tau_h'],nu0)
                        relaxation=(target-v)/(tau*3600)
                        pressure=-nu*(r['downstream_rho']-r['rho'])/(tau*p['segment_length_km']*3600*(r['rho']+p['metanet_kappa_veh_km_lane']))
                        original_conv=convection('original',v,r['upstream_speed'],p['segment_length_km'])
                        original_raw=v+relaxation+original_conv+pressure
                        canonical=mn.metanet_speed_update_kmh(v,r['upstream_speed'],r['rho'],r['downstream_rho'],target,
                            1/3600,p['segment_length_km'],p['metanet_tau_h'],nu0,p['metanet_kappa_veh_km_lane'],net.v_min)
                        err=abs(canonical-max(net.v_min,original_raw));canonical_error=max(canonical_error,err)
                        assert err<1e-8;calls+=1
                        conv=convection(mode,v,r['upstream_speed'],p['segment_length_km'])
                        raw=v+relaxation+conv+pressure
                        merge=spec.get('delta_merge',net.metanet_delta_merge)*r['observed_merge_per_sec']*v/(p['segment_length_km']*(r['rho']+p['metanet_kappa_veh_km_lane'])) if cell==21 else 0.
                        new=max(net.v_min,raw)-merge
                        if model=='148' and cap is not None:new=min(new,cap)
                        new=max(net.v_min,new)
                        terms.append(dict(relaxation=relaxation,convection=conv,anticipation=pressure,merge=-merge,
                                          clipping=new-raw+merge))
                        assert abs(sum(terms[-1].values())-(new-v))<1e-8
                        v=new;trajectory.append(v)
                    if mode=='original':
                        err=max(abs(a-b) for a,b in zip(trajectory,r['trajectory']))
                        parity=max(parity,err);assert err<1e-8
                    rows.append(dict(model=model,mode=mode,cell=cell,environment=r['environment'],time_s=r['time_s'],
                        actual=r['v1'],initial=r['v0'],predicted=v,trajectory=trajectory,terms=terms))
    finally:
        speedctx.clear();speedctx.update(saved_speed);statectx.clear();statectx.update(saved_state)
    summary=[]
    windows=[(2700.1,3120.1),(2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]
    for model in ('148','158'):
        for env in ('native_neighbors','predicted_neighbors'):
            for cell in (None,20,21):
                for lo,hi in windows:
                    for mode in ('original','lu48','lu410'):
                        z=[r for r in rows if r['model']==model and r['environment']==env and r['mode']==mode
                           and (cell is None or r['cell']==cell) and lo-1e-6<=r['time_s']<hi-1e-6]
                        summary.append(dict(model=model,environment=env,cell=cell,lo=lo,hi=hi,mode=mode,samples=len(z),
                            rmse=math.sqrt(sum((r['predicted']-r['actual'])**2 for r in z)/len(z)),
                            bias=sum(r['predicted']-r['actual'] for r in z)/len(z)))
    gates={}
    def key(r):return r['model'],r['environment'],r['cell'],r['lo'],r['hi']
    base={key(r):r for r in summary if r['mode']=='original'}
    for mode in ('lu48','lu410'):
        native=[r for r in summary if r['mode']==mode and r['environment']=='native_neighbors']
        pooled=[r for r in native if r['cell'] is None and r['lo']==2700.1 and r['hi']==3120.1]
        gates[mode]=dict(pooled_both_improve10=all(r['rmse']<=.9*base[key(r)]['rmse'] for r in pooled),
                        no_window_worse10=all(r['rmse']<=1.1*base[key(r)]['rmse'] for r in native if r['cell'] is not None and r['samples']>=10))
        gates[mode]['passes_screen']=all(gates[mode].values())
    assert len(rows)==1956 and calls==9780
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'rows.json',rows);h.save(HERE/'summary.json',summary)
    h.save(HERE/'verification.json',dict(probes=len(rows),canonical_calls=calls,canonical_error=canonical_error,
        original160_parity=parity,input_sha256=pins,core=True,STOP=True,hooks_restored=True))
    h.save(HERE/'assessment.json',dict(gates=gates,production_adopted=False,goal_complete=False,traffic_rollouts=0,fits=0,native=0,FZP=0))
    h.save(HERE/'status.json',dict(status='complete_screen_only',goal='ACTIVE_NOT_QUALIFIED'))
    print(gates)
    for r in summary:
        if r['cell'] is None and r['environment']=='native_neighbors' and r['lo']==2700.1 and r['hi']==3120.1:print(r)


if __name__=='__main__':main()
