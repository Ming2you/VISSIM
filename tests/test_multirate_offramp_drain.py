"""Finite10s outlet service and endpoint-stamped downstream ownership."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from src.models.state import SimulationConfig
from src.models import urban_queue_model as uqm
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
from evaluation.controllers.multirate_urban_boundary import release_delayed_interval
from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime,SharedSignalApproach
from evaluation.controllers.lane_urban_runtime import LaneUrbanRuntime
from evaluation.controllers.control_area_objective import ModelAreaLedger


def port(ready=0.,pending=()):
    p=DelayedPort(20.,100.,36.,[],100.,interval_service=True)
    p.ready=ready;p.pending=[list(row) for row in pending];p.initial=p.stock
    return p


def test_late_arrival_keeps_full_outlet_rate_until_finite_room_is_used():
    p=port(pending=[(109.,2.)])
    assert release_delayed_interval(p,100,10,3600.,1.)==pytest.approx(1.)
    assert p.stock==pytest.approx(1.) and p.last_time_s==110
    assert p.last_coarse_drain_segments==1
    assert p.residence_veh_h==pytest.approx(19.5/3600.)


def test_full_room_budget_cannot_be_reused_after_later_arrival():
    p=port(ready=4.,pending=[(105.,6.)]);before=deepcopy(p)
    actual=release_delayed_interval(p,100,10,3600.,3.)
    remaining=3.;fine=0.
    for t in range(100,110):
        n=before.release(t,1,3600. if remaining>0 else 0.)
        fine+=n;remaining-=n
    assert actual==fine==3. and p.stock==7.
    assert p.residence_veh_h==pytest.approx(before.residence_veh_h)
    assert p.last_coarse_drain_segments==2


def test_zero_receiving_does_not_erase_travelling_stock_or_bank_service():
    p=port(ready=2.,pending=[(105.,3.)])
    assert release_delayed_interval(p,100,10,3600.,0.)==0.
    assert p.stock==5. and p.ready==5. and p.residence_veh_h==pytest.approx(50/3600.)
    assert release_delayed_interval(p,110,10,3600.,2.)==2.
    assert p.stock==3.


def test_late_event_and_contiguous_clock_validation_are_pre_mutation():
    p=port(ready=1.);before=deepcopy(vars(p))
    with pytest.raises(ValueError):release_delayed_interval(p,101,10,3600.,1.)
    assert vars(p)==before


def fixture(monkeypatch,dt=10,head_at_end=True):
    names=('10481','10491','10638','10483','10479','10682','10645')
    ports={k:port(ready=4.) for k in names}
    shared=SharedSignalApproach(
        {'1':dict(capacity_veh=10.,service_veh_h=3600.,movements=['T'])},
        {k:[dict(lane='1',movement='T',share=1.,delay_sec=2)] for k in names[:2]},[],
        110 if dt==10 and head_at_end else 100)
    shared.storage='shared';shared.city_movements={'T':'mT'}
    descriptions={k:dict(storage='off_'+k,group='G_'+k,connector=int(k),to_link=1,
        lanes=1,direct=k not in names[:3],local_upstream=k=='10638',target='down',
        drain_service_veh_h=3600.) for k in names}
    descriptions['10643']=dict(storage='off_10643')
    runtime=LaneOfframpRuntime(ports,descriptions,NS(lanes=[]),{**{k:True for k in names},'1':True})
    capacities={**{'off_'+k:20. for k in (*names,'10643')},'shared':10.,'origin':20.,'down':20.}
    stock={k:4. if k.startswith('off_') and k!='off_10643' else 17. if k=='down' else 0. for k in capacities}
    arrivals=[]
    local=NS(origin='origin',schedule_upstream=lambda state,cfg,step,n,**kw:arrivals.append((step,n,kw)))
    state=NS(time_sec=100,urban_link_storage={k:capacities[k]-n for k,n in stock.items()},
        urban_arrival_buffer={},urban_storage_release_buffer={},lane_urban_runtime=local,
        sc1001_approach=shared,_control_area_ledger=ModelAreaLedger(
            {'storage:'+k:{'inside':n,'outside':0.} for k,n in stock.items()}))
    cfg=NS(simulation=SimulationConfig(T_u=dt,T_f=5,control_interval=150),
        network=NS(urban_link_storage_veh=capacities,multirate_urban_clock_sec=10,
            movement_capacity_veh_h=3600.,urban_movements={'mT':{'exit':'east'}}))
    monkeypatch.setattr(uqm,'_effective_available_space',lambda state,cfg,key:state.urban_link_storage[key])
    monkeypatch.setattr(uqm,'_link_delay_steps',lambda *a:2)
    return runtime,state,cfg,arrivals


def test_seven_port_drain_uses_one_receiver_and_endpoint_arrival_tags(monkeypatch):
    runtime,state,cfg,arrivals=fixture(monkeypatch)
    out=runtime.drain(state,None,cfg,10,{'down':[]})
    assert sum(out.values())==pytest.approx(15.)
    assert sum(p.stock for p in runtime.ports.values())==pytest.approx(13.)
    assert state.urban_link_storage['down']==0.
    assert state.sc1001_approach.stock()==8.
    assert all(p[0]==112 for p in state.sc1001_approach.queues['1'])
    assert arrivals==[(11,4.,{'entry':'off10638'})]
    assert state.urban_arrival_buffer['down']=={13:3.}
    assert state.urban_storage_release_buffer['down']=={13:3.}
    state._control_area_ledger.assert_stocks({
        'storage:'+k:cap-state.urban_link_storage[k] for k,cap in cfg.network.urban_link_storage_veh.items()})
    with pytest.raises(ValueError,match='Noncontiguous'):runtime.drain(state,None,cfg,10,{})


def test_old_one_second_drain_retains_start_time_receipts(monkeypatch):
    runtime,state,cfg,arrivals=fixture(monkeypatch,dt=1)
    out=runtime.drain(state,None,cfg,100,{'down':[]})
    assert sum(out.values())==6.
    assert arrivals==[(100,1.,{'entry':'off10638'})]
    assert all(p[0]==102 for p in state.sc1001_approach.queues['1'])
    assert state.urban_arrival_buffer['down']=={102:3.}


def test_coarse_drain_requires_old_shared_head_to_finish_first(monkeypatch):
    runtime,state,cfg,_=fixture(monkeypatch,head_at_end=False)
    before={k:deepcopy(vars(p)) for k,p in runtime.ports.items()}
    with pytest.raises(ValueError,match='shared head'):runtime.drain(state,None,cfg,10,{})
    assert before=={k:vars(p) for k,p in runtime.ports.items()}


def test_local_upstream_distance_is_converted_to_urban_ticks():
    local=NS(future_shares={'off10638':{'M':1.}},entry_paths={'off10638':70.},
        port=NS(urban=NS(speed=10.,continuation=True)),exits_by_movement={'M':1},arrival_tags={},origin='origin')
    state=NS(urban_arrival_buffer={},urban_storage_release_buffer={})
    cfg=NS(simulation=SimulationConfig(T_u=10,T_f=5,control_interval=150))
    due=LaneUrbanRuntime.schedule_upstream(local,state,cfg,11,2.,entry='off10638')
    assert due==12 and local.arrival_tags[12]=={('M',False):2.}
    assert state.urban_arrival_buffer==state.urban_storage_release_buffer=={'origin':{12:2.}}


@pytest.mark.parametrize("dt", [5, 10])
def test_positive_room_below_clock_resolution_keeps_stock_and_advances(dt):
    p=DelayedPort(20.,100.,36.,[],4340.,interval_service=True)
    p.ready=3.;p.pending=[[4340.+dt,2.]];p.initial=p.stock
    assert release_delayed_interval(p,4340.,dt,1400.,5.684341886080802e-14)==0.
    assert p.stock==5. and p.ready==5. and p.last_time_s==4340.+dt
    assert p.residence_veh_h==pytest.approx(5.*dt/3600.)
    # Tiny room was not erased from the stock or saved as future service.
    assert release_delayed_interval(p,4340.+dt,dt,1400.,1.)==pytest.approx(1.)
    assert p.stock==pytest.approx(4.)
