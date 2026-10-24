"""Run the existing real urban/ramp coupling tests with persistent storage OFF/ON."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_prediction_cache import scope


def main():
    rows=[]
    for enabled in (False,True):
        cfg=NS(network=NS(sdmpc_options=dict(prediction_cache=True,persistent_urban_fifo=enabled)))
        print('Persistent FIFO enabled:',enabled,flush=True)
        with scope(cfg):
            suite=unittest.defaultTestLoader.loadTestsFromName('diagnostics.test_lane_plant_coupling')
            result=unittest.TextTestRunner(verbosity=2).run(suite)
        rows.append(dict(enabled=enabled,tests=result.testsRun,passed=result.wasSuccessful()))
    out=ROOT/'diagnostics/sdmpc_persistent_plant_20260922/coupling_v1.json'
    with out.open('x',encoding='utf-8') as f:json.dump(rows,f,indent=2)
    return 0 if all(r['passed'] for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
