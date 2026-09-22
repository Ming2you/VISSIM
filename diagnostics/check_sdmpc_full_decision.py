"""Full offline SDMPC decision from a qualified saved request. No VISSIM."""
from pathlib import Path
import copy
import hashlib
import json
import pickle
import sys
import time
import traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def json_value(value):
    from src.models.state import ControlAction
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,ControlAction): return vars(value)
    raise TypeError('Unsupported result field: '+type(value).__name__)


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc
    from evaluation.controllers import area_follower_objective as joint
    source,out=map(Path,sys.argv[1:3]); out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    request=pickle.loads((source/'request.pickle').read_bytes())
    receipt=json.loads((source/'result.json').read_text())
    for name,expected in receipt['transformed_source_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Qualified derivative source changed: '+name)
        request['bootstrap']['runtime_sources'][name]=expected
    follower,state,reference,forecast=request['owned']; cfg=follower.cfg
    tuning_path=(Path(sys.argv[3]).resolve() if len(sys.argv)>3 else
                 ROOT/'diagnostics/sdmpc_reverse_20260921/config_candidate.json')
    tuning=json.loads(tuning_path.read_text(encoding='utf-8'))
    declared=sdmpc.configure(tuning,copy.deepcopy(cfg))
    if declared!=cfg.network.sdmpc_options:
        raise ValueError('Qualified request differs from the declared candidate policy')
    # Build the installed leader independently; retain the exact qualified
    # follower and state, including its three-block and derivative options.
    controller=adapter.build_priced_wu_link_controller(copy.deepcopy(cfg),tuning)
    controller.cfg=cfg; controller.nash_solver=follower
    if hasattr(controller.leader,'cfg'): controller.leader.cfg=cfg
    coord,callbacks,ctx,options=context(request)
    if options['response_parallel_workers']!=8:
        raise ValueError('Expected eight response workers')
    previous=(ROOT.parent/'sdmpc-lane-plant-20260921/evaluation/runs/lane_native_nc2850_s13_v3'
              '/decisions_lane_native_nc2850_s13_v3/action_000750.json')
    if state.time_sec!=900. or not previous.is_file():
        raise ValueError('This full-decision qualification requires the original 900s/750s anchor')
    mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
    pins=dict(request['bootstrap']['runtime_sources'])
    for path in (Path(__file__),ROOT/'diagnostics/sdmpc_json_records.py',tuning_path,ROOT/'evaluation/parameters.json',
                 *sorted((ROOT/'evaluation/controllers').glob('*.py'))):
        pins[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
    request['bootstrap']['runtime_sources']=pins
    budget=joint.DecisionBudget(options['decision_time_budget_sec'],
        reserve_sec=options['finalization_reserve_sec'],unlimited_time=True)
    report=dict(completed=False,native_applied=False,scope=__doc__,policy=cfg.network.sdmpc_options,
        source_sha256=pins,sim_sec=state.time_sec)
    def progress(row):
        event=dict(wall_sec=time.perf_counter()-started,**row)
        line=json.dumps(event,default=json_value)
        with (out/'progress.jsonl').open('a',encoding='utf-8') as stream: stream.write(line+'\n')
        print(line,flush=True)
    try:
        response,selection=sdmpc.solve(controller,state,forecast,reference,mapping,options=options,
            runtime_sources=pins,worker_bootstrap=request['bootstrap'],budget=budget,
            progress=progress,previous_path=previous)
        report.update(completed=True,response=response,selection=selection)
        report['iteration_context']={
            'max_iterations_per_candidate':cfg.network.sdmpc_options['max_iterations'],
            'candidates':[dict(np_cap=r['np_cap'],accepted_iterations=r['accepted_steps'],
                               status=r['status'],converged=r['converged']) for r in selection['candidates']],
            'converged':selection['converged'],
            'note':'Accepted outer iterations; prediction calls and QP inner iterations are separate.'}
    except Exception:
        report['error']=traceback.format_exc()
        raise
    finally:
        query=getattr(budget,'response_query',None)
        if query is not None:
            query.close(); report['query']=query.stats()
        report['wall_sec']=time.perf_counter()-started
        report['source_changes']=[p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        if report['source_changes']: report['completed']=False
        (out/'result.pickle').write_bytes(pickle.dumps(report,protocol=5))
        (out/'result.json').write_text(json.dumps(json_records(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=report['completed'],wall_sec=report['wall_sec'],
        iteration_context=report.get('iteration_context'),
        feasible=report['response']['feasible'],native_applied=False)),flush=True)


if __name__=='__main__':main()
