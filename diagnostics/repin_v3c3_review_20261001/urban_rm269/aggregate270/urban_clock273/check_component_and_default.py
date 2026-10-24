"""One saved-state component comparison and one unchanged-clock regression."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import copy
import hashlib
import json
import pickle
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    receipt=HERE/'execution.json'
    assert not receipt.exists(),'Inspect the existing attempt; no automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    plan=json.loads((M/'plan.json').read_bytes())
    changed='evaluation/controllers/lane_offramp_runtime.py'
    assert sha(HERE/'lane_offramp_before.py')==plan['source_pins'][changed]
    pins=dict(plan['source_pins']);pins[changed]=sha(ROOT/changed)
    pins['evaluation/controllers/multirate_urban_boundary.py']=sha(ROOT/'evaluation/controllers/multirate_urban_boundary.py')
    for p,h in pins.items():assert sha(ROOT/p)==h,p
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        source_pins=pins,full_forecast_limit=1,full_sdmpc_selections=0,native_runs=0)
    save(receipt,record)
    from evaluation.controllers import sdmpc_sequence as seq
    from evaluation.controllers.multirate_urban_boundary import advance_shared_interval,signal_intervals
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    from src.models import urban_queue_model as uqm
    request=pickle.loads((M/'macro_hold_ad_v3_request.pickle').read_bytes())
    cfg,state=request['owned'][:2];cfg=cfg.cfg
    action=seq.actions(request['action'],3)[0]
    base=state.sc1001_approach
    specs={g:cfg.network.urban_movements[base.city_movements[row['movements'][0]]] for g,row in base.lanes.items()}
    fractions=signal_intervals(action,cfg,specs)
    room={target:uqm._effective_available_space(state,cfg,cfg.network.urban_movements[m]['receiving_link'])
          for target,m in base.city_movements.items()}
    def evaluate(coarse,room):
        local=copy.deepcopy(base);start=local.time;before=local.residence_veh_h
        if coarse:
            rows=advance_shared_interval(local,start,10,fractions,room)
            steps=local.last_interval_segments
        else:
            rows=[];left=dict(room);steps=10
            for second in range(start,start+10):
                out=local.advance(second,fractions(second,1),left)
                for r in out:left[r['movement']]-=r['vehicles']
                rows.extend(out)
        local.assert_conserved()
        grouped={}
        for row in rows:
            key=':'.join(row[k] for k in ('lane','source','movement'))
            grouped[key]=grouped.get(key,0.)+row['vehicles']
        return dict(departed_veh=sum(r['vehicles'] for r in rows),end_stock_veh=local.stock(),
            residence_increment_veh_h=local.residence_veh_h-before,segments=steps,
            departures_by_lane_source_movement=grouped,remaining_room={k:v-sum(r['vehicles'] for r in rows if r['movement']==k) for k,v in room.items()})
    component=dict(scope='Actual saved2400 initial approach/command,10s,no new arrivals,one fixed downstream reservation; component comparison only',
        state_sec=state.time_sec,initial_stock_veh=base.stock(),receiving_veh=room,
        fine=evaluate(False,room),coarse=evaluate(True,room))
    assert all(v>=-1e-7 for v in component['coarse']['remaining_room'].values())
    save(HERE/'component.json',component)
    request['surrogate_evaluation']='scalar'
    for path,expected in request['bootstrap']['runtime_sources'].items():
        p=Path(path);actual=sha(p)
        if actual!=expected:
            assert actual==pins[p.relative_to(ROOT).as_posix()],path
            request['bootstrap']['runtime_sources'][path]=actual
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    src=HERE/'default_request.pickle';dst=HERE/'default_result.pickle'
    src.write_bytes(pickle.dumps(request,protocol=5))
    started=time.perf_counter()
    with (HERE/'default_stdout.log').open('w') as out,(HERE/'default_stderr.log').open('w') as err:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1'],
            cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        record.update(stage='unchanged_clock_scalar_regression',child_pid=child.pid);save(receipt,record)
        code=child.wait()
    record.update(exit_code=code,wall_sec=time.perf_counter()-started,
        source_pins_unchanged=all(sha(ROOT/p)==h for p,h in pins.items()))
    if code:
        record['status']='failed_preserved';save(receipt,record);return code
    original=pickle.loads((M/'macro_hold_v2_result.pickle').read_bytes())
    current=pickle.loads(dst.read_bytes())
    errors={key:max(abs(a-b) for a,b in zip(current[key],original[key])) for key in ('costs','resources')}
    a,b=[r['surrogate_prediction']['central_physical'] for r in (current,original)]
    assert a['names']==b['names']
    errors['central']=max(abs(x-y) for x,y in zip(a['values'],b['values']))
    record.update(max_absolute_errors=errors,central_states=len(a['names']))
    assert max(errors.values())<1e-7,errors
    p=current['surrogate_prediction']
    assert p['conditional_model_feasibility_witness'] and p['model_constraint_coverage']['complete']
    assert p['resource_summary']['max_exceedance_veh']<1e-7
    record.update(status='complete_reviewed',ended_utc=datetime.now(timezone.utc).isoformat())
    save(receipt,record)
    print(json.dumps(dict(status=record['status'],max_absolute_errors=errors,component=component),ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
