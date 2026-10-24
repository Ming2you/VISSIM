"""Check the physical interior merge location; no autonomous prediction."""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
PINS={}


def read(p):
    PINS[str(p)]=h.sha(p)
    return h.read(p)


def main():
    assert read(HERE/'status.json')['status']=='complete_cached_diagnostic'
    assert not (HERE/'spatial_result.json').exists()
    protocol=read(HERE/'protocol.json')
    geometry_path=h.I/'heldout67_freeway_20260930/observations/release/geometry.json'
    geometry=read(geometry_path)
    merge={str(x['connector']):x for x in geometry['boundaries'] if x['kind']=='ramp' and x['road']=='FW_E'}
    bounds=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    s,e=bounds[23:25];xmerge=merge['10484']['chain_pos_m'];fraction=(xmerge-s)/(e-s)
    assert s<xmerge<e and merge['10484']['to_cell']==23
    h.save(HERE/'spatial_protocol.json',dict(question='Does merging64% through physical23 account for its measured Nv/L-to-boundary mismatch, and does current upstream-part density alter22 overbraking?',
        geometry=dict(cell23_start_m=s,cell23_end_m=e,merge10484_chain_m=xmerge,merge_fraction=fraction),
        method='Endpoint chain-coordinate moment identity, then one no-fit local5x1s cell22 reaction using observed23 upstream-of-merge density. Future endpoints are accounting labels only.',
        interpretation='No added alpha*r operational flow. Interior source position and position-moment change must both be represented by any autonomous model. Endpoint longitudinal distance is not native continuous total travel distance.',
        budget=dict(conditional_variants=1,fits=0,traffic_rollouts=0,new_native=0,new_FZP=0),
        limits='A different spatial pressure sample also changes its averaging support. Conditional reaction improvement cannot establish conservation or RM/VSL gain.',
        input_sha256=PINS,source_sha256=h.sha(__file__)))
    events=read(h.F/'merge_speed_audit/events.json');window_rows=read(HERE/'windows.json')
    native_terms=read(h.R/'recovery_terms137/rows.json.gz')
    cells22={round(x['time_s'],6):[] for x in native_terms if x['case']=='s67_late' and x['arm']=='release' and x['cell']==22 and 'model' in x}
    for x in native_terms:
        if x['case']=='s67_late' and x['arm']=='release' and x['cell']==22 and 'model' in x:cells22[round(x['time_s'],6)].append(x)
    prior=read(h.R/'temporal_response138/rows.json');old={(round(x['time_s'],6),x['lane']):x for x in prior if x['case']=='s67_late' and x['model']=='frozen132'}
    l22=bounds[23]-bounds[22];moment=[];reaction=[];max_moment=0.;max_operator=0.
    for arm in ('release','release_vsl90'):
        cache=read(h.F/'flow67'/f'{arm}_frames.json.gz');frames={round(float(t),6):d for t,d in cache['frames'].items()};times=sorted(frames)
        emap={(round(z['hi'],6),str(z['vehicle'])):z for z in events if z['arm']==arm and z['road']=='FW_E'}
        clip=lambda x:max(s,min(e,x))
        for lo,hi in zip(times,times[1:]):
            a,b=frames[lo],frames[hi];common=a.keys()&b.keys()
            distance=sum(clip(b[v][2])-clip(a[v][2]) for v in common)
            injected_moment=0.;merges=0
            for v in b.keys()-a.keys():
                event=emap.get((hi,v))
                if event is None:continue
                injection=merge[str(event['connector'])]['chain_pos_m']
                distance+=clip(b[v][2])-clip(injection)
                if event['cell']==23:injected_moment+=(injection-s)/(e-s);merges+=1
            m0=sum((z[2]-s)/(e-s) for z in a.values() if z[0]==23)
            m1=sum((z[2]-s)/(e-s) for z in b.values() if z[0]==23)
            departures=sum(a[v][0]<=23<b[v][0] for v in common)
            departures+=sum(emap[hi,v]['cell']<=23<b[v][0] for v in b.keys()-a.keys() if (hi,v) in emap)
            reconstructed=distance/(e-s)+injected_moment-(m1-m0)
            error=abs(reconstructed-departures);max_moment=max(max_moment,error);assert error<1e-8
            moment.append(dict(arm=arm,lo=lo,hi=hi,departures=departures,merges=merges,
                endpoint_longitudinal_movement=distance/(e-s),merge_position_moment=injected_moment,stock_position_change=m1-m0))
            if arm=='release':
                for row in cells22.get(lo,[]):
                    m=row['model'];lane=row['lane'];head=[z for z in a.values() if z[0]==23 and z[3]==lane and z[2]<xmerge]
                    tail=[z for z in a.values() if z[0]==23 and z[3]==lane and z[2]>=xmerge]
                    face_rho=len(head)*1000/(xmerge-s)
                    reaction.append(dict(time_s=lo,lane=lane,original=row,current_front_rho=face_rho,
                        front_n=len(head),back_n=len(tail),front_v=sum(z[1] for z in head)/len(head) if head else None,
                        back_v=sum(z[1] for z in tail)/len(tail) if tail else None))
    # Canonical actual coefficients; use no assumed kappa or nu branch.
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    context,_,_=common.setup();manifest=h.R/'lane_state132/eval_01/manifest.json';read(manifest)
    cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E']);net=cfg.network
    p=net.freeway_segment_params['FW_E'][22];spec=cell_state_response(net,'FW_E',22)
    assert abs(p['segment_length_km']*1000-l22)<1e-8
    for r in reaction:
        row=r.pop('original');m=row['model'];series={}
        for label,down in [('whole',m['downstream_rho']),('front',r['current_front_rho'])]:
            v=row['v0'];trajectory=[v]
            for _ in range(5):
                tau,nu=state_response_coefficients(spec,v,m['desired'],m['rho'],down,p['rho_crit'],p['metanet_tau_h'],m['nu'])
                pressure=-nu*(down-m['rho'])/(tau*3600*p['segment_length_km']*(m['rho']+p['metanet_kappa_veh_km_lane']))
                v=max(net.v_min,v+(m['desired']-v)/(tau*3600)+v*(m['upstream_speed']-v)/(p['segment_length_km']*3600)+pressure)
                trajectory.append(v)
            series[label]=trajectory
        error=max(abs(a-b) for a,b in zip(series['whole'],old[r['time_s'],r['lane']]['trajectory']));max_operator=max(max_operator,error);assert error<1e-8
        r.update(rho=m['rho'],whole_downstream_rho=m['downstream_rho'],observed_rate=row['observed_rate'],
            whole_rate=(series['whole'][-1]-row['v0'])/5,front_rate=(series['front'][-1]-row['v0'])/5)
    summaries=[]
    for arm in ('release','release_vsl90'):
        for lo,hi in [(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)]:
            rr=[x for x in moment if x['arm']==arm and lo-1e-6<=x['lo']<hi-1e-6]
            report=dict(arm=arm,lo=lo,hi=hi,**{k:sum(x[k] for x in rr) for k in ('departures','merges','endpoint_longitudinal_movement','merge_position_moment','stock_position_change')})
            original=next(x['native'] for x in window_rows if x['arm']==arm and x['model']=='frozen144' and x['cell']==23 and x['lo']==lo and x['hi']==hi)
            assert report['departures']==original['outgoing'] and report['merges']==original['merge']
            report['measured_Nv_request']=original['measured_request_start'];summaries.append(report)
    rate_summary=[]
    for label,rr in [('all',reaction),('first30_lane1',[r for r in reaction if r['lane']==1 and r['time_s']<2700.1-1e-6])]:
        rate_summary.append(dict(scope=label,samples=len(rr),mean={k:sum(x[k] for x in rr)/len(rr) for k in ('observed_rate','whole_rate','front_rate')},
            rmse={k:math.sqrt(sum((x[k]-x['observed_rate'])**2 for x in rr)/len(rr)) for k in ('whole_rate','front_rate')}))
    for path,digest in {**PINS,**protocol['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    h.save(HERE/'spatial_result.json',dict(geometry=dict(start_m=s,end_m=e,merge_m=xmerge,merge_fraction=fraction),
        moment_windows=summaries,reaction_summary=rate_summary,moment_max_error=max_moment,operator138_max_error=max_operator,
        input_sha256=PINS,new_rollouts=0,new_fits=0,new_native=0,new_FZP=0))
    h.save(HERE/'spatial_moments.json',moment);h.save(HERE/'front_reaction.json',reaction)
    print('GEOMETRY',fraction,'moment checks',len(moment),'error',max_moment)
    for x in summaries:print('MOMENT',x)
    for x in rate_summary:print('REACTION',x)


if __name__=='__main__':main()
