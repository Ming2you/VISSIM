"""Offline current-plant PFO, achieved upper budgets, central SDMPC decision."""
from pathlib import Path
import copy, hashlib, json, pickle, sys, time, traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc
    from evaluation.controllers import area_follower_objective as joint
    source,out,config=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    request=pickle.loads((source/'request.pickle').read_bytes())
    tuning=json.loads(config.read_text(encoding='utf-8-sig'))
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    previous_policy=copy.deepcopy(cfg.network.sdmpc_options)
    policy=sdmpc.configure(tuning,cfg)
    if not policy.get('budget_caps') or not policy.get('pfo_each_interval') or policy['max_iterations']!=2:
        raise ValueError('Expected PFO upper-cap policy and two lower iterations')
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
        source_saved_request=str(source.resolve()),original_policy=previous_policy,sim_sec=state.time_sec,
        effective_options=options)
    budget=joint.DecisionBudget(options['decision_time_budget_sec'],reserve_sec=options['finalization_reserve_sec'],unlimited_time=True)
    def progress(row):
        line=json.dumps(json_records(dict(wall_sec=time.perf_counter()-started,**row)))
        with (out/'progress.jsonl').open('a',encoding='utf-8') as f:f.write(line+'\n')
        print(line,flush=True)
    try:
        mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
        response,selection=sdmpc.solve(controller,state,forecast,reference,mapping,options=options,
            runtime_sources=pins,worker_bootstrap=request['bootstrap'],budget=budget,progress=progress,previous_path=previous)
        report.update(completed=True,response=response,selection=selection)
        init=selection['budget_initialization'];first=selection['candidates'][0]
        checks=dict(first_np_equals_pfo=first['np_cap']==init['np_cap_veh'],
            first_nuf_equals_pfo=first['nuf_target']==init['nuf_cap_veh_h'],
            nuf_is_cap=selection['final_constraints']['nuf']['mode']=='cap',
            np_is_cap=selection['final_constraints']['np']['mode']=='cap',
            accepted_merge=selection['final_constraints']['nuf_definition']=='predicted_accepted_mainline_merge',
            no_lower_nuf_price=len(selection['price_state']['next_central_duals_scaled'])==2,
            pfo_budgetless=selection['pfo_warm_start']['budget_constraints_used'] is False,
            pfo_priceless=selection['pfo_warm_start']['prices_used'] is False,
            one_candidate=len(selection['candidates'])==1,feasible=response['feasible'])
        report['checks']=checks
        if not all(checks.values()):raise ValueError('Decision evidence check failed: '+str(checks))
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
    print(json.dumps(dict(completed=report['completed'],wall_sec=report['wall_sec'],checks=report['checks'])),flush=True)


if __name__=='__main__':main()
