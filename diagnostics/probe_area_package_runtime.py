"""One canonical150-second endpoint, repeated and in a fresh production worker."""
import argparse
import copy
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def predict(payload):
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    from evaluation.controllers import area_runtime
    from diagnostics.probe_model_area_integration import route_information
    result=evaluate_price_point(payload['state'],payload['control'],payload['forecast'],[],
        ObjectiveSpec(payload['cfg'],depth_override=1,score_mode='raw',box_walk=False))
    if result.aborted or len(result.states)!=1: raise AssertionError('Incomplete one-interval endpoint')
    final=result.states[-1]
    final._control_area_ledger.assert_stocks(area_runtime.model_inventory(final,payload['cfg']))
    fields=('freeway_density','freeway_speed','freeway_effective_lanes','freeway_flow',
            'ramp_queue','urban_movement_queue','urban_link_storage')
    return {'area':result.control_area,'objective':result.objective,
            'state':{field:getattr(final,field) for field in fields},
            'inventory':area_runtime.model_inventory(final,payload['cfg']),
            'final_route_information':route_information(final,payload['cfg'])}


def install_worker(payload):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,runtime_setup
    adapter.install_config_switches(payload['tuning'])
    os.environ['RW_OFFSET_WRITER']=payload['tuning'].get('actuation',{}).get('real_world_signal_control',{}).get('offset_writer','intent_only')
    before=pickle.dumps(payload['state'],protocol=5)
    runtime_setup.install_worker_runtime(adapter,payload['cfg'],payload['raw'],payload['detectors'])
    if before!=pickle.dumps(payload['state'],protocol=5): raise AssertionError('Worker changed received state')


def fresh_worker(input_path,output_path):
    if output_path.exists(): raise FileExistsError(output_path)
    payload=pickle.loads(input_path.read_bytes())
    install_worker(payload)
    result=predict(payload)
    with output_path.open('x',encoding='utf-8') as stream: json.dump(result,stream)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','snapshot','previous','action','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Choose a new output: '+str(args.output))
    for path in (args.config,args.snapshot,args.previous,args.action):
        if not path.is_file(): raise FileNotFoundError(path)
    from diagnostics.probe_model_area_integration import build_projected,adapter,replay_provenance,route_information
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(args.config,args.snapshot,args.previous,fixture_inputs=False)
    if not hasattr(state,'_control_area_ledger'): raise ValueError('Explicit area config required')
    os.environ['RW_OFFSET_WRITER']=tuning.get('actuation',{}).get('real_world_signal_control',{}).get('offset_writer','intent_only')
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)
    payload={'cfg':cfg,'state':state,'detectors':detectors,'tuning':tuning,'raw':raw,
             'control':adapter.control_from_json(args.action,cfg,ControlAction),'forecast':forecast}
    inputs=(args.config,args.snapshot,args.previous,args.action,Path(__file__))
    before=replay_provenance(tuning,*inputs); frozen=pickle.dumps(payload,protocol=5)
    initial_routes=route_information(state,cfg)
    main_result=predict(copy.deepcopy(payload))
    repeated_payload=copy.deepcopy(payload)
    install_worker(repeated_payload);install_worker(repeated_payload)
    repeated=predict(repeated_payload)
    if repeated!=main_result: raise AssertionError('Repeated worker setup changed prediction')
    with tempfile.TemporaryDirectory(prefix='canonical-worker-',dir=ROOT/'diagnostics') as folder:
        temporary=Path(folder).resolve()
        if not temporary.is_relative_to((ROOT/'diagnostics').resolve()): raise ValueError('Worker temp escaped diagnostics')
        input_path,output_path=temporary/'input.pkl',temporary/'output.json'; input_path.write_bytes(frozen)
        child=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),'--worker',str(input_path),str(output_path)],
            cwd=ROOT,text=True,encoding='utf-8',capture_output=True,timeout=55)
        if child.returncode: raise AssertionError('Fresh worker failed: '+child.stderr[-8000:])
        fresh=json.loads(output_path.read_text(encoding='utf-8'))
        if fresh!=json.loads(json.dumps(main_result)): raise AssertionError('Fresh worker changed prediction')
    if frozen!=pickle.dumps(payload,protocol=5): raise AssertionError('Original input objects changed')
    after=replay_provenance(tuning,*inputs)
    if any(after.get(key)!=value for key,value in before.items()): raise AssertionError('Input/source changed')
    output={'implementation':'installed configure_runtime, canonical endpoint and install_worker_runtime',
            'horizon_sec':float(raw['control_interval_sec']),'main_worker_equal':True,'fresh_worker_equal':True,
            'worker_reinstall_state_unchanged':True,'original_inputs_unchanged':True,'all_stock_closures_pass':True,
            'initial_route_information':initial_routes,'prediction':main_result,'source_sha256':after,'source_unchanged':True,
            'scope':'One held declared action and current forecast. Holding unknown routes is diagnostic only; no search/VISSIM.'}
    with args.output.open('x',encoding='utf-8') as stream: json.dump(output,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(args.output),'main_worker_equal':True,'fresh_worker_equal':True}))


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--worker': fresh_worker(Path(sys.argv[2]),Path(sys.argv[3]))
    else: main()
