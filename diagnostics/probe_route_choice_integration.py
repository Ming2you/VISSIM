"""Actual canonical1129 integration:450s endpoint and fresh worker, no VISSIM."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,os,pickle,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def evaluate(payload):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, runtime_setup,area_runtime,route_choice_corridor
    cfg,state=payload['cfg'],payload['state']
    adapter.install_config_switches(payload['tuning'])
    frozen=pickle.dumps(state)
    runtime_setup.install_worker_runtime(adapter,cfg,payload['raw'],payload['detectors'])
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    assert pickle.dumps(state)==frozen
    point=evaluate_price_point(state,payload['action'],payload['forecast'],[],ObjectiveSpec(cfg,depth_override=3,score_mode='raw'))
    assert pickle.dumps(state)==frozen
    for value in point.states:
        value._control_area_ledger.assert_stocks(area_runtime.model_inventory(value,cfg))
    return {'objective':point.objective,'area':point.control_area,
            'final_inventory':area_runtime.model_inventory(point.states[-1],cfg),
            'initial_choice':route_choice_corridor.diagnostics(state,cfg),
            'final_choice':route_choice_corridor.diagnostics(point.states[-1],cfg),
            'input_unchanged':True}


def direct(payload,area_on):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,runtime_setup,area_runtime
    from src.simulation import coupling
    cfg,state,action=deepcopy(payload['cfg']),payload['state'].copy(),deepcopy(payload['action'])
    cfg.network.control_area_enabled=area_on
    if not area_on: state.__dict__.pop('_control_area_ledger',None)
    runtime_setup.install_worker_runtime(adapter,cfg,payload['raw'],payload['detectors'])
    totals=[]
    for demand in payload['forecast']:
        result=coupling.run_coupled_interval(state,action,demand,cfg)
        totals.append(vars(result))
        state.time_sec+=cfg.simulation.control_interval
        if area_on: state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
    physical={k:v for k,v in vars(state).items() if not k.startswith('_control_area')}
    return physical


def main():
    if len(sys.argv)==4 and sys.argv[1] in ('--worker','--worker-off'):
        payload=pickle.loads(Path(sys.argv[2]).read_bytes())
        value=evaluate(payload) if sys.argv[1]=='--worker' else direct(payload,False)
        Path(sys.argv[3]).write_bytes(pickle.dumps(value)); return
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    run=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
    config=ROOT/'diagnostics/route_choice_integration_config.json'
    sources=[config,*[ROOT/'evaluation/controllers'/name for name in ('route_choice_corridor.py','runtime_setup.py','urban_flow_accounting.py','shared_approach.py','area_runtime.py','area_dynamic_routes.py','projection_support.py')],ROOT/'diagnostics/route_choice_corridor_ver2.json']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config,run/'state_001350.json',run/'action_001200.json',fixture_inputs=False)
    action=adapter.control_from_json(run/'action_001200.json',cfg,ControlAction)
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,3)
    payload={'cfg':cfg,'state':state,'detectors':detectors,'tuning':tuning,'raw':raw,'action':action,'forecast':forecast}
    initial=pickle.dumps(payload)
    main_result=evaluate(deepcopy(payload)); repeated=evaluate(deepcopy(payload))
    assert main_result==repeated
    on=direct(deepcopy(payload),True);off=direct(deepcopy(payload),False)
    assert on==off, [key for key in on if on[key]!=off.get(key)]
    with tempfile.TemporaryDirectory(prefix='choice_worker_',dir=ROOT/'diagnostics') as directory:
        folder=Path(directory).resolve()
        assert folder.is_relative_to((ROOT/'diagnostics').resolve())
        src,dst=folder/'input.pkl',folder/'output.pkl';src.write_bytes(initial)
        child=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',str(src),str(dst)],cwd=ROOT,timeout=55,capture_output=True)
        if child.returncode: raise AssertionError(child.stderr.decode('utf-8',errors='replace'))
        fresh=pickle.loads(dst.read_bytes());assert fresh==main_result
        child=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker-off',str(src),str(dst)],cwd=ROOT,timeout=55,capture_output=True)
        if child.returncode: raise AssertionError(child.stderr.decode('utf-8',errors='replace'))
        fresh_off=pickle.loads(dst.read_bytes());assert fresh_off==off
    assert pickle.dumps(payload)==initial
    changes=[key for key,value in hashes.items() if hashlib.sha256((ROOT/key).read_bytes()).hexdigest()!=value]
    output={'mode':'historical holding diagnostic; not live complete-route validation','seconds':450,'initial_sim_sec':1350,
            'sources_sha256':hashes,'source_changes_during_probe':changes,
            'main_repeated_fresh_worker_equal':True,'physics_omega_on_off_450s_equal':True,'omega_off_fresh_worker_equal':True,
            'new_external_demand_at_former_shared_receiver':forecast[0].urban_boundary.get('in_SC1005_W',0.),
            'main':main_result}
    path=ROOT/'diagnostics/route_choice_canonical_1350_450.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ('sources_sha256','main')}|{'objective':main_result['objective'],'initial_choice':main_result['initial_choice'],'final_choice':main_result['final_choice'],'output':str(path)},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
