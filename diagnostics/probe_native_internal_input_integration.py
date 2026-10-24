"""Actual1350 canonical450s integration, with explicit historical route holding."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib,json,os,pickle,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_route_choice_integration import evaluate,direct


def main():
    if len(sys.argv)==4 and sys.argv[1] in ('--worker','--worker-off'):
        payload=pickle.loads(Path(sys.argv[2]).read_bytes())
        result=evaluate(payload) if sys.argv[1]=='--worker' else direct(payload,False)
        Path(sys.argv[3]).write_bytes(pickle.dumps(result));return
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'diagnostics/native_internal_input_canonical_1350_450.json')
    parser.add_argument('--config',type=Path,default=ROOT/'diagnostics/route_choice_native_phase_integration_config.json')
    parser.add_argument('--state',type=Path)
    parser.add_argument('--previous',type=Path)
    parser.add_argument('--scope',default='Historical1350 complete physical snapshot, six unknown past routes held explicitly. Not live route-complete validation.')
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    folder=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
    config=args.config.resolve();state_path=(args.state or folder/'state_001350.json').resolve();previous=(args.previous or folder/'action_001200.json').resolve()
    sources=[config,state_path,previous,*sorted((ROOT/'evaluation/controllers').glob('*.py'))]
    sources += [ROOT/'diagnostics'/name for name in ('route_choice_corridor_ver2.json','route_choice_corridor_1128_ver2.json',
        'native_internal_input_1091_ver2.json','physical_projection_support_635_proposal.json')]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config,state_path,previous,fixture_inputs=False)
    from diagnostics.probe_model_area_integration import replay_provenance
    hashes.update(replay_provenance(tuning))
    action=adapter.control_from_json(previous,cfg,ControlAction)
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,3)
    assert all(d.urban_boundary.get('in_SC1_E',0.)==0. for d in forecast)
    payload={'cfg':cfg,'state':state,'detectors':detectors,'tuning':tuning,'raw':raw,'action':action,'forecast':forecast}
    frozen=pickle.dumps(payload)
    result=evaluate(deepcopy(payload));assert result==evaluate(deepcopy(payload))
    on=direct(deepcopy(payload),True);off=direct(deepcopy(payload),False);assert on==off
    with tempfile.TemporaryDirectory(prefix='native1091_worker_',dir=ROOT/'diagnostics') as directory:
        directory=Path(directory);src=directory/'input.pkl';dst=directory/'output.pkl';src.write_bytes(frozen)
        for mode,expected in [('--worker',result),('--worker-off',off)]:
            child=subprocess.run([sys.executable,'-X','utf8','-m','diagnostics.probe_native_internal_input_integration',
                mode,str(src),str(dst)],cwd=ROOT,timeout=55,capture_output=True)
            assert child.returncode==0,child.stderr.decode('utf-8',errors='replace')
            assert pickle.loads(dst.read_bytes())==expected
    assert pickle.dumps(payload)==frozen
    changed=[key for key,value in hashes.items() if hashlib.sha256((ROOT/key).read_bytes()).hexdigest()!=value]
    assert not changed,changed
    stats=on['native_internal_input_state']['inputs']['1091']
    all_stats=on['native_internal_input_state']['inputs']
    for no,input_stats in all_stats.items():
        assert abs(result['area']['flow_counts'].get('input:internal:'+no,0.)-input_stats['admitted_veh'])<1e-7
    generated=result['area']['flow_counts'].get('input:internal:1091',0.)
    assert abs(generated-stats['admitted_veh'])<1e-7
    output={'scope':args.scope,
        'start_sec':raw['sim_sec'],'horizon_sec':450,'sources_sha256':hashes,'source_changes':changed,
        'main_repeat_fresh_worker_equal':True,'physical_omega_on_off_equal':True,'omega_off_fresh_worker_equal':True,
        'caller_payload_unchanged':True,'native_input_desired_admitted':stats,
        'native_input_desired_admitted_by_id':all_stats,
        'ledger_generated_inside_veh':generated,'external_gate_forecast_in_SC1_E':0.,
        'ledger_generated_inside_by_id':{no:result['area']['flow_counts'].get('input:internal:'+no,0.) for no in all_stats},
        'initial_native_input':state.native_internal_input_state,'result':result}
    destination=args.output
    if destination.exists():raise FileExistsError(destination)
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ('sources_sha256','result')}|
        {'area':{k:v for k,v in result['area'].items() if k!='flow_counts'}},indent=2))


if __name__=='__main__':main()
