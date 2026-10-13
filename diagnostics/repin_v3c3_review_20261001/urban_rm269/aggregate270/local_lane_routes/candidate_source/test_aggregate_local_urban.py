from collections import Counter
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import aggregate_local_urban as a
from evaluation.controllers.physical_urban_transport import UrbanTransport, FIFO


def fixture():
    u = UrbanTransport.__new__(UrbanTransport)
    u.program = NS(state_at=lambda *args,**kwargs:'GREEN')
    u.offset=0;u.time=0;u.speed=1.;u.wave=1.;u.capacity_rate=1.
    u.lateral_access=False;u.continuation=True;u.exchange_rates={}
    u.edges={71:[0.,2.,4.,6.,8.]}
    u.exits={10634:dict(lanes=[1,2,3],position_m=8.),10635:dict(lanes=[4,5],position_m=8.),10642:dict(lanes=[1],position_m=4.)}
    u.fallback_exits=set(u.exits);u.unrouted_labels=set()
    u.cells={(71,lane,cell):FIFO() for lane in range(1,6) for cell in range(4)}
    u.cap={k:2. for k in u.cells};u.dx={k:2. for k in u.cells}
    u.initial=Counter();u.admitted=Counter();u.departed=Counter()
    u.movements=Counter();u.blocked_seconds=Counter();u.vehicle_seconds=0.;u.checks=0
    cfg=NS(network=NS(),simulation=NS(T_u_sec=1,T_f_sec=1))
    state=NS(lane_urban_runtime=NS(port=NS(urban=u)))
    return u,cfg,state


def enable(u,cfg,state):
    u.initial=u.counts()
    return a.configure(cfg,{'urban':{'local_lane_route_aggregate':True}},state)


def test_absent_option_is_noop():
    u,cfg,state=fixture()
    assert a.configure(cfg,{},state)=={}
    assert not hasattr(u,'route_aggregate') and not hasattr(cfg.network,'local_lane_route_aggregate')


def test_projection_preserves_destination_lane_and_continuation_not_vehicle_id():
    u,cfg,state=fixture();key=(71,2,0)
    u.cells[key]=FIFO([((10634,1),.4),((10634,2),.6),((None,3),.3),((None,4),.2)])
    u.unrouted_labels={(None,3)};enable(u,cfg,state)
    assert len(u.cells[key].q)==3 and u.cells[key].stock==pytest.approx(1.5)
    assert u.cells[key].counts()[(10634,'aggregate_routed')]==1.
    assert a.label(u,(None,3))==(None,'aggregate_unrouted')
    assert a.label(u,(None,4))==(None,'aggregate_routed')
    u.check()


def test_external_admits_original_prefix_and_waits_before_forward_movement():
    u,cfg,state=fixture();enable(u,cfg,state)
    q=FIFO([((10634,91),.6),((10635,92),.8)])
    got=u.step({'off:0':((71,2,0),q)},exit_receiving={d:10. for d in u.exits})
    assert got['off:0']==[((10634,91),.6),((10635,92),.4)]
    assert q.stock==pytest.approx(.4)
    assert u.cells[(71,2,0)].stock==1. and u.cells[(71,2,1)].stock==0.
    assert {x[0] for x in u.last_transfers[0][2]}=={(10634,91),(10635,92)}


def test_blocked_class_cannot_be_bypassed_inside_same_cell():
    u,cfg,state=fixture();key=(71,1,1)
    u.cells[key]=FIFO([((10634,1),1.),((10642,2),1.)]);enable(u,cfg,state)
    u.step({},exit_receiving={10634:10.,10635:10.,10642:0.})
    assert u.cells[key].stock==2. and u.cells[(71,1,2)].stock==0.
    assert sum(u.departed.values())==0.


def test_two_external_sources_share_room_proportionally():
    u,cfg,state=fixture();enable(u,cfg,state)
    got=u.step({'one':((71,2,0),FIFO([((10634,1),2.)])),
                'two':((71,2,0),FIFO([((10634,2),2.)]))})
    assert sum(n for _,n in got['one'])==.5
    assert sum(n for _,n in got['two'])==.5
    assert u.cells[(71,2,0)].stock==1.


def test_lateral_and_forward_share_old_receiving_without_swap_space():
    u,cfg,state=fixture();u.lateral_access=True
    u.cells[(71,4,3)]=FIFO([((10634,1),2.)])
    u.cells[(71,3,2)]=FIFO([((10634,2),2.)])
    u.cells[(71,3,3)]=FIFO([((10634,3),1.)]);enable(u,cfg,state)
    u.step({},exit_receiving={d:10. for d in u.exits})
    into=sum(n for source,target,packets in u.last_transfers if target==(71,3,3) for _,n in packets)
    assert into<=.5+1e-12
    assert all(q.stock<=u.cap[k]+1e-12 for k,q in u.cells.items())
    u.check()


def test_continuous_signal_capacity_shared_by_classes():
    u,cfg,state=fixture();u.program.service_fraction_at=lambda *args,**kwargs:.2
    u.cells[(71,2,3)]=FIFO([((10634,1),1.),((None,2),1.)]);enable(u,cfg,state)
    u.step({},exit_receiving={d:10. for d in u.exits})
    assert sum(u.departed.values())==pytest.approx(.2)


def test_repeated_exchange_conserves_class_stock_and_copy_is_independent():
    u,cfg,state=fixture();u.lateral_access=True
    u.cells[(71,4,0)]=FIFO([((10634,1),1.),((10635,2),1.)]);enable(u,cfg,state)
    clone=deepcopy(u)
    for _ in range(60):u.step({},exit_receiving={d:.25 for d in u.exits})
    u.check();assert clone.time==0 and clone.cells[(71,4,0)].stock==2.
    assert sum(u.counts().values())+sum(u.departed.values())==pytest.approx(2.)


def test_unsupported_options_rejected():
    u,cfg,state=fixture();cfg.network.sdmpc_distance_reward={'enabled':True}
    with pytest.raises(ValueError,match='distance accounting'):enable(u,cfg,state)
