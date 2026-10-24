"""Verify the saved lane-wave observations and conditional FD experiment."""
from pathlib import Path
import sys,csv,json,hashlib,math
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d
import canonical_harness as ch


def main():
    out=d.HERE/'downstream_wave_v2';obs=d.e.load(out/'result.json')
    fd=d.e.load(d.HERE/'downstream_fd_resolution_v1/result.json')
    pins=0
    for doc,key in ((obs,'sources'),(fd,'pins')):
        for path,digest in doc[key].items():
            assert hashlib.sha256((d.ROOT/path).read_bytes()).hexdigest()==digest; pins+=1
    cfgpath=d.HERE/'transport_step1_exchange_off_v2/config.json'
    model=d.e.load_base_model(d.e.load(d.H/'controller_response_s23_v1/none/geometry.json'),cfgpath)
    p=d.e.load(d.HERE/'port_travel_fit_v1/selected_parameters.json')['parameters']
    cfg=model._config('FW_E',p['by_direction']['FW_E']);control=ch.ControlAction.uncontrolled(cfg)
    mn=ch.accounting._mn;equations=0;csvchecks=0;records=0
    assert not getattr(cfg.network,'freeway_state_response',None)
    for arm,bycell in obs['summaries'].items():
        rows=list(csv.DictReader((out/f'{arm}_lane_1s.csv').open(encoding='utf-8')))
        assert len(rows)==601*7*3
        assert len({(r['time_s'],r['cell'],r['lane']) for r in rows})==len(rows)
        for c,summary in bycell.items():
            use=[r for r in rows if r['cell']==c and 2400<int(r['time_s'])<=2850]
            assert len(use)==450*3
            assert abs(sum(int(r['n']) for r in use)/3600-summary['ttt_1s_veh_h'])<1e-9
            for field in ('stopped_veh','slow_veh'):
                key={'stopped_veh':'stopped_vehicle_sec','slow_veh':'slow30_vehicle_sec'}[field]
                assert sum(int(r[field]) for r in use)==summary[key]
            assert sum(r['masked_stopped_cluster']=='True' for r in use)==summary['lane_seconds_masked_stopped_cluster']
            csvchecks+=4
        for scale,phases in fd['results'][arm].items():
            for phase,result in phases.items():
                records+=result['errors']['coarse']['n']
                assert result['errors']['coarse']==fd['results'][arm]['100.0'][phase]['errors']['coarse']
                for example in result['examples']:
                    c=example['cell'];r=example['current']
                    vsl=mn.segment_vsl(control,'FW_E',c,cfg)
                    active=vsl<max(cfg.freeway_follower.vsl_set)-.5
                    actual=mn.effective_desired_speed_kmh(r['rho'],cfg.network.v_free,cfg.network.rho_crit,
                        vsl,cfg.network.alpha_vsl,active,cfg.network.metanet_a_m,
                        getattr(cfg.network,'vsl_fd_two_branch',False),cfg.network.rho_max,
                        float(getattr(cfg.network,'rho_crit_two_branch',0.) or 0.))
                    assert abs(actual-r['coarse_eq'])<1e-9,(c,vsl,actual,r['coarse_eq'])
                    equations+=1
    assert obs['validation']['identical_precontrol_original9_rows']==31318
    assert sum(obs['validation']['snapshot_stock_and_speed'].values())==1932
    for arm in fd['results']:
        for scale in fd['results'][arm]:
            assert fd['results'][arm][scale]['precontrol']==fd['results']['none'][scale]['precontrol']
    result=dict(status='OBSERVATION_AND_CONDITIONAL_DIAGNOSTIC_VERIFIED_NOT_QUALIFIED',
                source_pin_checks=pins,csv_summary_checks=csvchecks,native_snapshot_checks=1932,
                exact_precontrol_native_rows=31318,canonical_equilibrium_call_matches=equations,
                conditional_comparisons_including_repeated_scales=records,
                native_runs=0,production_changes=0,qualification=False,
                not_proven=['Causal450s gain prediction','Future lane stop/release timing','Fresh holdout',
                            'VSL or both gain improvement','Full Omega/GNE'],
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    d.e.save(out/'validation.json',result);print(result)


if __name__=='__main__':main()
