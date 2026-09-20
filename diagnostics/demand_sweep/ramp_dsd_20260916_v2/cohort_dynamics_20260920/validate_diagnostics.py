"""Independent invariant checks for resolution and boundary-causality evidence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.flux_closure import e,H,HERE,transport,skipped_off_exit
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.interruption_oracle import moments
import hashlib
import argparse


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rm',action='store_true')
    args=parser.parse_args()
    out=HERE/('rm_diagnostic_validation_v1.json' if args.rm else 'diagnostic_validation_v1.json');assert not out.exists()
    checks={}
    # Constant-speed/constant-density transport must preserve the stationary
    # solution at both time resolutions and every tested spatial partition.
    fields=[{'t':t,'n':[5.]*8,'v_sum':[180.]*8,'in':.4 if t else 0.,'out':.4 if t else 0.}
            for t in range(61)]
    for parts,step in [(1,10),(1,1),(2,1),(4,1)]:
        r=transport(fields,[.5,.5],parts,step)
        assert abs(r['end_n']-40)<1e-10 and abs(r['out']-24)<1e-10
        assert abs(r['ttt_veh_h']-2/3)<1e-10 and r['n_rmse']<1e-10
    checks['stationary_transport_cases']=4
    routes={10643:{10641:(319.,2.25)}}
    assert skipped_off_exit((10643,317.,12.,None,'off'),(10641,.44,21.,None,None),routes)
    assert not skipped_off_exit((10643,250.,12.,None,'off'),(10641,.44,21.,None,None),routes)
    assert not skipped_off_exit((10643,317.,12.,None,'off'),None,routes)
    checks['short_link_geometry_cases']=3
    velocities=0
    for seed,arms in [(23,['none','vsl']),(33,['none','spread_only'])]:
        widths=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')['geometry']['widths']
        for arm in arms:
            data=moments(seed,arm)
            pred=e.load(HERE/f'complete_speed_oracle_v2/prediction_s{seed}_all_{arm}.json')
            for r in pred['lane_groups']['FW_E']:
                t,c,g=int(r['time_s']),r['cell'],r['group']
                lane_keys=([str(g+1)] if len(widths[c])>1 and g<2 else
                    [str(l) for l in range(1 if len(widths[c])==1 else 3,int(sum(widths[c]))+1)])
                obs=[data[t,c,l] for l in lane_keys if (t,c,l) in data]
                if not obs:continue
                v=sum(x['n']*x['speed_mean'] for x in obs)/sum(x['n'] for x in obs)
                assert abs(r['v_kmh']-v)<1e-8,(seed,arm,t,c,g)
                velocities+=1
    checks['complete_speed_oracle_exact_group_samples']=velocities
    for name in ['s23_none','s23_vsl','s33_none','s33_spread']:
        proof=e.load(HERE/f'urban_drain_observations_v5/{name}_evidence.json')
        rows=e.rows(HERE/f'urban_drain_observations_v5/{name}.csv')
        assert len(rows)==1050 and proof['signal_program_native_checks']==2102
        assert sum(int(r[f'urban_sg{g}_removals']) for r in rows for g in (2,5))==len(proof['explicit_urban_removals'])
        assert all(r['fzp_absence_confirms_abnormal_loss'] for r in proof['explicit_urban_removals'])
    checks['urban_native_signal_samples']=4*2102
    checks['urban_state_flow_one_second_rows']=4*1050
    for seed,arm in [(23,'vsl'),(33,'spread_only')]:
        nc=e.load(HERE/f'component_boundary_cohorts_v1/s{seed}_none.json')
        ctl=e.load(HERE/f'component_boundary_cohorts_v1/s{seed}_{arm}.json')
        assert nc['initial_vehicle_ids']==ctl['initial_vehicle_ids']
        for r in [nc,ctl]:
            assert not r['unexplained_events'] and abs(r['residence_identity_residual'])<1e-8
            assert abs(sum(r['cohort_residence_veh_h'].values())-r['ttt_veh_h'])<1e-8
    checks['native_cohort_mass_cost_cases']=4
    sources=[Path(__file__),HERE/'flux_closure.py',HERE/'speed_oracle.py',HERE/'urban_drain.py']
    if args.rm:
        attribution=e.load(HERE/'rm_port_attribution_v1/result.json')
        assert attribution['native_stock_checks']==720
        checks['rm_native_port_stock_checks']=720
        for seed in [23,33,43]:
            nc=e.load(HERE/f'rm_boundary_cohorts_v1/s{seed}_none.json')
            ctl=e.load(HERE/f'rm_boundary_cohorts_v1/s{seed}_rm_ramp.json')
            assert nc['initial_vehicle_ids']==ctl['initial_vehicle_ids']
            for r in [nc,ctl]:
                assert not r['unexplained_events'] and abs(r['residence_identity_residual'])<1e-8
                assert abs(sum(r['cohort_residence_veh_h'].values())-r['ttt_veh_h'])<1e-8
        checks['rm_native_cohort_mass_cost_cases']=6
        velocities=0
        for seed in [23,33]:
            widths=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')['geometry']['widths']
            for arm in ['none','rm_ramp']:
                data={(r['time_s'],r['cell'],r['lane']):r for r in e.load(HERE/f'rm_moments_v1/s{seed}_{arm}.json')['rows']}
                pred=e.load(HERE/f'rm_speed_oracle_v1/prediction_s{seed}_all_{arm}.json')
                for r in pred['lane_groups']['FW_E']:
                    t,c,g=int(r['time_s']),r['cell'],r['group']
                    ls=([g+1] if len(widths[c])>1 and g<2 else
                        range(1 if len(widths[c])==1 else 3,int(sum(widths[c]))+1))
                    obs=[data[t,c,str(l)] for l in ls if (t,c,str(l)) in data]
                    if not obs:continue
                    v=sum(x['n']*x['speed_mean'] for x in obs)/sum(x['n'] for x in obs)
                    assert abs(r['v_kmh']-v)<1e-8
                    velocities+=1
        checks['rm_speed_oracle_exact_group_samples']=velocities
        terminal=e.load(HERE/'terminal_probe_v1/results.json')
        assert terminal['existing_full_json_exact']==12 and terminal['west_cells_and_flows_exact']==12
        checks['terminal_existing_full_json_exact']=12
        checks['terminal_west_unchanged']=12
        sources.extend([HERE/'rm_attribution.py',HERE/'terminal_probe.py',HERE/'extract_moments.py'])
    for p in sources:compile(p.read_text(encoding='utf-8'),str(p),'exec')
    e.save(out,{'passed':True,'checks':checks,'core_or_controller_changes_in_this_checkpoint':False,
        'qualification':'Diagnostics validated; gain prediction still NOT_QUALIFIED',
        'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})
    print(checks,flush=True)


if __name__=='__main__':main()
