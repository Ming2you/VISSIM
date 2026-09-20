"""Check stored ordered-model trials and focused integration contracts."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import check_ordered_relative_response as a

K,e,r,OUT=a.K,a.e,a.r,a.OUT


def close(x,y):
    assert math.isfinite(x) and math.isfinite(y) and abs(x-y)<1e-8,(x,y)


def main():
    result=e.load(OUT/'result.json');initial=e.load(OUT/'initials.json')
    for name,digest in result['source_pins'].items():
        assert hashlib.sha256((r.d.ROOT/name).read_bytes()).hexdigest()==digest,name
    assert not result['qualified'] and not result['production_adopted'] and result['new_native_runs']==0
    spec=importlib.util.spec_from_file_location('restart_archive_for_contracts',OUT/'source_before.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    network=r.d.H/'source_dsd/baseline.inpx'
    assert frozen.native_parameters(network)==r.native_parameters(network)
    source_before=ast.parse((OUT/'source_before.py').read_text())
    source_after=ast.parse(Path(r.__file__).read_text())
    old_body=next(n for n in source_before.body if isinstance(n,ast.FunctionDef) and n.name=='rollout').body
    new_body=next(n for n in source_after.body if isinstance(n,ast.FunctionDef) and n.name=='rollout').body
    # Only the explicit optional dispatch was inserted after the docstring.
    assert [ast.dump(n) for n in old_body]==[ast.dump(n) for n in new_body[:1]+new_body[2:]]
    traces=states_count=vehicle_states=0
    for run in result['runs']:
        if run['status']!='completed':
            assert run['start']==2550 and run['lane'] in (1,3) and 'overlap' in run['reason']
            continue
        states=e.load(OUT/f"{run['start']}_{run['lane']}_{run['mode']}.json")
        before=initial[str(run['start'])][str(run['lane'])]
        assert states['0']==before
        assert set(states)=={str(i) for i in range(31)}
        for t in range(1,31):
            current=states[str(t)];assert set(current)==set(before)
            order=sorted(current,key=lambda i:current[i]['pos'])
            for vid,row in current.items():
                assert row['lane']==before[vid]['lane'] and row['pos']>=before[vid]['pos']
                assert row['v']>=0 and math.isfinite(row['v'])
                vehicle_states+=1
            for back,front in zip(order,order[1:]):
                assert current[front]['pos']-current[front]['length']-current[back]['pos']>=-1e-7
            before=current;states_count+=1
        for horizon,score in run['scores'].items():
            for row in score['rows']:
                prediction=states[horizon][str(row['vehicle'])]
                close(row['speed_error'],prediction['v']-row['actual_speed'])
                close(row['displacement_error'],row['predicted_displacement']-row['actual_displacement'])
                close(row['predicted_displacement'],prediction['pos']-states['0'][str(row['vehicle'])]['pos'])
        traces+=1
    runs=copy.deepcopy(result['runs'])
    for run in runs:
        if 'scores' in run:run['scores']={int(k):v for k,v in run['scores'].items()}
    summary,common=a.summarize(runs);common_summary,_=a.summarize(common)
    assert json.loads(json.dumps(summary))==result['summary']
    assert json.loads(json.dumps(common_summary))==result['common_support']
    params=dict(stand_m=1.5,headway_s=.9,vehicle_by_length={5.:dict(curve=[(0.,3.5),(200.,3.5)],
        deceleration_curve=[(0.,2.75),(200.,2.75)],max_deceleration_curve=[(0.,8.5),(200.,8.5)])})
    car=lambda x,v:dict(pos=x,v=v,desired=120.,length=5.,lane=1)
    free={1:car(0.,120.)}
    trace,_=r.rollout(free,params,1,interaction=dict(law='idm',delta=4.))
    close(trace[1][1]['v'],120.);close(trace[1][1]['pos'],120/3.6)
    for case in (free,{1:car(0.,0.),2:car(5.5,0.)},{1:car(0.,36.),2:car(25.,0.)}):
        assert frozen.rollout(case,params,1)==r.rollout(case,params,1)
    stopped={1:car(0.,0.),2:car(5.5,0.)}
    trace,_=r.rollout(stopped,params,1,interaction=dict(law='idm',delta=4.))
    assert trace[1][1]['pos']>=0 and trace[1][1]['v']>=0
    closing={1:car(0.,36.),2:car(25.,0.)}
    faster={1:car(0.,36.),2:car(25.,72.)}
    slow,_=r.rollout(closing,params,1,interaction=dict(law='idm',delta=4.))
    fast,_=r.rollout(faster,params,1,interaction=dict(law='idm',delta=4.))
    assert slow[1][1]['v']<fast[1][1]['v']
    short={1:car(0.,3.6),2:car(5.1,0.)}
    trace,_=r.rollout(short,params,1,interaction=dict(law='idm',delta=4.))
    assert trace[1][1]['pos']>=0 and trace[1][1]['braking_envelope_exceeded']
    overlaps={1:car(0.,0.),2:car(4.,0.)}
    try:r.rollout(overlaps,params,1,interaction=dict(law='idm',delta=4.))
    except ArithmeticError:pass
    else:raise AssertionError('Overlapping bodies must remain unsupported')
    core=['evaluation/controllers/physical_lane_groups.py','evaluation/controllers/physical_ramp_boundary.py',
        'evaluation/controllers/vissim_stackelberg_adapter.py',
        'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:assert subprocess.check_output(['git','show','a5dcbd3:'+name],cwd=r.d.ROOT)==(r.d.ROOT/name).read_bytes()
    report=dict(passed=True,qualified=False,source_pins=len(result['source_pins']),saved_traces=traces,
        conserved_integer_states=states_count,vehicle_state_checks=vehicle_states,default_body_ast_unchanged=True,
        default_trial_replays_exact=result['default_replays_exact'],native_default_parameters_exact=True,
        focused_contracts=6,core_unchanged_from='a5dcbd3',native_started=False,full_forecasts_recomputed=False,
        previous_goal_turn='progress: exact mixing/response/weight ledger identified within-bin force error',
        current_goal_turn='progress: existing ordered model received relative-speed candidate, NC gate rejected',
        goal_status='active; NOT_QUALIFIED',completed_session='21205 exit0',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    destination=OUT/'verification.json'
    if destination.exists():assert e.load(destination)==report
    else:e.save(destination,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
