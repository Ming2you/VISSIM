"""Four fixed forecasts of the already reviewed physical-path candidate."""
import ctypes
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent
ROOT = I.parents[2]
OUT = HERE/'physical_path_comparison'
TUNING = I/'expanded036_9000_20260930/loss_onset2250/physical_speed/candidate_config.json'
OLD = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def main():
    OUT.mkdir(exist_ok=False)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    from evaluation.controllers import obs150_contract as oc
    history = json.loads((HERE/'observer_replay_v3/summary.json').read_bytes())
    assert history['stage']=='consumed_head_and_vsl_history_exact'
    def readonly(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived)
        return path
    oc.write_derived=readonly
    source=I/'probe_selected_arrival_path.py'
    spec=importlib.util.spec_from_file_location('candidate_probe',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.probe_levers
    prior=json.loads((I/'closedloop_recorded2250_lever450_RM_C10484_city2250_ps_all8/held_actual.json').read_bytes())
    baseline=json.loads((I/'closedloop_recorded2250_lever450_RM_C10484_trace10484_of2/summary.json').read_bytes())
    protocol=dict(max_forecasts=4,optimizer_iterations=0,coefficient_fits=0,new_native_runs=0,
        candidate='Previously reviewed head-lane attribution, SC1002 SG6 service ownership, SC1001 physical-observation travel speed; no new parameters.',
        comparison='Same onset2250 held/RM10484/VSL13-release/both commands; native four-arm results already known, so not a blind holdout.',
        adoption='No automatic production adoption. Require physical flow/stock improvement and preserve strong independent RM ordering; tiny signs are not a fitting target.',
        prior_held_cost=prior['ttt_omega_veh_h'],results=None)
    files=[Path(__file__),source,TUNING,HERE/'observer_replay_v3/summary.json',HERE/'protocol.json',
           OLD/'state_002250.json',OLD/'action_002250.json',
           ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/lane_plant_runtime.py',
           ROOT/'evaluation/controllers/route_choice_corridor.py',ROOT/'evaluation/controllers/head_service_resources.py',
           ROOT/'evaluation/controllers/physical_ramp_boundary.py',ROOT/'evaluation/controllers/lane_ramp_runtime.py']
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    protocol['source_pins']=pins
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    calls=[]
    def audited(captured,reference,output,**kwargs):
        from src.controllers import rollout_endpoint as ep
        evaluate=ep.evaluate_price_point
        def bounded(*args,**kw):
            assert len(calls)<4,'Finite budget exhausted'
            point=evaluate(*args,**kw)
            calls.append(float(point.ttt))
            if len(calls)==1:
                assert abs(point.ttt-prior['ttt_omega_veh_h'])<1e-9,('Existing candidate changed',point.ttt)
            return point
        ep.evaluate_price_point=bounded
        try:
            original(captured,reference,output,**dict(kwargs,onset_factorial=True,first_interval_audit=True))
        finally:
            ep.evaluate_price_point=evaluate
        assert len(calls)==4
        result=json.loads((output/'summary.json').read_bytes())
        for arm,row in result['results'].items():
            assert row['commands']==baseline['results'][arm]['commands'],arm
            assert row['physical_cell_states'][0]==baseline['results'][arm]['physical_cell_states'][0],arm
        (OUT/'results_location.json').write_text(json.dumps(dict(output=str(output),costs=calls),indent=2)+'\n',encoding='utf-8')
    module.probe_levers=audited
    sys.argv=[str(source),'--closedloop-recorded','--at=2250','--lever-probe450',
        '--meter-ramp=RM_C10484','--trace-ramp=RM_C10484','--warm-head-history','--replay-vsl-history',
        '--recording-dir='+str(OLD),'--tuning-json='+str(TUNING),'--probe-label=onset_ps4_20261001']
    started=time.perf_counter();module.main()
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
    (OUT/'completion.json').write_text(json.dumps(dict(stage='four_forecasts_complete',forecasts=len(calls),
        wall_sec=time.perf_counter()-started,new_native_runs=0,optimizer_iterations=0,source_pins_unchanged=True),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
