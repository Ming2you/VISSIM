"""Validate the bounded startup pilot and reject a non-binding scalar cap.

No mean-car acceleration cap is introduced into the production plant.
"""
from pathlib import Path
import sys,hashlib,math
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_restart as r
d=r.d


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=d.HERE/'restart_response_validation_v1';out.mkdir(exist_ok=False)
    startup_path=d.HERE/'downstream_restart_v3/result.json';startup=d.e.load(startup_path)
    source_checks=0
    for path,expected in startup['pins'].items():
        assert digest(d.ROOT/path)==expected;source_checks+=1
    params=r.native_parameters(d.H/'source_dsd/baseline.inpx')
    assert params['stand_m']==startup['parameters']['stand_m']
    assert params['headway_s']==startup['parameters']['headway_s']
    coverage={}
    for arm,doc in startup['results'].items():
        assert r.summarize(doc['records'])==doc['all']
        assert r.summarize([x for x in doc['records'] if len(x['predictions'])==2])==doc['common_supported']
        supported={(x['start_s'],x['vehicle']) for x in doc['records']}
        failed=set()
        for x in doc['unsupported']:
            for vid in x.get('targets',[x.get('vehicle')]):
                if vid is not None:failed.add((x['start_s'],vid))
        coverage[arm]=dict(all_target_cutoffs=len(supported|failed),supported_at_least_one_mode=len(supported),
            both_modes=sum(len(x['predictions'])==2 for x in doc['records']),
            failed_at_least_one_mode=len(failed),completely_unsupported=len(failed-supported),
            no_own_or_leader_lane_change=sum(not x['own_lane_change_in_scoring_window'] and
                not x['leader_lane_change_in_scoring_window'] for x in doc['records']),
            precontrol_records=sum(x['start_s']+20<=2400 for x in doc['records']))
    before=lambda arm:[{k:v for k,v in x.items() if k!='arm'} for x in startup['results'][arm]['records'] if x['start_s']+20<=2400]
    assert before('none') and before('none')==before('vsl')
    config_path=d.HERE/'transport_step1_exchange_off_v2/config.json';config=d.e.load(config_path)
    fw=config['freeway']
    assert fw['physical_integration_step_sec']==1 and not fw.get('physical_lane_momentum_advection',False)
    assert not fw.get('physical_lane_interruption_gamma')
    geom_path=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(geom_path)
    cells={x['cell']:x for x in geometry['cells'] if x['road']=='FW_E'}
    moment_path=d.HERE/'rm_moments_v1/s23_none.json'
    initial={x['cell']:x['speed_mean'] for x in d.e.load(moment_path)['rows'] if x['time_s']==2400 and x['lane']=='all'}
    curve=params['vehicle_by_length'][4.211]['curve']
    cap={};files=[Path(__file__),Path(r.__file__),startup_path,config_path,geom_path,moment_path]
    for arm in ('none','rm_ramp','vsl','both'):
        path=d.HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json';files.append(path)
        rows=d.e.load(path)['lane_groups']['FW_E']
        use={(int(x['time_s']),x['cell']):x for x in rows if x['cell']>=15}
        assert len(use)==450*6
        max_acc=(-math.inf,None);max_excess=(-math.inf,None);count=0;binding=0
        for t in range(2401,2851):
            for c in range(16,21):
                x=use[t,c];old=initial[c] if t==2401 else use[t-1,c]['v_kmh']
                up=initial[c-1] if t==2401 else use[t-1,c-1]['v_kmh']
                assert x['group']==0 and x['merge_in_veh']==x['off_out_veh']==x['exchanged_veh']==0
                convection=old*(up-old)/(cells[c]['length_km']*3600)
                # Material acceleration excludes movement of the speed field.
                acceleration=(x['v_kmh']-old-convection)/3.6
                bound=r.acceleration(old/3.6,curve);excess=acceleration-bound
                event=dict(time_s=t,cell=c,material_accel_mps2=acceleration,car_mean_bound_mps2=bound,
                           old_speed_kmh=old,convection_kmh=convection)
                if acceleration>max_acc[0]:max_acc=(acceleration,event)
                if excess>max_excess[0]:max_excess=(excess,event)
                binding+=excess>1e-10;count+=1
        cap[arm]=dict(steps=count,exceedances=binding,max_acceleration=max_acc[1],
                      maximum_excess_mps2=max_excess[0],maximum_excess_case=max_excess[1])
        assert count==2250 and binding==0
    # Small independent manufactured checks of the startup approximation.
    single={1:dict(pos=0.,v=0.,desired=120.,length=4.211,lane=1)}
    bounded,n=r.rollout(single,params,2,True)
    assert set(bounded[2])=={1} and 0<bounded[1][1]['v']<13
    assert abs(bounded[1][1]['v']-single[1]['v'])<=3.6*3.5
    overlap={1:dict(pos=0.,v=0.,desired=120.,length=4.211,lane=1),
             2:dict(pos=2.,v=0.,desired=120.,length=4.211,lane=1)}
    try:r.rollout(overlap,params,1,True)
    except ArithmeticError:pass
    else:raise AssertionError('Overlapping bodies silently accepted')
    old=d.e.load(d.HERE/'transport_step_work_v1/checkpoint.json')
    core_checks={}
    for path,expected in old['sha256'].items():
        if path.startswith('evaluation') or path.endswith('canonical_harness.py'):
            assert digest(d.ROOT/path)==expected;core_checks[path]=expected
    result=dict(status='PILOT_CHECKED_CAP_NONBINDING_NOT_QUALIFIED',coverage=coverage,
        source_pin_checks=source_checks,precontrol_duplicate_cases=len(before('none')),
        short_pilot_common_support={a:x['common_supported'] for a,x in startup['results'].items()},
        acceleration_cap=cap,core_hashes_unchanged=core_checks,
        manufactured_checks=['Positive bounded free acceleration','Initial overlap fails explicitly'],
        limitations=['A mean CAR cap is not a W99 implementation or a bound for every individual/type.',
            'Cap comparison covers single-group cells16..20 only; it does not address cut-in braking or merge ordering.',
            'Startup fixed-lane pilot is compared to its gap-only reference, not the full canonical METANET.',
            'Few supported targets and strong lane-changing omissions prevent using this pilot as a450s gain model.'],
        pins={str(p.relative_to(d.ROOT)):digest(p) for p in files},new_native_runs=0,core_changes=False,qualified=False)
    d.e.save(out/'result.json',result)
    print(dict(coverage=coverage,cap={a:(v['steps'],v['exceedances'],v['maximum_excess_mps2']) for a,v in cap.items()},core_checks=len(core_checks)),flush=True)


if __name__=='__main__':main()
