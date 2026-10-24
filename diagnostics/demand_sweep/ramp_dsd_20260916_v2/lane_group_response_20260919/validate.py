"""Run from a file: Windows multiprocessing tests cannot spawn from stdin."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import numpy
import unittest
import argparse


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='tests.json');args=parser.parse_args()
    p='diagnostics.demand_sweep.ramp_dsd_20260916_v2.'
    names=['diagnostics.test_freeway_fd',p+'state_response_20260919.test_state_response',
           p+'plant_completion_20260919.test_receiving_node',p+'spatial_calibration_20260919.test_off_interval',
           p+'ramp_response_20260919.test_ramp_profiles',p+'merge_drain_response_20260919.test_transit',
           'diagnostics.handoff_20260916.test_restore_evidence',p+'lane_group_response_20260919.test_lane_groups']
    r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    e.save(Path(__file__).with_name(args.output),{'tests':r.testsRun,'passed':r.wasSuccessful(),
        'failures':[str(x) for x in r.failures],'errors':[str(x) for x in r.errors]})
    raise SystemExit(not r.wasSuccessful())


if __name__=='__main__':main()
