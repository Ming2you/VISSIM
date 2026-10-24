"""Record completed evidence gates separately from gain-model qualification."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import hashlib
import unittest
from datetime import datetime

HERE=Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    tests=unittest.defaultTestLoader.loadTestsFromName(
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.dsd_response_20260920.test_desired_speed')
    result=unittest.TextTestRunner(verbosity=1).run(tests)
    assert result.wasSuccessful()
    run=HERE/'native_v2/run_retry1'
    execution=e.load(run/'run.json');actuation=e.load(run/'fixed_validation.json')
    replay=e.load(HERE/'observed_v2/validation.json')
    clocks=e.load(HERE/'clock_v2/summary.json')
    changed=next(r for r in clocks['statistics'] if r['changed_only'] and r['frame_offset']==1)
    all_crossings=next(r for r in clocks['statistics'] if not r['changed_only'] and r['frame_offset']==1)
    assert execution['completed'] and execution['terminal_sec']==3000 and not execution['owned_native_alive']
    assert actuation['passed'] and actuation['event_readbacks']==128
    assert actuation['untargeted_snapshot_sha256_before']==actuation['untargeted_snapshot_sha256_after']
    assert replay['physical_original_nine_columns_exact'] and replay['rows']==11791383
    assert changed['recorded']==changed['eligible']==1505 and changed['over_001_kmh']==0
    assert changed['max_abs_error_kmh']<.002
    assert all_crossings['over_001_kmh']==0
    assert e.load(HERE/'station_v1/protocol.json')['precontrol_station_summaries_exact']
    conservation=e.load(HERE/'local_queue_v1/conservation.json')
    assert all(r['residual']==0 for r in conservation.values())
    candidates=[(13,'vsl','exchange_s13_v1'),(23,'vsl','exchange_probe_v2'),
                (33,'vsl','exchange_s33_v1'),(23,'rm_ramp','exchange_s23_rm_v1'),
                (23,'both','exchange_s23_both_v1')]
    comparisons=[]
    for seed,arm,folder in candidates:
        r=e.load(HERE/folder/'summary.json')
        assert r['history_predictions_exact']
        assert r['qualification']=='DIAGNOSTIC_ONLY_FUTURE_INPUTS'
        comparisons.append({'seed':seed,'arm':arm,'history':r['deltas']['history'],
                            'future_exchange_diagnostic':r['deltas']['future_arm_exchange'],'actual':r['actual']})
    e.save(HERE/'gain_diagnostics.json',comparisons)
    files=list(HERE.glob('*.py'))+[HERE/'REPORT.md',
        e.ROOT/'evaluation/controllers/desired_speed_transport.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.CAL/'canonical_harness.py',
        e.HERE/'evaluate_response.py',HERE/'native_v2/protocol.json',
        HERE/'native_v2/prepared/network/baseline.inpx',run/'run.json',run/'fixed_validation.json',
        run/'vissim_eval/baseline_001.fzp',run/'baseline_001.err',run/'baseline.err',
        HERE/'observed_v2/validation.json',HERE/'clock_v2/summary.json',
        HERE/'station_v1/protocol.json',HERE/'local_queue_v1/conservation.json']
    files += [HERE/folder/'summary.json' for _,_,folder in candidates]
    pins={str(p.relative_to(e.ROOT)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}
    record={'status':'ACTUATOR_EVENT_MAPPING_VERIFIED_GAIN_NOT_QUALIFIED','adopted':False,
        'new_runtime_controller_feature_enabled':False,'new_native_run_completed':True,
        'new_independent_performance_replicate':False,'native_physical_replay_exact':True,
        'replayed_physical_rows':replay['rows'],'native_LDP_and_apply_readback_passed':True,
        'changed_desired_speed_crossings':changed,'all_testable_crossings':all_crossings,
        'terminal_censored_unchanged_crossings':all_crossings['eligible']-all_crossings['recorded'],
        'unit_tests_passed':result.testsRun,'local_inventory_balance':conservation,
        'history_prediction_exact_executions':10,'unique_history_predictions':8,
        'oracle_diagnostic_cases':len(candidates),'fitted_parameters':0,
        'elapsed_launch_to_final_validation_sec':(datetime.fromisoformat(execution['finished'])-
            datetime.fromisoformat(execution['started'])).total_seconds(),
        'remaining':['Causal control-dependent lane exchange and blocking',
                     'RM merge target-lane discharge/recovery benefit',
                     'Component costs and combined-control interaction',
                     'Independent seed validation before controller promotion'],
        'pins':pins}
    e.save(HERE/'QUALIFICATION.json',record)
    print(record['status'],flush=True)


if __name__=='__main__':main()
