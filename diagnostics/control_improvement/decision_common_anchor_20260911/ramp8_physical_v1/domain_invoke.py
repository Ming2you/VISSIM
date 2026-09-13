"""Recorded-state canonical domain/writer/response audit; no COM or optimizer."""
import csv
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.chdir(ROOT)
os.environ['RW_OFFSET_WRITER']='experiment'
label=sys.argv[1]
parity_only=sys.argv[2:]==['--deferred-parity']
if sys.argv[2:] and not parity_only:raise ValueError('Unknown domain audit option')
if not label.replace('_','').isalnum():raise ValueError('Fresh explicit result label required')
target=D/(label+'.json')
if target.exists():raise FileExistsError(target)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
paths=[Path(__file__),D/'domain_config.json',D/'topology.json',record/'state_000900.json',record/'action_000750.json',record/'action_000900.json',record/'action_000900.csv']
paths+=list((ROOT/'evaluation/controllers').glob('*.py'))
pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
report={'complete':False,'native_run':False,'source_sha256':pins,'owners':{},'responses':{},
    'scope':'Canonical physical eight-meter candidate generation and CSV projection at recorded80/50seed13t900. Frozen held450s response checks; not a joint-game optimization or native execution.'}
started=time.perf_counter()
try:
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as a,area_follower_objective as objective,physical_ramp_branches as ramps
    from evaluation.controllers import joint_owner_game as game
    from src.models.state import ControlAction,segment_vsl
    from src.models.demand import DemandStep
    from src.controllers import rollout_endpoint as ep
    cfg,state,det,tuning,raw,mapping,metadata=build_projected(D/'domain_config.json',record/'state_000900.json',record/'action_000750.json',fixture_inputs=False)
    cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
    controller=a.build_priced_wu_link_controller(cfg,tuning)
    follower=controller.nash_solver
    actual=a.control_from_json(record/'action_000900.json',cfg,ControlAction)
    actual,vsl_expansion=objective.expand_shared_vsl_action(actual,cfg,segment_vsl_func=segment_vsl)
    report['vsl_expansion']=vsl_expansion
    source_token=hashlib.sha256(pickle.dumps(pins,protocol=5)).hexdigest()
    initial=pickle.dumps((cfg,state,actual,forecast),protocol=5)
    controls={'open':actual}
    # No legacy7200 target enters a benchmark: freeze the unchanged response's
    # accepted merge quantity before requesting any alternative owner domain.
    t=time.perf_counter()
    base=ep.evaluate_price_point(state,actual,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
    assert not base.aborted and base.control_area_response['model_constraint_coverage']['complete']
    target_nuf=base.control_area['predicted_ramp_merge']['total_rate_veh_h']
    leader=actual.copy();leader.N_UF_star=target_nuf
    report['fixed_benchmark_nuf_target_veh_h']=target_nuf
    report['baseline_response_sec']=time.perf_counter()-t
    callbacks,context,fingerprint=objective._joint_runtime_callbacks(follower,state,forecast,actual,leader,mapping,pins,
        reference=actual,total_budget=None,directional={},tolerance=1e-7)
    report['actual_move_box']=callbacks['move_box'].entries
    expected=list(csv.DictReader((record/'action_000900.csv').open(encoding='utf-8-sig',newline='')))
    baseline_commands=callbacks['command_evidence'](actual)['ordered_rows']
    # Numeric CSV string spellings may differ; physical rows below are compared
    # in the canonical writer's own typed representation for owner invariance.
    report['recorded_meter_greens_exact']=all(
        float(next(r for r in baseline_commands if r['kind']=='ramp_meter' and r['id']==old['id'])['green_sec'])==float(old['green_sec'])
        for old in expected if old['kind']=='ramp_meter')
    for owner in ('FW_W','FW_E'):
        t=time.perf_counter()
        result=callbacks['neighbor_evidence'](owner,actual,context)
        assert result['complete']
        pure={};coupled=[];vsl=[]
        for candidate in result['candidates']:
            changed=game.assert_owner_transition(callbacks['ownership'],owner,actual,candidate)
            fields={field for field,key in changed}
            if fields=={'ramp_metering'}:
                assert len(changed)==1
                mid=changed[0][1]
                green=candidate.diagnostics['rw_meter_green_'+mid]
                pure.setdefault(mid,[]).append(green)
                if green==8.:controls[mid+'_g8']=candidate
            elif fields=={'ramp_metering','vsl'}:coupled.append(candidate)
            elif fields=={'vsl'}:vsl.append(candidate)
        assert set(pure)=={r for r,o in cfg.network.ramp_to_freeway.items() if o==owner}
        assert all(set(v)=={8.,9.} for v in pure.values())
        if coupled:controls[owner+'_joint_first']=coupled[0]
        report['owners'][owner]={'candidate_count':len(result['candidates']),'pure_meter_greens':pure,
            'pure_vsl_count':len(vsl),'coupled_count':len(coupled),'canonical_command_checks':len(result['command_evidence']),
            'elapsed_sec':time.perf_counter()-t,'provenance':result['provenance']}
        if parity_only:
            tick=time.perf_counter()
            deferred=callbacks['neighbor_evidence'](owner,actual,context,_all_command_evidence=False)
            assert deferred['complete'] and not deferred['command_evidence']
            before=[pickle.dumps(vars(c),protocol=5) for c in result['candidates']]
            after=[pickle.dumps(vars(c),protocol=5) for c in deferred['candidates']]
            assert before==after
            report['owners'][owner]['deferred_parity']={
                'all_ordered_full_actions_exact':True,'eager_native_command_proofs':len(result['command_evidence']),
                'deferred_generation_sec':time.perf_counter()-tick,
                'ordered_action_sha256':[hashlib.sha256(c).hexdigest() for c in before],
                'eager_physical_owner_sha256':[e['owner_physical_sha256'] for e in result['command_evidence']]}
        print(owner,'candidates',len(result['candidates']),flush=True)
    assert pickle.dumps((cfg,state,actual,forecast),protocol=5)==initial
    for name,control in ({} if parity_only else controls).items():
        t=time.perf_counter()
        point=base if name=='open' else ep.evaluate_price_point(state,control,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert not point.aborted and point.control_area_response['model_constraint_coverage']['complete']
        assert pickle.dumps((cfg,state,actual,forecast),protocol=5)==initial
        local=objective.score_shared_owner_point(follower,point,state,control,actual,horizon_steps=3)
        report['responses'][name]={'objective_veh_h':point.objective,'predicted_merge':point.control_area['predicted_ramp_merge'],
            'local_costs':{o:r['cost'] for o,r in local.items()},'physical_commands':ramps.physical_commands(control,cfg),
            'vsl':dict(control.vsl),'elapsed_sec':time.perf_counter()-t,
            'source_action_nuf_field':control.N_UF_star,'source_action_nuf_is_benchmark_target':control.N_UF_star==target_nuf,
            'response_sha256':hashlib.sha256(pickle.dumps(point.control_area_response,protocol=5)).hexdigest()}
        print(name,round(point.objective,6),flush=True)
    report['complete']=True
except Exception:
    report['error']=traceback.format_exc();print(report['error'],flush=True)
finally:
    report['source_changes']=[p for p,h in pins.items() if sha(ROOT/p)!=h]
    report['complete']=report['complete'] and not report['source_changes']
    report['elapsed_sec']=time.perf_counter()-started
    with target.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
sys.exit(0 if report['complete'] else 1)
