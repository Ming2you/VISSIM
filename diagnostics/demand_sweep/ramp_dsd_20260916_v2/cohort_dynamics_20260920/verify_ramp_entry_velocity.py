"""Check completed entry-velocity trials without rerunning their forecasts."""
from pathlib import Path
import argparse
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ARMS=('none','rm_ramp','vsl','both')


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(check_only=False):
    current_script=HERE/'ramp_entry_velocity_check.py'
    pins_checked=0
    for version in ('v2','v3'):
        work=HERE/('ramp_entry_velocity_work_'+version)
        protocol=load(work/'protocol.json')
        for name,digest in protocol['source_pins'].items():
            p=ROOT/name
            if version=='v2' and p==current_script:
                p=work/'source_before_spatial_variant.txt'
            assert sha(p)==digest,name
            pins_checked+=1
        for values in protocol['estimated_entry_speeds'].values():
            assert 2250<values['first_event']<=values['last_event']<=2400
        assert load(work/'result.json')['source_pins_verified']
    modes=('reference','mix_keep_merge','mix_replace_merge','short_merge_keep')
    checked_moments=0;cases={}
    for mode in modes:
        work=HERE/('ramp_entry_velocity_work_v3' if mode=='short_merge_keep' else 'ramp_entry_velocity_work_v2')
        trace=load(work/(mode+'_trace.json'))
        for r in trace:
            expected=0. if mode=='reference' else r['ramp_amount']*(r['entry_speed']-r['assumed_ramp_speed'])
            assert abs(r['stock']*(r['v_after']-r['v_before'])-expected)<1e-7
            assert abs(r['expected_moment_change']-expected)<1e-7
            assert r['stock']+1e-7>=r['ramp_amount']>=0
            checked_moments+=1
        folder=HERE/('ramp_entry_velocity_'+mode+'_v2')
        result=load(folder/'result.json')
        summary=load(work/(mode+'_summary.json'))
        assert summary['consumed_ode_moment_checks']==(3600 if mode=='short_merge_keep' else 5400)
        for arm in ARMS:
            pred=load(folder/f'prediction_{arm}.json')
            base=load(HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json')
            if mode=='reference':assert pred==base
            for key in ('cells','flows','ports','ramps'):
                assert [r for r in pred[key] if r.get('road')=='FW_W']==[r for r in base[key] if r.get('road')=='FW_W']
            assert pred['local_ramp_audit']['passed']
            for d in pred['diagnostics']['roads']:
                assert d['continuity_residual_max_veh']<1e-7
                assert d['negative_density_count']==d['jam_density_exceedance_count']==0
        for delta in result['deltas'].values():
            assert abs(sum(delta[x] for x in ('mainline','on','off'))-delta['total'])<1e-8
        cases[mode]=dict(deltas=result['deltas'],nc_objective=summary['nc_objective'],
            consumed_ode_moment_checks=summary['consumed_ode_moment_checks'],qualified=False)
    report=dict(passed=True,qualified=False,previous_goal_turn='progress: completed and verified GitHub delivery56fcfac',
        source_pins_checked=pins_checked,reference_full_jsons_exact=4,completed_forecasts=16,
        candidate_west_and_conservation_checks=12,moment_identities=checked_moments,
        consumed_ode_moment_checks=sum(v['consumed_ode_moment_checks'] for v in cases.values()),
        cases=cases,decision='All three causal candidates fail net-gain signs; retain disabled, do not promote.',
        invalid_first_attempt='work_v1/adjudication.json: nonpartition mixing was overwritten; excluded.',
        new_native_runs=0,full_omega_or_gne_validation=False,multi_state_guards=False,fresh_holdout=False,
        core_source_sha256=sha(ROOT/'evaluation/controllers/physical_lane_groups.py'),
        verifier_sha256=sha(Path(__file__)))
    if not check_only:
        with (HERE/'ramp_entry_velocity_validation_v1.json').open('x',encoding='utf-8') as f:
            json.dump(report,f,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check-only',action='store_true',help='Verify without overwriting the completed receipt')
    main(ap.parse_args().check_only)
