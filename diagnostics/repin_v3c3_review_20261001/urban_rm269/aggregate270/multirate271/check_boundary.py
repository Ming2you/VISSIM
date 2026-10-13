"""Real saved-state eight-ramp boundary checks; not a coupled rollout claim."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import copy,hashlib,json,pickle,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];BASE=HERE.parent/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as sequence
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers.sdmpc_continuous import ramp_services
    assert not (HERE/'boundary_result.json').exists(),'No duplicate component check'
    source=pickle.loads((BASE/'new_hold.pickle').read_bytes())
    follower,initial,_,forecast=source['owned']
    for name,value in source['runtime'].items():setattr(adapter,name,copy.deepcopy(value))
    install_worker_runtime(adapter,follower.cfg,source['bootstrap']['state_json'],source['bootstrap']['detector_mapping'])
    pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
    rows={}
    for name in ('new_hold','new_release'):
        request=pickle.loads((BASE/(name+'.pickle')).read_bytes())
        action=sequence.first_action(request['action'])
        for dt in (1,5):
            state=copy.deepcopy(initial);full_cfg=copy.deepcopy(follower.cfg)
            runtime=state.lane_ramp_runtime;freeway=state.lane_freeway_runtime
            full_cfg.simulation.T_f=dt
            for cfg in freeway.configs.values():cfg.simulation.T_f=dt
            before={r:b.snapshot() for r,b in runtime.buffers.items()}
            merges={r:0. for r in runtime.buffers};head={r:0. for r in runtime.buffers}
            ttt={r:0. for r in runtime.buffers};max_error=0.;started=time.perf_counter();steps=0
            for offset in range(0,150,dt):
                state.time_sec=initial.time_sec+offset;freeway.time_sec=state.time_sec
                release,_,receipts=runtime.advance(state,action,forecast[0],freeway,
                    service=ramp_services(action,full_cfg,runtime.cycle_sec))
                runtime.finish(state)
                for r,row in receipts.items():
                    merges[r]+=row['accepted_merge_veh'];head[r]+=row['head_service_veh'];ttt[r]+=row['connector_ttt_veh_h']
                    assert abs(release[r]*dt/3600.-row['accepted_merge_veh'])<1e-9
                    assert row['accepted_merge_veh']<=row['eligible_merge_veh']+1e-7
                    if dt==5:assert row['local_step_sec']==5 and row['local_receipts']==[]
                    max_error=max(max_error,abs(before[r]['connector_veh']-runtime.buffers[r].snapshot()['connector_veh']-merges[r]))
                steps+=1
            assert max_error<1e-7
            rows[name+':'+str(dt)]=dict(steps=steps,wall_sec=time.perf_counter()-started,merges=merges,head=head,
                ramp_ttt_veh_h=ttt,max_conservation_error_veh=max_error,
                final_stock={r:b.snapshot()['connector_veh'] for r,b in runtime.buffers.items()},
                causal_timestamps=runtime.buffers['RM_C10681']._lane_buffers[0]._spatial_entry.get('departure_times'))
    delta={str(dt):dict(merge10681=rows['new_release:'+str(dt)]['merges']['RM_C10681']-rows['new_hold:'+str(dt)]['merges']['RM_C10681'],
        ramp_ttt10681=rows['new_release:'+str(dt)]['ramp_ttt_veh_h']['RM_C10681']-rows['new_hold:'+str(dt)]['ramp_ttt_veh_h']['RM_C10681']) for dt in (1,5)}
    for p,h in pins.items():assert sha(Path(p))==h,p
    result=dict(status='boundary_component_only_complete',rows=rows,deltas=delta,source_pins=pins,
        scope='Saved2400 initial state, eight physical ramps,150s closed initial-stock discharge. FWstate held and no urban arrivals; same continuous cycle-mean head service as SDMPC surrogate. Not450s coupled prediction, urban spillback,Omega gain, or native/full decision speed qualification.',
        new_updates='At5s30actualcoarse updates, not150hidden1s iterations. Physical lane source/capacity retained; separate end-of-step head departure andmerge; timed causal entry history.')
    save(HERE/'boundary_result.json',result)
    print(json.dumps(dict(deltas=delta,times={k:r['wall_sec'] for k,r in rows.items()},max_conservation_error=max(r['max_conservation_error_veh'] for r in rows.values())),ensure_ascii=False))


if __name__=='__main__':main()
