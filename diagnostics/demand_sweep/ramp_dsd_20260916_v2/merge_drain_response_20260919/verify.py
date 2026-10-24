"""Freeze final code, check unchanged defaults and cost-only state invariance."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.audit import *
import numpy
import unittest,copy,hashlib,json,subprocess

def main():
    out=HERE/'verification_v1';out.mkdir(exist_ok=False)
    modules=['diagnostics.test_freeway_fd',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_response_20260919.test_state_response',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.plant_completion_20260919.test_receiving_node',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.test_off_interval',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.test_ramp_profiles',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.test_transit']
    with (out/'tests.log').open('w',encoding='utf-8') as f:
        rs=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    assert rs.wasSuccessful()
    print('tests',rs.testsRun,flush=True)
    exact=physics=0
    profile=e.load(BASE/'port_profile.json');params=e.load(BASE/'selected_parameters.json')['parameters']
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,BASE/'config.json')
        protocol=e.load(bank/'protocol.json')
        prior=H/'ramp_response_20260919/arrival_v1/gap84/model/config.json'
        normal=e.load_base_model(data.geometry,prior)
        integral=e.load_base_model(data.geometry,HERE/'decisions_v1/internal_cost/config.json')
        for arm in ['none','rm_ramp','vsl','both']:
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def cmd(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,cmd)
            pred=e.simulate(model,w,params)
            assert json.loads(json.dumps(pred))==e.load(H/'spatial_calibration_20260919/combined_v3'/f'prediction_{seed}_spatial_{arm}.json')
            exact+=1
            w=e.window(data,normal,start,'history_forecast',profile,cmd)
            a=e.simulate(normal,w,params);b=e.simulate(integral,w,params)
            for field in ['cells','flows','ramps','ports']:assert a[field]==b[field],(seed,arm,field)
            parts=e.component(data,integral,start,b)
            assert abs(parts['ramp_ttt_veh_h']-sum(r['connector_ttt_veh_h'] for r in b['ramps']))<1e-8
            physics+=1
        print('default / cost-only physical invariance',seed,flush=True)
    # The entry-speed change uses the forecast state, never an observed future.
    model=e.load_base_model(data.geometry,HERE/'decisions_v1/entry_and_cost/config.json')
    w=e.window(data,model,start,'history_forecast',profile,lambda t: ({},{}))
    data.cells={t:rs for t,rs in data.cells.items() if t<=start}
    for attr in ['flows','ports','boundaries']:
        setattr(data,attr,{k:v for k,v in getattr(data,attr).items() if k[0]<=start})
    data.port_cohorts={t:v for t,v in data.port_cohorts.items() if int(t)<=start}
    data.port_events=[r for r in data.port_events if float(r['time_s'])<=start]
    after=e.window(data,model,start,'history_forecast',profile,lambda t: ({},{}))
    assert w==after
    assert e.simulate(model,w,params)==e.simulate(model,after,params)
    conf=HERE/'decisions_v1/entry_and_cost/config.json'
    run=subprocess.run([sys.executable,'-B','-X','utf8','scripts/verify_parameters.py',str(conf.relative_to(ROOT))],
        cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (out/'parameters.log').write_text(run.stdout+run.stderr,encoding='utf-8');assert run.returncode==0
    files=[e.CAL/'canonical_harness.py',H/'evaluate_response.py',ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',
        ROOT/e.load(BASE/'config.json')['freeway']['segment_params'],conf,HERE/'decisions_v1/entry_and_cost/selected_parameters.json']
    freeze={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    write(out/'freeze.json',freeze)
    result={'unit_tests_passed':rs.testsRun,'default_full_json_exact':exact,'cost_only_full_physical_states_exact':physics,
        'future_removed_window_and_prediction_exact':True,'parameters_pass':True,'native_runs_started':0,
        'scope':'Recorded-state/component verification; not fullGNE or fresh native performance'}
    write(out/'validation.json',result);print(result,flush=True)

if __name__=='__main__':main()
