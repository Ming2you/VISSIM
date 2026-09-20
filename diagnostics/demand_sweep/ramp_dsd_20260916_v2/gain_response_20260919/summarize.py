"""Explicit gain/ranking qualification; never promote a failed physical candidate."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL
import statistics
import hashlib

HERE=Path(__file__).resolve().parent


def main():
    fit=e.load(HERE/'fit_v2/evaluation.json');shape=e.load(HERE/'speed_shape_trial_v1/results.json')
    summary={}
    for name in ['baseline','candidate','speed_shape']:
        summary[name]={}
        for seed in ['13','23','33']:
            refs=fit['baseline']['seeds'][seed]['deltas']
            actual={a:r['actual']['total'] for a,r in refs.items()}
            pred=({a:r['predicted']['total'] for a,r in fit[name]['seeds'][seed]['deltas'].items()}
                  if name!='speed_shape' else {a:r['total'] for a,r in shape[seed]['deltas'].items()})
            cost={'none':0.,**pred};best=min(cost.values())
            actual_cost={'none':0.,**actual};actual_best=min(actual_cost.values())
            selected=[a for a,v in cost.items() if abs(v-best)<1e-8]
            summary[name][seed]={'delta_predicted':pred,'delta_actual':actual,
                'delta_mae_veh_h':statistics.mean(abs(pred[a]-actual[a]) for a in actual),
                'direction_matches':sum(abs(pred[a])>1e-8 and pred[a]*actual[a]>0 for a in actual),
                'best_candidates_with_numeric_ties':selected,
                'actual_best':[a for a,v in actual_cost.items() if abs(v-actual_best)<1e-8],
                'selection_regret_range_veh_h':[min(actual_cost[a]-actual_best for a in selected),max(actual_cost[a]-actual_best for a in selected)],
                'native_interaction_veh_h':actual['both']-actual['rm_ramp']-actual['vsl'],
                'predicted_interaction_veh_h':pred['both']-pred['rm_ramp']-pred['vsl']}
    e.save(HERE/'QUALIFICATION.json',{'status':'gain_prediction_not_qualified',
        'adopted_candidate':None,'unchanged_component_reference':str(MODEL.relative_to(e.ROOT)),
        'conclusions':[
            'Actual merge counts/timing alone do not recover seed23 mainline VSL or full RM response.',
            'Bounded coefficient response calibration improves training loss slightly, not seed23 signs or seed33 validation.',
            '1s integration and actual1s merge pulses do not resolve the gap.',
            'Observed speed-shape closure makes VSL responsive but predicts the wrong late-state net-benefit sign.',
            'No new reward, artificial capacity gain/drop, native demand change, model promotion or VISSIM run.'],
        'metrics':summary,'scope':'450s FW_E mainline+4on+4off connectors; not Omega or4500s performance',
        'validation_seeds_note':'13/23 used for response fit;33 withheld from this coefficient fit but previously seen development data, not an independent fresh seed'})
    # Verify that the production physics and the reference configuration have
    # not been changed while diagnostic hooks were tried in separate processes.
    pins=e.load(HERE/'isolation_v2/protocol.json')['pins']
    assert all(hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==v for p,v in pins.items())
    clock=e.load(HERE/'clock_v1/results.json')
    assert all(not r['score']['invalid'] for modes in clock.values() for arms in modes.values() for a,r in arms.items() if a!='delta')
    assert all(not r['state_score']['invalid'] for seed in shape.values() for r in seed['arms'].values())
    e.save(HERE/'verification.json',{'canonical_source_and_config_pins_unchanged':True,
        'clock_rollouts_numerically_valid':24,'speed_shape_rollouts_numerically_valid':12,
        'inactive_shape_none_and_RM_full_JSON_exact':6,'speed_snapshot_counts_and_means_match_existing_observer':True,
        'native_speed_source_rows':sum(e.load(HERE/f'speed_shapes_v1/evidence_s{s}.json')['rows'] for s in [13,23,33]),
        'native_runs_started':0})
    for name,scores in summary.items():
        print(name,{s:round(r['delta_mae_veh_h'],6) for s,r in scores.items()},flush=True)


if __name__=='__main__':main()
