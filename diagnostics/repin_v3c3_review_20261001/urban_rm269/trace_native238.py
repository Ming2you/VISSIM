"""Capture current10681 per-lane receipts on two already-qualified commands.

Only instrumentation. Compare outputs with the completed uninstrumented pair;
no native run, tuning, optimizer, future-observation input or production edits.
"""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
import argparse,copy,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'component10681_v2'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def prepare():
    assert not OUT.exists()
    plan=read(HERE/'native238_validation/plan.json')
    for p,h in plan['source_pins'].items():assert sha(Path(p))==h,p
    OUT.mkdir()
    # Preserve the parent receipt verbatim; this is a separate trace budget.
    plan.update(status='prepared_current_receipts',budget=dict(predictions=2,conditional_local_replays_max=4,
        native_runs=0,optimizer_calls=0,coefficient_fits=0),
        purpose='Capture current per-lane head/merge/arrival receipts; verify against completed pair before conditional diagnosis')
    plan['parent_validation_consumed']=plan.pop('consumed',{})
    plan['consumed']=dict(predictions=0,conditional_replays=0,native_runs=0)
    plan['trace_repair']=dict(previous='component10681',previous_rollouts=1,
        reason='Read closing ledger inside Omega wrapper instead of its not-yet-attached result attributes',
        production_change=False)
    for p in (Path(__file__),HERE/'native238_validation/candidate_config.json',
              HERE/'native238_validation/candidate_native_command/summary.json'):
        plan['source_pins'][str(p)]=sha(p)
    save(OUT/'plan.json',plan)
    save(OUT/'candidate_config.json',read(HERE/'native238_validation/candidate_config.json'))
    print('Prepared two unchanged forecasts and at most four local component diagnoses')

def run():
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    spec=importlib.util.spec_from_file_location('pair_driver',HERE/'validate_native238.py')
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    driver.DEST=OUT
    from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    original=endpoint.evaluate_price_point
    prior=read(HERE/'native238_validation/candidate_native_command/summary.json')['results']
    calls=[]
    def traced(state,action,forecast,owners,spec,*args,**kwargs):
        assert state.time_sec==4650 and spec.depth_override==3
        arm='hold' if action.diagnostics['rw_meter_green_RM_C10681']==0 else 'selected'
        assert arm not in calls and len(calls)<2;calls.append(arm)
        buffer=state.lane_ramp_runtime.buffers['RM_C10681']
        metadata,stock=copy.deepcopy(buffer.metadata()),copy.deepcopy(buffer.snapshot())
        receipts=[]
        advance=LaneResolvedRampBoundary.advance_local_interval
        def observe(current,*a,**kw):
            result=advance(current,*a,**kw)
            if current.connector_id=='10681':
                assert not a
                receipts.append(dict(arguments=copy.deepcopy(kw),receipt=copy.deepcopy(result)))
            return result
        with patch.object(LaneResolvedRampBoundary,'advance_local_interval',observe):
            point=original(state,action,forecast,owners,spec,*args,**kwargs)
        assert not point.aborted and len(receipts)==450
        # This hook runs inside the Omega wrapper. Its final public result fields
        # are attached after we return, but the same closing ledger is complete.
        closing=get_ledger(point.states[-1])
        response=closing.response()
        merge=sum(r['receipt']['accepted_merge_veh'] for r in receipts)
        assert abs(closing.metrics.ttt_veh_h-prior[arm]['omega_ttt_veh_h'])<1e-8
        assert abs(merge-prior[arm]['predicted_ramp_merge']['accepted_vehicles_by_ramp']['RM_C10681'])<1e-8
        data=dict(ramp='RM_C10681',start_sec=4650,end_sec=5100,initial_buffer=metadata,initial_stock=stock,
            final_stock=point.states[-1].lane_ramp_runtime.buffers['RM_C10681'].snapshot(),
            lane_interval_receipts=receipts,
            transfers=[r for r in response['transfers'] if any('RM_C10681' in (r.get(k) or '') for k in ('source','target'))],
            head_service_by_green=spec.cfg.network.physical_ramp_branches['ramps']['RM_C10681']['service_by_green_veh_h'],
            future_observation_inputs=False,original_objective_exact=True,original_merge_exact=True)
        with gzip.open(OUT/(arm+'_trace.json.gz'),'wt',encoding='utf8') as f:json.dump(data,f,allow_nan=False)
        print('TRACED',arm,'head',sum(r['receipt']['head_service_veh'] for r in receipts),'merge',merge,flush=True)
        return point
    endpoint.evaluate_price_point=traced
    driver.run('candidate')
    assert calls==['hold','selected']
    save(OUT/'trace_completion.json',dict(status='complete',forecasts=2,outputs_equal_to_prior=True,native_runs=0))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args()
    if args.prepare:prepare()
    else:run()
