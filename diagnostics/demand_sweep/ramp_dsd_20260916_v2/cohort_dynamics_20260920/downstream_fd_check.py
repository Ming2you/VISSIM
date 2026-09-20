"""One explicit spatial-FD ablation: undo ordinary3's effective1.4 multiplier.

No gain fitting or capacity bonus. The parameter-free comparison uses the
previous3-lane class value28, not a new claim of measured critical density.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from contextlib import contextmanager
import canonical_harness as ch
import copy,json,math,hashlib,argparse

HERE=Path(__file__).resolve().parent
OUT=HERE/'downstream_fd_check_v2'


@contextmanager
def trace_cell14():
    """Capture consumed runtime coefficients; wrappers never change a value."""
    mn=ch.accounting._mn;sv=mn.segment_vsl;up=mn.metanet_speed_update_kmh
    context={};audit=[]
    def segment(control,road,index,cfg):
        value=sv(control,road,index,cfg)
        context.update(road=road,cell=index,net=cfg.network)
        return value
    def speed(*args,**kwargs):
        result=up(*args,**kwargs)
        if context.get('road')=='FW_E' and context.get('cell')==14:
            v,uv,rho,down,veq,dt,length,tau,nu,kappa,vmin=args
            net=context['net'];p=net.freeway_segment_params['FW_E'][14]
            tau=p.get('metanet_tau_h',tau);length=p.get('segment_length_km',length)
            kappa=p.get('metanet_kappa_veh_km_lane',kappa)
            terms=dict(relaxation=dt/tau*(veq-v),convection=dt/length*v*(uv-v),
                anticipation=-nu*dt/tau/length*(down-rho)/(rho+kappa))
            reconstructed=max(vmin,v+sum(terms.values()))
            assert abs(reconstructed-result)<1e-8,(reconstructed,result)
            audit.append(dict(step=len(audit)//3,group=len(audit)%3,speed_before=v,
                upstream_speed=uv,rho=rho,downstream_rho=down,desired_speed=veq,
                tau_sec=tau*3600,nu=nu,kappa=kappa,length_km=length,
                fd=dict(p),terms=terms,before_merge_speed=result))
        return result
    mn.segment_vsl=segment;mn.metanet_speed_update_kmh=speed
    try:yield audit
    finally:mn.segment_vsl=sv;mn.metanet_speed_update_kmh=up


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--local-response',action='store_true')
    args=parser.parse_args()
    if args.local_response:OUT=HERE/'local_merge_response_v1'
    OUT.mkdir(exist_ok=False)
    config=HERE/'port_origin_split_v1/config.json';cfg=e.load(config)
    old_fd=e.ROOT/cfg['freeway']['segment_params'];document=e.load(old_fd)
    params_file=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(params_file)['parameters'];profile=e.load(MODEL/'port_profile.json')
    changed=[]
    scoped=None
    if args.local_response:
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.fit_local_speed import records
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.open_speed_recalibration import fit,score
        p=params['by_direction']['FW_E']
        train=[r for r in records(23,'none') if r['cell'] in [13,14] and r['time_s']<2400]
        selected,trials=fit(train,p,False);spec=selected['spec']
        scoped=dict(cells=[13,14],tau_sec=spec['relaxation']['acceleration_sec'],nu=spec['anticipation']['downstream_ge_local'])
        assert spec['relaxation']['acceleration_sec']==spec['relaxation']['deceleration_sec']
        assert spec['anticipation']['downstream_ge_local']==spec['anticipation']['downstream_lt_local']
        e.save(OUT/'fit.json',dict(training='Seed23 NC900..2390 cell13/14 only, speed next10s; no cost or control-arm fitting',
            selected=selected,trials=trials,scoped=scoped,
            development={str(seed):score([r for r in records(seed,'none') if r['cell'] in [13,14] and (seed!=23 or r['time_s']>=2400)],p,spec) for seed in [23,33]}))
        print('LOCAL_SELECTION',scoped,selected['score'],flush=True)
    for i in ([] if args.local_response else range(15,21)):
        row=document['segments'][f'FW_E_S{i}'];assert row['lanes']==3 and abs(row['rho_crit']-39.2)<1e-7
        changed.append(dict(cell=i,old_critical=row['rho_crit'],new_critical=28.))
        row['rho_crit']=28.
        row['q_cap_veh_h_lane']=row['v_free']*28.*math.exp(-1/row['metanet_a_m'])
    document['downstream_fd_ablation']=dict(status='DIAGNOSTIC_NOT_CALIBRATED',changes=changed,
        reason='Restore existing plain3-lane class value; no control gain fitting or new capacity drop.')
    fdpath=OUT/'segment_params.json';e.save(fdpath,document)
    cfg['freeway']['segment_params']=str(fdpath.relative_to(e.ROOT)).replace('\\','/')
    candidate=OUT/'config.json';e.save(candidate,cfg)
    files=[Path(__file__),config,old_fd,fdpath,candidate,params_file,MODEL/'port_profile.json',
        e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',e.ROOT/'evaluation/controllers/freeway_fd.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if scoped:files.extend([HERE/'fit_local_speed.py',HERE/'open_speed_recalibration.py',OUT/'fit.json'])
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(OUT/'protocol.json',dict(status='LOCAL_NC_FIT_NOT_QUALIFIED' if scoped else 'SINGLE_SPATIAL_FD_ABLATION_NOT_FIT',changes=changed,pins=pins,
        scoped_response=scoped,application='Diagnostic _config instance applies scoped coefficients after global calibration; production/default config unchanged.',
        unchanged='Both use open outlet; same initial observations, previous coefficients, ramp/exit dynamics and controls.',
        future_inputs=False,new_native_runs=0,guard_reference=str(MODEL),
        reference='spatial_calibration_20260919/REPORT.md documents prior effective calibration, not physical measured capacity.'))
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores']
    results={};exact=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        results[str(seed)]={}
        for name,path in [('open_reference',config),('local_response' if scoped else 'plain3_critical',candidate)]:
            model=e.load_base_model(data.geometry,path);original=model._config
            def configured(road,override):
                value=original(road,override)
                if road=='FW_E':value.network.terminal_zero_gradient=True
                if road=='FW_E' and name=='local_response':
                    for index in scoped['cells']:
                        row=value.network.freeway_segment_params[road][index]
                        row['metanet_tau_h']=scoped['tau_sec']/3600
                        row['metanet_nu_km2_h']=scoped['nu']
                return value
            model._config=configured
            def window(t,command):
                w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origins['counts'])
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                    'initial_ramp_origin':origins['counts'][str(t)],
                    'initial_off_eligible':origins['eligible_before_off'][str(t)]}}
                return w
            guards={}
            for t in [900,1650,2400,3600]:
                p=e.simulate(model,window(t,lambda _: ({},{})),params)
                s=e.score_rollout(data,t,p,'FW_E');assert not s['invalid']
                guards[str(t)]=dict(score=s,vs_established=s['objective']/established[str(seed)][str(t)]['objective'])
            forecasts={}
            for arm in list(ARMS)+(['rm10484'] if seed==23 else []):
                seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
                if arm=='rm10484':seq=dict(green=[8,6,4],vsl=[])
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10484' if arm=='rm10484' else 'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                with trace_cell14() as audit:
                    pred=e.simulate(model,window(start,command),params)
                assert len(audit)==135
                if seed==23 and arm=='none':e.save(OUT/f'speed_terms_{name}.json',audit)
                old=e.load(HERE/'direct10484_s23_v1/prediction_open_candidate_rm10484.json' if arm=='rm10484'
                    else HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
                if name=='open_reference':assert json.loads(json.dumps(pred))==old;exact+=1
                for key in ['cells','flows']:
                    assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
                for r in pred['diagnostics']['roads']:
                    assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
                forecasts[arm]=parts(pred);e.save(OUT/f'prediction_s{seed}_{name}_{arm}.json',pred)
            deltas={a:{k:v-forecasts['none'][k] for k,v in row.items()} for a,row in forecasts.items() if a!='none'}
            for row in deltas.values():row['total']=sum(row.values())
            results[str(seed)][name]=dict(guards=guards,parts=forecasts,deltas=deltas,
                guards_passed=sum(s['vs_established']<=1.1 for s in guards.values()))
            print(seed,name,'guards',results[str(seed)][name]['guards_passed'],deltas,flush=True)
        e.save(OUT/f'result_s{seed}.json',results[str(seed)])
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(OUT/'results.json',dict(results=results,reference_exact=exact,source_pins_verified=True,
        qualified=False,consumed_cell14_speed_terms_reconstructed=True))


if __name__=='__main__':main()
