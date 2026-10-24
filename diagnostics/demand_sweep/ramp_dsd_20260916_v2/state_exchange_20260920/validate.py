"""Run the existing physical invariants plus the new closure tests from a file."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import numpy
import unittest


def main():
    p='diagnostics.demand_sweep.ramp_dsd_20260916_v2.'
    names=['diagnostics.test_freeway_fd',p+'state_response_20260919.test_state_response',
        p+'plant_completion_20260919.test_receiving_node',p+'spatial_calibration_20260919.test_off_interval',
        p+'ramp_response_20260919.test_ramp_profiles',p+'merge_drain_response_20260919.test_transit',
        'diagnostics.handoff_20260916.test_restore_evidence',p+'lane_group_response_20260919.test_lane_groups',
        p+'dsd_response_20260920.test_desired_speed',p+'state_exchange_20260920.test_exchange']
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    e.save(Path(__file__).with_name('tests.json'),{'tests':result.testsRun,'passed':result.wasSuccessful(),
        'failures':[str(r) for r in result.failures],'errors':[str(r) for r in result.errors]})
    raise SystemExit(not result.wasSuccessful())


if __name__=='__main__':main()
