"""Bounded lane-drop audit/refit using the existing component and calibrator.

No native run, runtime patch, or duplicate traffic equation. `prepare` freezes
one-parameter fitting; `report` evaluates the frozen fit, including rolling150.
"""
import copy
import gzip
import json
import math
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CAL = ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
B = CAL/'res10_20260922'
OLD = B/'boundary_literature_v1'
sys.path[:0] = [str(CAL), str(ROOT/'.review-deps'), str(ROOT)]
from canonical_harness import load_base_model, sha256, TrafficState, accounting, adapter
from boundary_factory import ObservationData, build_window


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def check_queue():
    queue = load('D:/VISSIM_runs/20260922_fw080_urban090_controls/queue.json')
    assert all(sha256(Path(p)) == h for p,h in queue['code_sha256'].items())
    return queue['code_sha256']


def prepare():
    if (OUT/'protocol.json').exists():
        raise FileExistsError('Preserve frozen protocol')
    queue_pins = check_queue()
    data = ObservationData(B/'fw080_urban090_observations')
    model = load_base_model(data.geometry, OLD/'boundary_config.json')
    params = load(OLD/'family_parameters.json')['boundary']['by_direction']
    audit = {'native_queue_pins':queue_pins, 'drop':vars(model.base.freeway_offramp_capacity_drop),
             'occupancy_definition':'off-connector stock / geometric storage, not detector OccupRate',
             'profile_cases':[], 'observed_offramps':[]}
    for off,geom in model.offramps.items():
        stocks=[float(r['snapshot_n_veh']) for (t,key),r in data.boundaries.items() if key==geom['id']]
        audit['observed_offramps'].append({'connector':off,'road':geom['road'],
            'capacity_veh':geom['storage_capacity_veh'], 'max_n_veh':max(stocks),
            'max_storage_fraction':max(stocks)/geom['storage_capacity_veh']})
    window = build_window(data,2700.1,'history_forecast',model_step_sec=1)
    audit['forecast_occupancy_constant'] = all(
        row['offramp_occupancy_veh']==window['boundary_steps'][0]['offramp_occupancy_veh']
        for row in window['boundary_steps'])
    for road in model.roads:
        cfg = model._config(road,params[road])
        physical = cfg.network.freeway_segment_lanes[road]
        for ratio in (0., .25, .5, .75, 1., 'observed2700.1'):
            state = TrafficState.initial(cfg)
            state.urban_link_storage = dict(cfg.network.urban_link_storage_veh)
            for off,key in cfg.network.off_ramp_storage_link.items():
                cap=cfg.network.urban_link_storage_veh[key]
                n=window['boundary_steps'][0]['offramp_occupancy_veh'][off] if isinstance(ratio,str) else cap*ratio
                state.urban_link_storage[key]=max(0.,cap-n)
            # Demand is not consumed by this stock-based profile function.
            profile, detail = accounting._mn.effective_lane_profile(state,cfg,None)
            assert adapter._FW_SEG_CTX_STATE['profile']==profile
            effective=profile[road]
            losses=[max(0.,a-b) for a,b in zip(physical,effective)]
            dlam=[max(0.,a-b) for a,b in zip(effective,effective[1:])]
            audit['profile_cases'].append(dict(road=road,occupancy=ratio,
                physical=physical,effective=effective,lane_losses=losses,
                positive_dlambda=[{'upstream_cell':i,'delta_lanes':v} for i,v in enumerate(dlam) if v>1e-9]))
        rows=[r for r in audit['profile_cases'] if r['road']==road and not isinstance(r['occupancy'],str)]
        assert all(all(b>=a-1e-10 for a,b in zip(old['lane_losses'],new['lane_losses'])) for old,new in zip(rows,rows[1:]))
        assert max(rows[0]['lane_losses'])<1e-9
        assert abs(max(rows[-1]['lane_losses'])-1.)<1e-9
    save('chain_audit.json',audit)
    protocol=load(OLD/'boundary_fit/protocol.json')
    protocol['baseline_config']=protocol['config']
    protocol['baseline_config_sha256']=protocol['config_sha256']
    protocol['initial_parameters']={r:{**p,'lane_drop_phi':3.} for r,p in params.items()}
    protocol['baseline_parameters']=copy.deepcopy(protocol['initial_parameters'])
    protocol['fit_keys']=['lane_drop_phi']
    protocol['comparison_family']='boundary_lane_drop_only'
    manifest=load(data.folder/'manifest.json')
    protocol['validation'].append(dict(id='fw080_urban090',observations=str(data.folder.relative_to(ROOT)),
        run='D:/VISSIM_runs/20260922_both_off_half/fw080_urban090_nc9000/run',
        network_sha256=manifest['network']['sha256'],cutoffs_s=protocol['training']['cutoffs_s']))
    protocol['limitations'] += ['Only phi refitted within [0,6]; all six earlier direction coefficients and off-ramp lane-loss law fixed.',
        'Forecast off-ramp stock is held at cutoff; conditioned fitting supplies measured future off-connector stock.',
        '80-90 was inspected previously; demand validation, not blind or independent-seed validation.']
    save('protocol.json',protocol)
    print(json.dumps({'prepared':str(OUT),'occupancy_to_lane_drop_connected':True,'only_fit_key':'lane_drop_phi'}),flush=True)


def report():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scoring import stats, score_rollout
    fitted=load(OUT/'fit/parameters.json')['parameters']
    protocol=load(OUT/'protocol.json')
    baseline={'by_direction':protocol['baseline_parameters']}
    assert load(OUT/'fit/completion.json')['complete']
    assert sha256(OUT/'fit/parameters.json')==load(OUT/'fit/freeze.json')['parameters_sha256']
    scores=load(OUT/'fit/validation.json')['scores']
    summary=[]
    for case in [protocol['training']]+protocol['validation']:
        for mode in protocol['evaluation_modes']:
            for road in ('FW_W','FW_E'):
                for label in ('baseline','calibrated'):
                    rows=[r for r in scores if (r['case'],r['mode'],r['road'],r['model'])==(case['id'],mode,road,label)]
                    row=dict(case=case['id'],mode=mode,road=road,model=label,
                        objective=sum(r['objective'] for r in rows)/len(rows),invalid=sum(r['invalid'] for r in rows))
                    for metric in ('speed','density','flow_vph','off_flow_vph'):
                        n=sum(r[metric]['count'] for r in rows)
                        row[metric+'_rmse']=math.sqrt(sum(r[metric]['rmse']**2*r[metric]['count'] for r in rows)/n)
                    summary.append(row)
    save('validation_summary.json',summary)
    data=ObservationData(B/'fw080_urban090_observations')
    model=load_base_model(data.geometry,OLD/'boundary_config.json')
    # Removing phi is not removing occupancy-dependent effective lanes. Keep
    # these two mechanisms separate in a small fixed-coefficient ablation.
    ablations=[]
    model.base.freeway_offramp_capacity_drop.enabled=False
    try:
        for cutoff in protocol['training']['cutoffs_s']:
            w=build_window(data,cutoff,'history_forecast',model_step_sec=1)
            for road in model.roads:
                for label,params in [('baseline',baseline),('calibrated',fitted)]:
                    result=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],roads=(road,))
                    ablations.append(dict(occupancy_lane_loss=False,model=label,
                        **score_rollout(data,cutoff,result,road,include_source_boundary=True)))
    finally:
        model.base.freeway_offramp_capacity_drop.enabled=True
    assert not any(r['invalid'] for r in ablations)
    save('occupancy_ablation.json',ablations)
    last=load(data.folder/'manifest.json')['last_complete_30s_window_s']
    preds=[];details=[]
    for cutoff in [round(s+data.phase_sec,6) for s in range(150,8851,150)]:
        horizon=min(150,int(round(last-cutoff)))
        w=build_window(data,cutoff,'history_forecast',model_step_sec=1,horizon_sec=horizon)
        for road in model.roads:
            result=model.rollout(w['initial_cells'],w['boundary_steps'],fitted,w['initial_origin_queue'],roads=(road,),horizon_sec=horizon)
            preds.extend(result['cells']);details.extend(result['diagnostics']['roads'])
        if int(cutoff)%900==0:print(json.dumps({'rolling_cutoff':cutoff}),flush=True)
    with gzip.open(OUT/'rolling150.json.gz','wt',encoding='utf8') as f:json.dump(preds,f)
    with gzip.open(ROOT/'diagnostics/prediction_heatmaps_20260922/fw080_urban090_150s/predictions.json.gz','rt',encoding='utf8') as f:
        old=[r for r in json.load(f) if r['model']=='boundary']
    prefix_proofs=0
    w=build_window(data,2700.1,'history_forecast',model_step_sec=1,horizon_sec=150)
    for road in model.roads:
        check=model.rollout(w['initial_cells'],w['boundary_steps'],baseline,w['initial_origin_queue'],roads=(road,),horizon_sec=150)
        expected=[{k:v for k,v in r.items() if k not in ('model','cutoff_s','horizon_s')} for r in old
                  if r['road']==road and 2700.1<r['time_s']<=2850.1]
        # Compare physical states explicitly; report metadata is not physics.
        assert len(expected)==len(check['cells'])
        fields=('road','cell','time_s','n_veh','v_kmh','rho_veh_per_km_lane')
        assert [[r[k] for k in fields] for r in expected]==[[r[k] for k in fields] for r in check['cells']]
        prefix_proofs+=1
    times=sorted(t for t in data.cells if 0<t<=last);indices={t:i for i,t in enumerate(times)}
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10})
    metrics=[]
    for road,name in (('FW_E','동측'),('FW_W','서측')):
        geo=sorted((c for c in data.geometry['cells'] if c['road']==road),key=lambda c:c['cell'])
        obs=np.full((len(geo),len(times)),np.nan)
        for t,rs in data.cells.items():
            if t not in indices:continue
            for r in rs:
                if r['road']==road and r['n_veh']>=5 and r['v_kmh'] is not None:obs[r['cell'],indices[t]]=r['v_kmh']
        panels=[('VISSIM 실측',obs)]
        for label,rows in [('기존 φ=3',old),('φ만 재보정',preds)]:
            z=np.full_like(obs,np.nan)
            for r in rows:
                if r['road']==road:z[r['cell'],indices[round(r['time_s'],6)]]=r['v_kmh']
            z[~np.isfinite(obs)]=np.nan
            mask=np.isfinite(z)&np.isfinite(obs)
            metric=dict(road=road,model=label,**stats((z[mask]-obs[mask]).tolist()));metrics.append(metric)
            panels.append((f"{label} · 속도 RMSE {metric['rmse']:.2f} km/h",z))
        fig,axes=plt.subplots(3,1,figsize=(15,10),sharex=True,sharey=True,layout='constrained')
        cmap=plt.get_cmap('RdYlBu').copy();cmap.set_bad('#e8e8e8')
        y=np.array([geo[0]['start_m']]+[r['end_m'] for r in geo])/1000
        for ax,(label,z) in zip(axes,panels):
            im=ax.pcolormesh(np.array([data.phase_sec]+times),y,z,cmap=cmap,vmin=0,vmax=120,shading='flat')
            ax.set(title=label,ylabel='상류 → 하류 [km]',xlim=(0,9000));ax.set_xticks(range(0,9001,900))
        axes[-1].set_xlabel('시뮬레이션 시간 [초]')
        fig.colorbar(im,ax=axes,label='속도 [km/h]',shrink=.85)
        phi=fitted['by_direction'][road]['lane_drop_phi']
        fig.suptitle(f'FW80 · 도시90 — {name} lane-drop 재보정 (φ 3 → {phi:.2f})\n150초마다 실측 초기화 · 과거150초 경계만 사용 · seed23',fontsize=16)
        fig.supxlabel('30초 간격 끝 시각 상태 · 실측 N<5 공통 제외 · 첫150초/기록 끝 이후는 회색\nφ 외 계수·off-ramp 저장용량·차로감소식 고정; no-control 자료만 사용',fontsize=10)
        fig.savefig(OUT/f'{road}_rolling150.png',dpi=140);plt.close(fig)
    assert all(r['density_projection_count']==0 and r['jam_density_exceedance_count']==0 and r['negative_density_count']==0
        and r['continuity_residual_max_veh']<1e-6 for r in details)
    for road in model.roads:
        assert all(v==fitted['by_direction'][road][k] for k,v in baseline['by_direction'][road].items() if k!='lane_drop_phi')
    check_queue()
    save('completion.json',dict(complete=True,parameters=fitted,rolling150=metrics,
        rolling_rollouts=len(details),validation_rollouts=len(scores),invalid=sum(r['invalid'] for r in scores),
        occupancy_ablation_rollouts=len(ablations),
        max_continuity_residual=max(r['continuity_residual_max_veh'] for r in details),
        baseline150_exact=prefix_proofs,native_queue_pins_unchanged=True,control_gain_validated=False,production_adopted=False))
    print(json.dumps(load(OUT/'completion.json'),ensure_ascii=False),flush=True)


if __name__=='__main__':
    {'prepare':prepare,'report':report}[sys.argv[1]]()
