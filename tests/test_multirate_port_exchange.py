from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers.physical_urban_transport import CumulativeLane
from evaluation.controllers.lane_coupling import split_10643,lane_amounts_10643
from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime


def lane():return CumulativeLane(capacity=10.,length=60.,speed=36.,vehicles=[],start=100.,wave=3.)


def test_coarse_port_keeps_travel_delay_and_timestamp_history():
    p=lane();assert p.release(100.,5.,3600.)==0.
    p.receiving(5.);p.accept(105.,1.)
    assert p.release(105.,5.,3600.)==0. # 6s physical travel from admission at105
    assert p.release(110.,5.,3600.)==1.
    assert p.departure_times==[0,5.,10.,15.] and p.stock==0.
    assert p.residence_veh_h==pytest.approx(7.5/3600.)


def test_no_service_credit_and_no_duplicate_admission_budget():
    p=lane();p.release(100.,5.,0.)
    room=p.receiving(5.);p.accept(105.,room)
    assert p.receiving(5.)<1e-10
    with pytest.raises(ArithmeticError):p.accept(105.,.1)
    assert p.release(105.,5.,0.)==0.
    assert p.stock==pytest.approx(room)


def test_default1s_port_state_keeps_legacy_representation():
    p=lane();copy=deepcopy(p)
    assert p.release(100.,1.,3600.)==copy.release(100.,1.,3600.)
    assert vars(p).keys()==vars(copy).keys() and not hasattr(p,'departure_times')
    assert p.departure_history==[0.,0.]


def test_rate_to_mass_conversion_respects5s_and_physical_lane_rooms():
    spec=dict(mode='observed_lane_shares_held',shares=[.8,.2])
    cap=[360.,720.,0.]
    assert split_10643(1.,cap,spec,duration_sec=5.)==pytest.approx([.5,.5])
    with pytest.raises(ArithmeticError):split_10643(1.6,cap,spec,duration_sec=5.)
    fw=NS(lanes={});net=NS(lane_plant_10643_lane_split=spec)
    assert lane_amounts_10643(fw,{'10643':720.},{'10643':cap},net,duration_sec=5.)==pytest.approx([.5,.5])


def test_actual_landing_debits_the_same_five_second_mass_once(monkeypatch):
    from evaluation.controllers import control_area_objective as accounting
    transfers=[];visits=[]
    monkeypatch.setattr(accounting,'get_ledger',lambda state:NS(captures_response=False,
        complete_constraint_coverage=lambda name:visits.append(name)))
    monkeypatch.setattr(accounting,'emit_transfer',lambda state,cfg,source,target,n,**kw:transfers.append((source,target,n)))
    packets=[];local=NS(lanes=[lane(),lane()],admit=lambda index,n:packets.append((index,n)))
    runtime=LaneOfframpRuntime({}, {'10643':dict(storage='off',road='FW_E',connector=10643)}, local,{'10643':True})
    state=NS(urban_link_storage={'off':20.});cfg=NS(network=NS(urban_link_storage_veh={'off':20.}))
    for p in local.lanes:p.release(100.,5.,0.)
    caps,groups=runtime.capacities(state,cfg,duration_sec=5.)
    assert caps['10643']*5/3600.==pytest.approx(sum(p.receiving(5.) for p in local.lanes))
    got=runtime.land(state,cfg,105.,{'10643':720.},{'10643':[.5,.5]},duration_sec=5.)
    assert got==1. and state.urban_link_storage['off']==19.
    assert sum(p.stock for p in local.lanes)==1. and sum(n for _,n in packets)==1.
    assert transfers==[('freeway:FW_E','storage:off',1.)]
    assert visits==['offramp_landing']


def test_too_short_port_rejects_large_clock_without_advancing():
    p=CumulativeLane(capacity=1.,length=6.,speed=36.,vehicles=[],start=100.,wave=3.)
    with pytest.raises(ValueError,match='wave lag'):p.release(100.,5.,3600.)
    assert p.time==100. and p.departure_history==[0.]
