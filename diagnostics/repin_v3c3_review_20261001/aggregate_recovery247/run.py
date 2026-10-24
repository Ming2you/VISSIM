"""Current expanded036 aggregate versus observed lane force diagnostic.

No new dynamics, coefficient fit, autonomous rollout or native/FZP read.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import csv
import inspect
import math
from pathlib import Path
import time
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve earlier attempt'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()  # Existing canonical imports and BelowNormal process priority.
    from evaluation.controllers import lane_plant_runtime as lpr, area_freeway_accounting as accounting
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients, literature_desired_speed
    from src.models.state import ControlAction
    manifest=h.R/'retained10638/candidate_manifest.json'
    context=lpr.load_sources(manifest)
    model=context['component'];cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E'])
    net=cfg.network;mn=accounting._mn
    assert model.lane_groups_enabled is False
    assert all(abs(x-3)<1e-8 for x in net.freeway_segment_lanes['FW_E'][20:27])
    command=ControlAction(vsl={'FW_E':110})
    protected={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(h.R/'cell21_spatial246/flux_selection/protocol.json')['STOP']
    cases=[('s67_late',a,h.R/f'blocking176/{a}_frames.json.gz',h.I/f'heldout67_freeway_20260930/observations/{a}') for a in ('hold','release')]
    record=next(x for x in h.read(h.C/'data_catalog.json')['checked_records'] if x['case']=='s29_late' and x['arm']=='hold')
    cases.append(('s29_late','hold',h.F/'vsl_native_exposure/s29_late_hold_frames.json.gz',Path(record['truth'])))
    paths=[Path(__file__),manifest,context['paths']['reference_config'],context['paths']['parameters']]
    for _,_,frames,truth in cases:paths.extend([frames,truth/'port_events.csv'])
    pins={str(p):h.sha(p) for p in paths}
    h.save(HERE/'protocol.json',dict(
        previous_goal_turn='PROGRESS246: completed spatial and one coefficient exit-speed information fit, not adopted.',
        question='Do the reported21--25 lane recovery biases transfer to the actual expanded036 aggregate freeway law? Separate instantaneous acceleration, population turnover, and nonlinear averaging.',
        model_manifest=str(manifest),source='Same reference_config/parameters as active frozen233/235 SDMPC; aggregate roads, not experimental148 lane region.',
        scope='29hold110,67hold110/release110 at2670.1, ninety5s windows each, physical21--25. Known states, no blind claim.',
        command='110 only to avoid replacing observed VSL exposure history with nominal90; no VSL-gain assertion from this diagnostic.',
        clock='One-second canonical speed function at each observed state; native instantaneous acceleration and5s mean change are distinct targets.',
        merge='Observed next5s accepted10490/10484 departures divided by5. CONDITIONAL diagnostic only, never an autonomous input.',
        lane_comparison='Same expanded036 coefficients applied to each currently observed lane as an information counterfactual; this is not a deployed lane model. Lane1 receives observed merge amount.',
        limitations=['Material rate excludes classical convection but is not an exact cell average of microscopic acceleration; covariance/pressure and boundary selection remain.',
                     'All force diagnostics precede coupled receiving/off-ramp speed caps and stock evolution. They cannot qualify450s flow/TTT or fullOmega.',
                     'Instantaneous acceleration is current native acceleration; 5s mean change includes population turnover and lateral movement.',
                     'No minmod/moment candidate rerun: recovery_transport already tested these.134/137 and merge_population ledgers reused as prior evidence.'],
        budget=dict(fits=0,forecasts=0,native=0,FZP=0),protected_sha256=protected,STOP=stop,input_pins=pins))
    (HERE/'canonical_speed_function.py.txt').write_text(inspect.getsource(mn.metanet_speed_update_kmh),encoding='utf-8')
    started=time.perf_counter();rows=[];force_checks=0;maximum=0.;identity_error=0.
    params={i:dict(parameters=net.freeway_segment_params['FW_E'][i],response=cell_state_response(net,'FW_E',i)) for i in range(21,26)}
    h.save(HERE/'parameters.json',params)

    def terms(cell,stock,upstock,downstock,lanes,merges):
        nonlocal force_checks,maximum
        if not stock or not upstock:
            return None
        p=net.freeway_segment_params['FW_E'][cell]
        pd=net.freeway_segment_params['FW_E'][cell+1]
        length=p['segment_length_km'];rho=len(stock)/(length*lanes)
        downstream=len(downstock)/(pd['segment_length_km']*lanes)
        speed=math.fsum(x['v'] for x in stock)/len(stock)
        upstream=math.fsum(x['v'] for x in upstock)/len(upstock)
        # Use the exact call order that arms the physical cell parameter hook.
        shown=mn.segment_vsl(command,'FW_E',cell,cfg)
        active=shown < max(cfg.freeway_follower.vsl_set)-.5
        assert not active
        desired=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,shown,net.alpha_vsl,active,net.metanet_a_m,
            getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
        desired=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),cfg,'FW_E',cell,rho,desired,shown,active)
        nu0=mn.select_anticipation_nu(rho,net,shown)
        ctx=mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX']
        assert ctx['armed'] and not (ctx.get('phi',0) and ctx.get('dlam',0))
        spec=cell_state_response(net,'FW_E',cell)
        tau,nu=state_response_coefficients(spec,speed,desired,rho,downstream,ctx.get('response_rho_crit',ctx['rho_crit_link']),p['metanet_tau_h'],nu0)
        relaxation=(desired-speed)/(tau*3600.)
        convection=speed*(upstream-speed)/(length*3600.)
        anticipation=-nu*(downstream-rho)/(tau*length*3600.*(rho+p['metanet_kappa_veh_km_lane']))
        canonical=mn.metanet_speed_update_kmh(speed,upstream,rho,downstream,desired,1/3600.,length,net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
        error=abs(canonical-max(net.v_min,speed+relaxation+convection+anticipation))
        maximum=max(maximum,error);force_checks+=1;assert error<1e-8
        delta=spec.get('delta_merge',net.metanet_delta_merge)
        loss=delta*(merges/5.)*speed/(length*lanes*(rho+p['metanet_kappa_veh_km_lane']))
        return dict(n=len(stock),rho=rho,downstream_rho=downstream,v=speed,upstream_v=upstream,desired=desired,
            critical=p['rho_crit'],tau_sec=tau*3600,nu=nu,relaxation=relaxation,convection=convection,
            anticipation=anticipation,merge_loss=loss,material_unclipped=relaxation+anticipation-loss,
            eulerian_unclipped=relaxation+convection+anticipation-loss,
            canonical_rate_after_merge=max(net.v_min,canonical-loss)-speed,
            rho_over_critical=rho>p['rho_crit'],downstream_ge_local=downstream>=rho,acceleration=desired>=speed)

    for case,arm,path,truth in cases:
        data=h.read(path);ix={k:i for i,k in enumerate(data['fields'])}
        vi=ix.get('speed',ix.get('speed_kmh'));ai=ix.get('accel',ix.get('acceleration_mps2'))
        frames={}
        for timekey,raw in data['frames'].items():
            pairs=raw.items() if isinstance(raw,dict) else ((str(int(v[ix['vehicle']])),v) for v in raw)
            frames[round(float(timekey),1)]={str(vid):dict(cell=z[ix['cell']],lane=z[ix['lane']],v=z[vi],accel=z[ai]) for vid,z in pairs}
        with (truth/'port_events.csv').open(encoding='utf-8-sig',newline='') as f:
            events=list(csv.DictReader(f))
        for step in range(90):
            t=round(2670.1+step*5,1);later=round(t+5,1);before=frames[t];after=frames[later]
            for cell in range(21,26):
                old={v:z for v,z in before.items() if z['cell']==cell};new={v:z for v,z in after.items() if z['cell']==cell}
                assert old and new
                mean0=math.fsum(z['v'] for z in old.values())/len(old);mean1=math.fsum(z['v'] for z in new.values())/len(new)
                stay=old.keys()&new.keys();enter=new.keys()-old.keys();leave=old.keys()-new.keys()
                stay_part=math.fsum(new[v]['v']-old[v]['v'] for v in stay)/(5*len(new))
                enter_part=math.fsum(new[v]['v']-mean0 for v in enter)/(5*len(new))
                leave_part=-math.fsum(old[v]['v']-mean0 for v in leave)/(5*len(new))
                observed=(mean1-mean0)/5
                residual=observed-stay_part-enter_part-leave_part
                identity_error=max(identity_error,abs(residual));assert abs(residual)<1e-10
                connector={21:'10490',23:'10484'}.get(cell)
                merges=sum(e['connector']==connector and e['kind']=='departure' and t+1e-7<float(e['time_s'])<=later+1e-7 for e in events) if connector else 0
                adjacent={i:[z for z in before.values() if z['cell']==i] for i in (cell-1,cell,cell+1)}
                aggregate=terms(cell,adjacent[cell],adjacent[cell-1],adjacent[cell+1],3.,merges)
                lanes=[]
                for lane in (1,2,3):
                    groups={i:[z for z in adjacent[i] if z['lane']==lane] for i in adjacent}
                    result=terms(cell,groups[cell],groups[cell-1],groups[cell+1],1.,merges if lane==1 else 0)
                    lanes.append(dict(lane=lane,terms=result))
                assert aggregate is not None
                valid=all(x['terms'] is not None for x in lanes)
                lane_mean=None
                if valid:
                    lane_mean={name:math.fsum(x['terms']['n']*x['terms'][name] for x in lanes)/len(old) for name in (
                        'relaxation','convection','anticipation','merge_loss','material_unclipped','eulerian_unclipped','canonical_rate_after_merge')}
                rows.append(dict(case=case,arm=arm,time_s=t,block=step//30,cell=cell,n0=len(old),n1=len(new),
                    observed_mean_rate=observed,current_mean_acceleration=math.fsum(z['accel']*3.6 for z in old.values())/len(old),
                    stayer_contribution=stay_part,enter_contribution=enter_part,leave_contribution=leave_part,
                    merges5=merges,aggregate=aggregate,lanes=lanes,lane_mean=lane_mean))
    groups=[]
    for case,arm,_,_ in cases:
        for cell in range(21,26):
            for block in (None,0,1,2):
                rr=[r for r in rows if r['case']==case and r['arm']==arm and r['cell']==cell and (block is None or r['block']==block)]
                valid=[r for r in rr if r['lane_mean'] is not None]
                mean=lambda key:math.fsum(r[key] for r in rr)/len(rr)
                obskeys=('observed_mean_rate','current_mean_acceleration','stayer_contribution','enter_contribution','leave_contribution')
                forcekeys=('relaxation','convection','anticipation','merge_loss','material_unclipped','eulerian_unclipped','canonical_rate_after_merge')
                groups.append(dict(case=case,arm=arm,cell=cell,block=block,samples=len(rr),valid_lane_samples=len(valid),
                    **{k:mean(k) for k in obskeys},aggregate={k:math.fsum(r['aggregate'][k] for r in rr)/len(rr) for k in forcekeys},
                    lane_mean={k:math.fsum(r['lane_mean'][k] for r in valid)/len(valid) for k in forcekeys} if valid else None,
                    matched_aggregate={k:math.fsum(r['aggregate'][k] for r in valid)/len(valid) for k in forcekeys} if valid else None,
                    opposite_anticipation_lane_samples=sum(any(x['terms'] is not None and x['terms']['downstream_ge_local']!=r['aggregate']['downstream_ge_local'] for x in r['lanes']) for r in rr)))
    h.save(HERE/'rows.json',rows);h.save(HERE/'groups.json',groups)
    assert all(h.sha(p)==v for p,v in {**pins,**protected,stop['path']:stop['sha256']}.items())
    completion=dict(status='COMPLETE_CONDITIONAL_NOT_ADOPTED',rows=len(rows),force_checks=force_checks,
                    max_force_reconstruction_error=maximum,max_population_identity_error=identity_error,
                    seconds=time.perf_counter()-started,forecasts=0,fits=0,native=0,FZP=0,protected_unchanged=True)
    h.save(HERE/'completion.json',completion);print(completion)
    for g in groups:
        if g['case']=='s67_late' and g['arm']=='release' and g['block'] is None:print(g)


if __name__=='__main__':main()
