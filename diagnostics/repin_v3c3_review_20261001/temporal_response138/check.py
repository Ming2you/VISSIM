"""Cell22 local5s reaction diagnostic; no physical traffic rollout or fitting."""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'status.json').exists(), 'No automatic retry'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    from src.models.state import ControlAction
    context,_,_=common.setup();mn=area._mn
    protected=h.read(h.R/'recovery_terms137/forecast/protocol.json')
    source=h.R/'recovery_terms137/rows.json.gz';rows=h.read(source)
    rows=[x for x in rows if x['cell']==22 and 'model' in x]
    assert {x['arm'] for x in rows}=={'hold','release'}
    pins={str(source):h.sha(source),str(Path(__file__)):h.sha(__file__)}
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS:135/136 completed and137 fitted cell22 candidate failed autonomous gain; revalidated terminal status.',
        purpose='Check whether excessive cell22 anticipation in current native states disappears when the canonical1s speed equation is advanced5times.',
        scope='22 only, nominal110,67release and29hold; current rho/upstream speed/downstream rho fixed across each5s local reaction probe.',
        exclusions='No vehicle flow/storage update, no mainline/ramp/city rollout, no fitting, no future states/merge flows used as inputs. Following native mean is scoring only.',
        limits='Frozen current environment is a conditional local ODE diagnostic, not a5s full conservation forecast. It cannot identify all effects of changing populations or time-varying neighbors.',
        models=['frozen132','unadopted137'],new_forecasts=0,new_native=0,new_FZP=0,
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],pins=pins))
    h.save(HERE/'status.json',dict(status='running'))
    results=[];term_error=0.;checks=0
    for label,manifest in [('frozen132',h.R/'lane_state132/eval_01/manifest.json'),('unadopted137',h.R/'recovery_terms137/candidate/manifest.json')]:
        pins[str(manifest)]=h.sha(manifest)
        cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E']);net=cfg.network
        p=net.freeway_segment_params['FW_E'][22];spec=cell_state_response(net,'FW_E',22)
        control=ControlAction(vsl={'FW_E':110})
        for r in rows:
            m=r['model'];v=r['v0'];rho=m['rho'];down=m['downstream_rho'];up=m['upstream_speed'];trajectory=[v]
            for j in range(5):
                command=mn.segment_vsl(control,'FW_E',22,cfg)
                desired=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,command,net.alpha_vsl,False,net.metanet_a_m,False,net.rho_max,0.)
                nu0=mn.select_anticipation_nu(rho,net,command)
                tau,nu=state_response_coefficients(spec,v,desired,rho,down,p['rho_crit'],p['metanet_tau_h'],nu0)
                relaxation=(desired-v)/(tau*3600)
                convection=v*(up-v)/(p['segment_length_km']*3600)
                anticipation=-nu*(down-rho)/(tau*p['segment_length_km']*3600*(rho+p['metanet_kappa_veh_km_lane']))
                result=mn.metanet_speed_update_kmh(v,up,rho,down,desired,1/3600,p['segment_length_km'],p['metanet_tau_h'],nu0,p['metanet_kappa_veh_km_lane'],net.v_min)
                error=abs(result-max(net.v_min,v+relaxation+convection+anticipation));term_error=max(term_error,error);assert error<1e-8
                if label=='frozen132' and j==0:assert abs(result-v-m['pre_exit_rate'])<1e-8
                v=result;trajectory.append(v);checks+=1
            observed=r['v1'];key='congested' if rho>p['rho_crit'] else 'below_critical'
            results.append(dict(model=label,case=r['case'],arm=r['arm'],time_s=r['time_s'],lane=r['lane'],rho=rho,downstream_rho=down,
                regime=key,downstream_ge=down>=rho,initial_speed=r['v0'],observed_final=observed,observed_rate=r['observed_rate'],
                observed_acceleration=r['instantaneous_mean_acceleration'],one_second_rate=trajectory[1]-trajectory[0],
                five_second_rate=(v-r['v0'])/5,trajectory=trajectory))
    summaries=[]
    for label in ('frozen132','unadopted137'):
        for case in sorted({r['case'] for r in results}):
            for lane in ('all',1,2,3):
                for end in (30,150,450):
                    for regime in ('all','below_critical','congested'):
                        rr=[x for x in results if x['model']==label and x['case']==case and (lane=='all' or x['lane']==lane)
                            and x['time_s']<2670.1+end-1e-6 and (regime=='all' or x['regime']==regime)]
                        if not rr:continue
                        summaries.append(dict(model=label,case=case,lane=lane,seconds=end,regime=regime,samples=len(rr),
                            mean={k:sum(x[k] for x in rr)/len(rr) for k in ('observed_rate','observed_acceleration','one_second_rate','five_second_rate')},
                            five_second_endpoint_rmse=math.sqrt(sum((x['trajectory'][-1]-x['observed_final'])**2 for x in rr)/len(rr))))
    for p,digest in {**protected['protected_sha256'],**pins}.items():assert h.sha(p)==digest,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'rows.json',results);h.save(HERE/'summary.json',summaries)
    h.save(HERE/'verification.json',dict(canonical_speed_updates=checks,term_max_error=term_error,first1s_matches137=True,pins=pins,core=True,STOP=True))
    h.save(HERE/'status.json',dict(status='complete_conditional_only',fit=0,new_forecasts=0,new_native=0,new_FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    for x in summaries:
        if x['lane']==1 and x['seconds'] in (30,150) and x['regime']=='all':print(x)


if __name__=='__main__':main()
