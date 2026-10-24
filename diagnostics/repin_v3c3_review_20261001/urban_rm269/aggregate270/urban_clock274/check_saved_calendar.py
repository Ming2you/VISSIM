"""Read one saved state and verify rebase without running the full predictor."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import copy
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def flatten(value,path=()):
    if isinstance(value,dict):
        for key,child in value.items():yield from flatten(child,(*path,key))
    else:yield path,float(value)


def main():
    output=HERE/'saved_calendar.json'
    assert not output.exists(),'Inspect existing evidence before another attempt'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    started=time.perf_counter()
    from evaluation.controllers.multirate_urban_clock import rebase_projection
    from evaluation.controllers import sdmpc_sequence  # saved request class registration
    source=HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle'
    request=pickle.loads(source.read_bytes())
    cfg=request['owned'][0].cfg;state=request['owned'][1]
    original_cfg,original=copy.deepcopy((cfg,state))
    previous=json.loads((HERE.parent/'urban_clock273/plan.json').read_bytes())
    pins=dict(previous['source_pins'])
    for rel,expected in pins.items():assert sha(ROOT/rel)==expected,rel
    for rel in ('aggregate_wout.py','aggregate_route_corridors.py','multirate_urban_clock.py'):
        pins['evaluation/controllers/'+rel]=sha(ROOT/'evaluation/controllers'/rel)
    before_owners={k:copy.deepcopy(getattr(state,k)) for k in
        ('urban_link_storage','urban_movement_queue','ramp_queue')}
    port=state.lane_urban_runtime.port
    report=rebase_projection(cfg,state)
    checks=[];max_error=0.
    def compare_calendar(label,before,after):
        nonlocal max_error
        # Compare all route/lane payloads at every physical10s boundary,
        # including deadlines beyond the450s prediction horizon.
        end=max([state.time_sec,*before.keys(),*(10*k for k in after)])
        for physical in range(int(state.time_sec),int(end)+11,10):
            old=defaultdict(float);new=defaultdict(float)
            for due,value in before.items():
                if due<=physical:
                    for key,n in flatten(value):old[key]+=n
            for tick,value in after.items():
                if tick*10<=physical:
                    for key,n in flatten(value):new[key]+=n
            for key in old.keys()|new.keys():
                err=abs(old[key]-new[key]);max_error=max(max_error,err)
                assert err<1e-9,(label,physical,key,old[key],new[key])
        checks.append(label)
    def nested(label,before,after,depth):
        if depth==0:return compare_calendar(label,before,after)
        assert before.keys()==after.keys(),label
        for key in before:nested(label+'/'+str(key),before[key],after[key],depth-1)
    for name in ('urban_arrival_buffer','urban_storage_release_buffer','urban_inflow_transit_buffer',
                 'offramp_transit_buffer','gate_initial_route_tags','gate_future_route_tags'):
        nested(name,getattr(original,name),getattr(state,name),1)
    for name,depth in (('shared_approach_state',1),('sc2001_corridor_state',2)):
        nested(name,vars(original)[name]['bins'],vars(state)[name]['bins'],depth)
    compare_calendar('local_urban/arrival_tags',original.lane_urban_runtime.arrival_tags,state.lane_urban_runtime.arrival_tags)
    cohort_count=0
    for name in ('route_choice_corridor_state','native_input_route_state','native_input_prehead_state',
                 'known_legsplit_route_state','direct_exit_route_state'):
        before=vars(original)[name]['cohorts'];after=vars(state)[name]['cohorts']
        assert len(before)==len(after)
        for old,new in zip(before,after):
            expected=copy.deepcopy(old)
            for key in ('due','ready'):
                if key in expected:expected[key]=-(-expected[key]//10)
            for key,field in (('lane68','exit_step'),('connector68','ready_step')):
                if key in expected and field in expected[key]:expected[key][field]=-(-expected[key][field]//10)
            assert new==expected,(name,old,new)
            cohort_count+=1
    for name,value in before_owners.items():assert getattr(state,name)==value,name
    assert state.lane_urban_runtime.port is port
    assert state.lane_urban_runtime.port.urban.time==original.lane_urban_runtime.port.urban.time
    assert state.sc1001_approach.queues==original.sc1001_approach.queues
    assert state.sc1001_approach.time==original.sc1001_approach.time
    for name,key in (('known_legsplit_route_state','aggregate_transport'),('route_choice_corridor_state','aggregate_routes')):
        a=vars(original)[name][key];b=vars(state)[name][key]
        assert a.bins.labels==b.bins.labels
        for array in ('future','waiting','pending'):assert (getattr(a.bins,array)==getattr(b.bins,array)).all()
        a.bins.verify();b.bins.verify()
    # Same physical10s aggregate W_out motion under seconds versus tick units.
    # No external admission or whole-network rollout is performed here.
    a=original.known_legsplit_route_state['aggregate_transport']
    b=state.known_legsplit_route_state['aggregate_transport']
    wout_error=0.
    for offset in range(0,60,10):
        a.advance(original,original_cfg,int(original.time_sec+offset))
        b.advance(state,cfg,int((state.time_sec+offset)/10))
        for array in ('future','waiting','pending'):
            aa=getattr(a.bins,array).flat;bb=getattr(b.bins,array).flat
            err=max(abs(x-y) for x,y in zip(aa,bb));wout_error=max(wout_error,float(err))
            assert err<1e-9,(offset,array,err)
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    result=dict(status='complete_reviewed',created_utc=datetime.now(timezone.utc).isoformat(),
        source=str(source),source_sha256=sha(source),source_pins=pins,
        saved_time_sec=original.time_sec,rebase=report,calendar_groups=len(checks),
        max_boundary_prefix_mass_error_veh=max_error,cohorts_checked=cohort_count,
        owner_stocks_unchanged=True,physical_port_alias_preserved=True,
        shared_absolute_ready_times_preserved=True,aggregate_arrays_initially_exact=True,
        wout_component_steps=6,wout_physical_sec=60,wout_max_state_error_veh=wout_error,
        wall_sec=time.perf_counter()-started,native_runs=0,full_rollouts=0,full_sdmpc_selections=0,
        whole_urban10_qualified=False)
    save(output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','source')},ensure_ascii=False))


if __name__=='__main__':main()
