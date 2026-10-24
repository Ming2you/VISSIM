"""Small synthetic conservation/API checks; never reads any native FZP."""
import copy
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'))
from canonical_harness import load_base_model
from extract_observations import physical_geometry


def run():
    network = ROOT/'diagnostics/demand_sweep/user_native_20260914/east080_v1/source_network/baseline.inpx'
    geometry = physical_geometry(network)
    model = load_base_model(geometry)
    initial = [{"road": r["road"], "cell": r["cell"], "time_s": 900,
                "n_veh": 25.0, "v_kmh": 80.0} for r in geometry["cells"]]
    steps = [{"window_start_s": t, "window_end_s": t+10,
              "source_demand_vph": dict.fromkeys(model.roads, 2000.0),
              "ramp_release_vph": dict.fromkeys(model.ramps, 50.0),
              "off_capacity_vph": dict.fromkeys(model.offramps, 1000.0),
              "off_split_ratio": dict.fromkeys(model.offramps, 0.01)} for t in range(900,1350,10)]
    snapshot = copy.deepcopy((initial,steps))
    first = model.rollout(initial,steps)
    repeat = model.rollout(initial,steps)
    assert first == repeat, "Repeated candidate must be deterministic without global parameter bleed"
    assert (initial,steps) == snapshot, "Caller input mutation"
    assert len(first['cells']) == len(first['flows']) == 630
    for row in first['diagnostics']['roads']:
        assert row['continuity_residual_max_veh'] < 1e-9, row
        assert row['density_projection_count'] == 0, row
    # A directional parameter change must not alter the other independent road.
    changed = model.rollout(initial,steps,{'by_direction':{'FW_E':{'v_free_multiplier':.85}}})
    assert [r for r in first['cells'] if r['road']=='FW_W'] == [r for r in changed['cells'] if r['road']=='FW_W']
    assert [r for r in first['cells'] if r['road']=='FW_E'] != [r for r in changed['cells'] if r['road']=='FW_E']
    assert first == model.rollout(initial,steps), "Calibrated values leaked into baseline"
    excessive = copy.deepcopy(steps)
    # A single forced boundary spike is deliberately infeasible; it must be
    # visible as a jam exceedance, never mislabeled as ordinary congestion.
    excessive[0]['ramp_release_vph'] = dict.fromkeys(model.ramps, 100000.0)
    invalid = model.rollout(initial,excessive)
    assert all(r['jam_density_exceedance_count'] > 0 and r['maxdensity_ratio'] > 1
               for r in invalid['diagnostics']['roads']), invalid['diagnostics']
    try:
        model.rollout(initial,steps[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError('Short horizon accepted')
    return {'status':'PASS','synthetic_frames':len(first['cells']),
            'checks':['450s contiguous','traffic-state input immutable','selected flow conservation',
                      'direction isolation','parameter reset','repeat determinism','incomplete horizon rejection',
                      'forced merge above jam explicitly detected'],
            'diagnostics':first['diagnostics'],'model_provenance':model.provenance}


if __name__ == '__main__':
    result = run()
    path = Path(__file__).with_name('selftest_harness.json')
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':result['checks']}))
