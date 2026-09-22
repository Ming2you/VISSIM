"""New central-reuse SDMPC: one budget candidate, two outer iterations, offline."""
from pathlib import Path
import copy
import hashlib
import json
import pickle
import sys
import time
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc
    from evaluation.controllers import area_follower_objective as joint
    source,out,config=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    request=pickle.loads((source/'request.pickle').read_bytes())
    tuning=json.loads(config.read_text(encoding='utf-8-sig'))
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    previous_policy=copy.deepcopy(cfg.network.sdmpc_options)
    policy=sdmpc.configure(tuning,cfg)
    expected=dict(previous_policy,central_multiplier=True,central_options=policy['central_options'])
    if policy!=expected or not policy.get('central_multiplier') or policy['max_iterations']!=2:
        raise ValueError('New benchmark must only add central algorithm to the qualified two-iteration policy')
    context(request)
    options=adapter.joint_owner_game_settings(tuning,cfg,'wu-link')
    if options['max_leader_candidates']!=1 or options['response_parallel_workers']!=8:
        raise ValueError('Expected one budget candidate and eight workers')
    controller=adapter.build_priced_wu_link_controller(copy.deepcopy(cfg),tuning)
    controller.cfg=cfg;controller.nash_solver=follower
    if hasattr(controller.leader,'cfg'):controller.leader.cfg=cfg
    previous=ROOT.parent/'sdmpc-lane-plant-20260921/evaluation/runs/lane_native_nc2850_s13_v3/decisions_lane_native_nc2850_s13_v3/action_000750.json'
    if state.time_sec!=900. or not previous.is_file():raise ValueError('Saved benchmark anchor unavailable')
    paths=set(map(Path,request['bootstrap']['runtime_sources']))
    paths.update([Path(__file__).resolve(),config.resolve(),ROOT/'evaluation/parameters.json',
                  ROOT/'diagnostics/check_sdmpc_three_blocks.py',ROOT/'diagnostics/sdmpc_json_records.py'])
    paths.update((ROOT/'evaluation/controllers').glob('*.py'))
    pins={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    request['bootstrap']['runtime_sources']=pins
    (out/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    report=dict(completed=False,native_applied=False,scope=__doc__,policy=policy,source_sha256=pins,
        source_saved_request=str(source.resolve()),original_policy=previous_policy,
        input_semantics='Same saved 900s state, reference and forecast; explicitly changed controller policy and current source pins',
        sim_sec=state.time_sec,effective_options=options)
    budget=joint.DecisionBudget(options['decision_time_budget_sec'],reserve_sec=options['finalization_reserve_sec'],unlimited_time=True)
    def progress(row):
        event=dict(wall_sec=time.perf_counter()-started,**row)
        line=json.dumps(json_records(event))
        with (out/'progress.jsonl').open('a',encoding='utf-8') as f:f.write(line+'\n')
        print(line,flush=True)
    try:
        mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
        response,selection=sdmpc.solve(controller,state,forecast,reference,mapping,options=options,
            runtime_sources=pins,worker_bootstrap=request['bootstrap'],budget=budget,
            progress=progress,previous_path=previous)
        report.update(completed=True,response=response,selection=selection)
        report['iteration_context']=dict(max_iterations_per_candidate=policy['max_iterations'],
            candidates=[dict(np_cap=c['np_cap'],nuf_target=c['nuf_target'],accepted_iterations=c['accepted_steps'],
                             status=c['status'],converged=c['converged']) for c in selection['candidates']],
            converged=selection['converged'])
        if len(selection['candidates'])!=1:raise ValueError('Incorrect benchmark candidate count')
    except BaseException:
        report['completed']=False;report['error']=traceback.format_exc();raise
    finally:
        query=getattr(budget,'response_query',None)
        if query is not None:query.close();report['query']=query.stats()
        report['wall_sec']=time.perf_counter()-started
        report['source_changes']=[p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        if report['source_changes']:report['completed']=False
        (out/'result.pickle').write_bytes(pickle.dumps(report,protocol=5))
        (out/'result.json').write_text(json.dumps(json_records(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=report['completed'],wall_sec=report['wall_sec'],
        iteration_context=report['iteration_context'],feasible=response['feasible'])),flush=True)


if __name__=='__main__':main()
