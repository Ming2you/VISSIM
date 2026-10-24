"""Run existing lane physics checks OFF/ON using explicitly recorded old fixtures.

Only missing read-only JSON/CSV fixture paths under diagnostics/demand_sweep
may use the original lane worktree. Never redirect source, writes or existing data.
"""
from pathlib import Path
import hashlib
import json
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    original=Path.open
    original_exists=Path.exists
    fixture_root=ROOT.parent/'sdmpc-lane-plant-20260921'
    used={}
    def missing_source(path):
        actual=path.resolve()
        if (not original_exists(path) and actual.suffix in ('.json','.csv')
                and actual.is_relative_to(ROOT/'diagnostics/demand_sweep')):
            relative=actual.relative_to(ROOT)
            source=fixture_root/relative
            if source.is_file():
                return source
        return None
    def opened(path,*args,**kwargs):
        mode=args[0] if args else kwargs.get('mode','r')
        source=missing_source(path) if mode in ('r','rb','rt') else None
        if source is not None:
            with original(source,'rb') as stream:sha=hashlib.sha256(stream.read()).hexdigest()
            used[str(path.resolve().relative_to(ROOT))]=dict(source=str(source),sha256=sha)
            return original(source,*args,**kwargs)
        return original(path,*args,**kwargs)
    results=[]
    module='diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.test_lane_groups'
    with patch.object(Path,'open',opened),patch.object(Path,'exists',
            lambda path:original_exists(path) or missing_source(path) is not None):
        from evaluation.controllers.sdmpc_prediction_cache import scope
        for enabled in (False,True):
            print('Existing physical lane tests; array_transport='+str(enabled),flush=True)
            cfg=NS(network=NS(sdmpc_options=dict(prediction_cache=True,array_transport=enabled)))
            with scope(cfg):
                suite=unittest.defaultTestLoader.loadTestsFromName(module)
                result=unittest.TextTestRunner(verbosity=2).run(suite)
            results.append(dict(enabled=enabled,tests=result.testsRun,passed=result.wasSuccessful(),
                failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors]))
    folder=ROOT/'diagnostics/sdmpc_array_transport_20260922'
    report=dict(scope=__doc__,fixtures=used,results=results,pass_all=all(r['passed'] for r in results))
    (folder/'physical_fixture_check_v3.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
