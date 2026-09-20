"""File entrypoint required by Windows multiprocessing tests."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import unittest
import importlib
import json
import argparse


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(__file__).with_name('tests_port_travel_v1.json'))
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve previous test evidence: '+str(args.output))
    p='diagnostics.demand_sweep.ramp_dsd_20260916_v2.'
    names=['diagnostics.test_freeway_fd',p+'state_response_20260919.test_state_response',
        p+'plant_completion_20260919.test_receiving_node',p+'spatial_calibration_20260919.test_off_interval',
        p+'ramp_response_20260919.test_ramp_profiles',p+'merge_drain_response_20260919.test_transit',
        'diagnostics.handoff_20260916.test_restore_evidence',p+'lane_group_response_20260919.test_lane_groups',
        p+'dsd_response_20260920.test_desired_speed',p+'state_exchange_20260920.test_exchange',
        p+'cohort_dynamics_20260920.test_interruption',p+'cohort_dynamics_20260920.test_off_lanes',
        p+'cohort_dynamics_20260920.test_destination',p+'cohort_dynamics_20260920.test_momentum',
        p+'cohort_dynamics_20260920.test_port_travel',p+'cohort_dynamics_20260920.test_upstream_inventory',
        p+'cohort_dynamics_20260920.test_ramp_lane_coupling',p+'cohort_dynamics_20260920.test_ramp_exchange']
    suite=unittest.TestSuite()
    for name in names:
        m=importlib.import_module(name)
        for c in vars(m).values():
            if isinstance(c,type) and issubclass(c,unittest.TestCase) and c.__module__==name:
                suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    r=unittest.TextTestRunner(verbosity=1).run(suite)
    args.output.write_text(json.dumps({
        'tests':r.testsRun,'passed':r.wasSuccessful(),'failures':[str(x) for x in r.failures],
        'errors':[str(x) for x in r.errors]},indent=2),encoding='utf-8')
    raise SystemExit(not r.wasSuccessful())


if __name__=='__main__':main()
