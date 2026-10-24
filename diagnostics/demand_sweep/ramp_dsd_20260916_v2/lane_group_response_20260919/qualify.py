"""Keep adoption decisions separate from implementation/invariant success."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, ARMS, MODEL
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.run import HERE
import hashlib
import statistics


def main():
    result=e.load(HERE/'qualification_v6/results.json')
    old=e.load(H/'gain_response_20260919/fit_v2/evaluation.json')['baseline']
    records=[];state_checks=[];interactions={};mae={};maximum_residual=0.
    for seed,r in result.items():
        actual={'none':0.};predicted={'none':0.}
        for arm in ARMS[1:]:
            target=r['actual'][arm]['FW_E']['total'];value=r['deltas'][arm]['total']
            before=old['seeds'][seed]['deltas'][arm]['predicted']['total']
            records.append({'seed':int(seed),'arm':arm,'actual_delta_veh_h':target,
                            'old_prediction_veh_h':before,'new_prediction_veh_h':value})
            actual[arm]=target;predicted[arm]=value
        interactions[seed]={'actual':actual['both']-actual['rm_ramp']-actual['vsl'],
                            'predicted':predicted['both']-predicted['rm_ramp']-predicted['vsl'],
                            'actual_ranking':sorted(actual,key=actual.get),'predicted_ranking':sorted(predicted,key=predicted.get)}
        mae[seed]={'before':statistics.mean(abs(x['old_prediction_veh_h']-x['actual_delta_veh_h']) for x in records if x['seed']==int(seed)),
                   'after':r['delta_mae']}
        for t,scores in r['state_guards'].items():
            a,b=scores['baseline']['objective'],scores['candidate']['objective']
            state_checks.append({'seed':int(seed),'cutoff':int(t),'old':a,'new':b,'within_ten_percent':b<=a*1.1})
        for arm in ARMS:
            final=e.load(HERE/f'qualification_v6/prediction_{seed}_{arm}.json')
            earlier=e.load(HERE/f'qualification_v4/prediction_{seed}_{arm}.json')
            for key in ['cells','flows','ports','diagnostics']:
                assert final[key]==earlier[key],(seed,arm,key,'extra ledger fields changed physics')
            for receipts in [final['ramps'],earlier['ramps']]:
                for receipt in receipts:receipt.pop('receiving_node',None)
            assert final['ramps']==earlier['ramps'],(seed,arm,'ramp physics')
            road=next(r for r in final['diagnostics']['roads'] if r['road']=='FW_E')
            maximum_residual=max(maximum_residual,road['continuity_residual_max_veh'],road['lane_group_continuity_residual_max_veh'])
    verification=e.load(HERE/'qualification_v6/verification.json')
    assert verification['default_full_prediction_exact_cases']==12
    assert e.load(HERE/'tests_final.json')['passed']
    e.save(HERE/'QUALIFICATION.json',{'adopted':False,'status':'NOT_QUALIFIED',
        'reason':['Seed23 RM and VSL benefit signs remain wrong','Combined-control interaction remains near zero',
                  'Absolute state error exceeds the ten-percent guard in some NC windows'],
        'records':records,'interactions':interactions,'delta_mae_by_seed':mae,'state_checks':state_checks,
        'verification':{**verification,'unit_tests_passed':71,'lane_and_aggregate_continuity_max_veh':maximum_residual,
                        'ledger_only_revision_full_physical_predictions_exact':12},
        'scope':'FW_E mainline + its four on-ramp and four off-ramp connectors; not Omega',
        'seed33_is_fresh_holdout':False,
        'failures_preserved':{'smoke_v1':'Rejected initial FIFO/lateral closure; inaccessible branch labels falsely stopped whole groups',
            'qualification_v2':'Output writer attempted exclusive-create results.json twice; eight prediction files preserved, incomplete summary',
            'stdin_test_attempt':'Windows child could not spawn <stdin>; only owned process24624 stopped, file-based71tests passed'},
        'remaining_model_assumptions':['Past150s lateral hazards frozen over450s',
            'No desired-speed/headway distribution or DSD-crossing cohorts within each lane group',
            'Off-route labels inferred at branch-cell entry, not observed destination inventory',
            'Off connectors retain aggregate storage and historical departure proxy',
            'Ramp node retains fitted gap-acceptance closure with target-group mean flow',
            'No online lane-group observer or full-GNE integration'],
        'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.CAL/'canonical_harness.py',H/'evaluate_response.py',
             HERE/'qualification_v6/config.json',HERE/'qualification_v6/parameters.json',MODEL/'config.json',
             MODEL/'selected_parameters.json',MODEL/'port_profile.json']}})
    print('NOT_QUALIFIED',mae,'max conservation residual',maximum_residual,flush=True)


if __name__=='__main__':main()
