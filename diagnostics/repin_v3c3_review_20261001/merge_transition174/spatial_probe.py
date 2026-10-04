"""Bounded local ODE screen of the actual10639 interior coordinate.

Native current state is reset for each probe. Counts/neighbor states stay frozen:
these are conditional speed diagnostics, never conservative traffic forecasts.
"""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'spatial_protocol.json').exists(), 'Preserve prior work'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import literature_desired_speed,state_response_coefficients
    from src.models.state import ControlAction
    protocol=h.read(HERE/'protocol.json');pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    h.save(HERE/'spatial_protocol.json',dict(
        hypothesis='Current spatial variation lost by a single lane mean might explain wrong initial acceleration; inspect before implementing another split.',
        scope='Cell10 lanes1/2, seed67release110, current5s snapshots; same153 speed parameters; no fitted coefficient.',
        comparison='One cell versus two subcells divided at actual10639 merge coordinate. Update only speed5x1s; hold stocks/neighbors and lane membership fixed.',
        merge='Use SAME already predicted173 one-second accepted merges for both probes; place it after split in spatial probe. No future measured merges.',
        lane_drop='Freeze the dynamic lane-reduction coefficient reconstructed from the current173 call; apply at physical downstream boundary only. No interior lane-drop.',
        no_lateral_exchange=True,no_future_native_predictor=True,
        limits='No longitudinal/lateral mass update, position renewal, shared receiving, VSL history forecast, waiting or TTT. Observed next5s mean is only a label and contains population change. This screen cannot qualify physical gain or prove that a conservative split would work/fail.',
        budget=dict(max_probes=360,max_canonical_calls=2700,fits=0,traffic_forecasts=0,native=0,FZP=0),
        screen='Do not proceed solely on initial frame: report all150s blocks and both lanes. >=10% aggregate5s RMSE improvement with no block/lane worse>10% is only a reason to examine conservative implementation, not adoption.'))
    context,_,_=common.setup();manifest=h.R/'coupled_recovery153/candidate/manifest.json';read(manifest)
    cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    net=cfg.network;mn=area._mn;control=ControlAction(vsl={'FW_E':110})
    boundaries=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    merge_x=read(h.R/'merge_target172/protocol.json')['geometry']['10639']['x_m']
    lengths=[(merge_x-boundaries[10])/1000,(boundaries[11]-merge_x)/1000]
    assert min(lengths)>0 and abs(sum(lengths)-net.freeway_segment_params['FW_E'][10]['segment_length_km'])<1e-10
    doc=read(h.F/'flow67/release_frames.json.gz');fields=doc['fields']
    frames={round(float(t),6):[dict(zip(fields,v)) for v in f.values()] for t,f in doc['frames'].items()}
    trace={(round(r['time_s'],6),r['lane']):r for r in read(HERE/'executed_terms.json.gz') if r['arm']=='release' and r['cell']==10}
    speedctx=mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX']
    statectx=mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX_STATE']
    savedctx,savedstate=copy.deepcopy(speedctx),copy.deepcopy(statectx)
    rows=[];skipped=[];calls=0;error=0.
    try:
        statectx['profile']=None
        for t,u in zip(sorted(frames),sorted(frames)[1:]):
            for lane in (1,2):
                own=[r for r in frames[t] if r['cell']==10 and r['lane']==lane]
                final=[r for r in frames[u] if r['cell']==10 and r['lane']==lane]
                up=[r for r in frames[t] if r['cell']==9]
                down=[r for r in frames[t] if r['cell']==11 and r['lane']==lane]
                groups=[[r for r in own if (r['x_m']>=merge_x)==bool(part)] for part in (0,1)]
                if not own or not final or not up or any(not part for part in groups):
                    skipped.append(dict(time_s=t,lane=lane,n=len(own),parts=[len(x) for x in groups]));continue
                initial=sum(r['speed_kmh'] for r in own)/len(own)
                observed=sum(r['speed_kmh'] for r in final)/len(final)
                upstream=sum(r['speed_kmh'] for r in up)/len(up)
                downstream=len(down)/net.freeway_segment_params['FW_E'][11]['segment_length_km']
                recorded=trace[t,lane]
                drop=-recorded['terms']['lane_drop']/(recorded['rho']*recorded['exchange_v']**2) if recorded['rho'] and recorded['exchange_v'] else 0.
                for version in ('whole','split_at_merge'):
                    parts=[own] if version=='whole' else groups
                    ls=[sum(lengths)] if version=='whole' else lengths
                    ns=[len(x) for x in parts]
                    velocities=[sum(r['speed_kmh'] for r in group)/len(group) for group in parts]
                    initial_parts=list(velocities);series=[sum(n*v for n,v in zip(ns,velocities))/sum(ns)]
                    all_terms=[]
                    for j in range(5):
                        old=list(velocities);next_v=[]
                        for part,(n,length,v) in enumerate(zip(ns,ls,old)):
                            edge=part==len(parts)-1
                            rho=n/length;dn=downstream if edge else ns[part+1]/ls[part+1]
                            uv=upstream if part==0 else old[part-1]
                            command=mn.segment_vsl(control,'FW_E',10,cfg,physical_length_km=length,segment_end=edge)
                            target=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,command,net.alpha_vsl,False,net.metanet_a_m,False,net.rho_max,0.)
                            target=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),cfg,'FW_E',10,rho,target,command,False)
                            p=copy.deepcopy(speedctx['p']);sr=copy.deepcopy(speedctx['state_response'])
                            nu0=mn.select_anticipation_nu(rho,net,command)
                            tau,nu=state_response_coefficients(sr,v,target,rho,dn,speedctx['response_rho_crit'],p['metanet_tau_h'],nu0)
                            terms=dict(relaxation=(target-v)/(tau*3600),convection=v*(uv-v)/(length*3600),
                                anticipation=-nu*(dn-rho)/(tau*length*3600*(rho+p['metanet_kappa_veh_km_lane'])))
                            raw=v+sum(terms.values());value=mn.metanet_speed_update_kmh(v,uv,rho,dn,target,1/3600,length,net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
                            error=max(error,abs(value-max(net.v_min,raw)));assert error<1e-8;calls+=1
                            dropped=max(net.v_min,value-drop*sum(lengths)/length*rho*v*v) if edge else value
                            merge=trace[round(t+j,6),lane]['accepted_merge'] if edge else 0.
                            loss=recorded['delta_merge']*merge*v/(length*(rho+net.metanet_kappa_veh_km_lane))
                            velocity=max(net.v_min,dropped-loss)
                            all_terms.append(dict(step=j,part=part,n=n,rho=rho,up=uv,down=dn,v=v,target=target,
                                nu=nu,tau_sec=tau*3600,**terms,lane_drop=dropped-value,merge_loss=-loss,final=velocity))
                            next_v.append(velocity)
                        velocities=next_v;series.append(sum(n*v for n,v in zip(ns,velocities))/sum(ns))
                    rows.append(dict(version=version,time_s=t,lane=lane,n=len(own),part_n=ns,part_lengths_km=ls,
                        part_initial_v=initial_parts,actual_initial=initial,actual_final=observed,trajectory=series,terms=all_terms))
    finally:
        speedctx.clear();speedctx.update(savedctx);statectx.clear();statectx.update(savedstate)
    assert len(rows)<=360 and calls<=2700
    summaries=[]
    for lane in (1,2):
        for lo,hi in ((2670.1,2675.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1),(2670.1,3120.1)):
            for version in ('whole','split_at_merge'):
                z=[r for r in rows if r['lane']==lane and r['version']==version and lo-1e-6<=r['time_s']<hi-1e-6]
                if z:summaries.append(dict(lane=lane,version=version,lo=lo,hi=hi,probes=len(z),
                    rmse5=math.sqrt(sum((r['trajectory'][-1]-r['actual_final'])**2 for r in z)/len(z)),
                    predicted_rate=sum(r['trajectory'][-1]-r['actual_initial'] for r in z)/(5*len(z)),
                    observed_rate=sum(r['actual_final']-r['actual_initial'] for r in z)/(5*len(z)),
                    max_internal_speed=max(x['final'] for r in z for x in r['terms'])))
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    h.save(HERE/'spatial_rows.json',rows);h.save(HERE/'spatial_summary.json',summaries);h.save(HERE/'spatial_skipped.json',skipped)
    h.save(HERE/'spatial_verification.json',dict(probes=len(rows),canonical_calls=calls,manual_error=error,
        lengths_km=lengths,merge_x=merge_x,input_sha256=pins,core=True,STOP=True,context_restored=True,
        status='complete_conditional_only',fit=0,traffic_forecasts=0,production_adopted=False))
    for row in summaries:
        if row['hi']-row['lo']<=5.1 or row['hi']-row['lo']>449:print(row)


if __name__=='__main__':main()
