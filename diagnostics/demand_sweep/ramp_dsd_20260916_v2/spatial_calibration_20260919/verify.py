"""Frozen installed calibration, archive compatibility and causal replay."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.calibrate import *
import unittest
from contextlib import redirect_stdout, redirect_stderr
import numpy  # Resolve bundled dependencies before legacy tests alter sys.path.

def main():
    out=HERE/'combined_v3';out.mkdir(exist_ok=False)
    modeldir=out/'model';modeldir.mkdir()
    for filename in ['config.json','selected_parameters.json','port_profile.json']:
        doc=e.load(HERE/'fit_v1/model'/filename)
        if filename=='config.json':doc['freeway']['physical_offramp_interval_service']=True
        if filename=='selected_parameters.json':doc['adoption']='Spatial FD plus corrected drainage clock. Absolute prediction improvement only; control-response gate pending.'
        write(modeldir/filename,doc)
    pins=[modeldir/'config.json',modeldir/'selected_parameters.json',modeldir/'port_profile.json',
          HERE/'fit_v1/model/segment_params.json', e.CAL/'canonical_harness.py',
          ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/freeway_fd.py',
          ROOT/'evaluation/controllers/area_freeway_accounting.py']
    freeze={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
    write(out/'freeze.json',freeze)
    modules=['diagnostics.test_freeway_fd',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_response_20260919.test_state_response',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.plant_completion_20260919.test_receiving_node',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.test_off_interval']
    with (out/'tests.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    if not result.wasSuccessful():raise AssertionError('Unit tests failed')
    evaluate(out,modeldir)
    default_checks=west_checks=0
    for seed in [13,23,33]:
        for arm in ARMS:
            before=e.load(HERE/'fit_v1'/f'prediction_{seed}_baseline_{arm}.json')
            after=e.load(out/f'prediction_{seed}_baseline_{arm}.json')
            assert before==after,('Archived default changed',seed,arm)
            if seed in [13,23]:
                era='early13' if seed==13 else 'late23'
                older=e.load(H/'plant_completion_20260919/response_installed_v2'/f'{era}_node_{arm}.json')
                assert after==older,('Historical node default changed',seed,arm)
            default_checks+=1
            spatial=e.load(out/f'prediction_{seed}_spatial_{arm}.json')
            for field in ['cells','flows']:
                assert [r for r in after[field] if r['road']=='FW_W']==[r for r in spatial[field] if r['road']=='FW_W']
            west_checks+=1
    # Remove every future measurement before constructing a window. A forecast
    # must neither consult it nor change when it is absent.
    data,model,profile,windows=setup(H/'controller_response_s23_v1/none',modeldir/'config.json')
    w=windows[2400]
    data.cells={t:rs for t,rs in data.cells.items() if t<=2400}
    data.boundaries={k:r for k,r in data.boundaries.items() if k[0]<=2400}
    data.flows={k:r for k,r in data.flows.items() if k[0]<=2400}
    data.ports={k:r for k,r in data.ports.items() if k[0]<=2400}
    data.port_cohorts={k:r for k,r in data.port_cohorts.items() if int(k)<=2400}
    data.port_events=[r for r in data.port_events if float(r['time_s'])<=2400]
    assert w==e.window(data,model,2400,'history_forecast',profile,lambda t: ({},{}))
    for p,sha in freeze.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha
    validation={'unit_tests_passed':result.testsRun,'default_full_json_exact_checks':default_checks,
        'older_archived_default_checks':8,'west_mainline_state_and_flow_exact_checks':west_checks,
        'future_measurements_removed_window_exact':True,'frozen_files_unchanged':True,
        'native_runs_started':0,'scope':'Offline replay of completed validated native experiments. Not a new native run or full GNE.'}
    write(out/'verification.json',validation)
    print(validation,flush=True)

if __name__=='__main__':main()
