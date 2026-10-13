from copy import deepcopy
from types import SimpleNamespace as NS
import math
import pytest
from evaluation.controllers import route_choice_corridor as rc
from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_order.candidate import advance


def cohort(lane, n, order, target='R'):
    return dict(target=target, vehicles=n, due=0,
                lane68=dict(shares={str(lane):1.}, exit_step=0, order=(0,order)))


def setup(rows, rate=-math.log(.9)):
    cfg=NS(network=NS(known_legsplit_routes=dict(storage='W', local_queue_gate=True,
        lateral_access_rate_per_sec=rate, entry_lane_receiving=dict(ramp='R',
            ramp_lanes={'1':0,'2':1}, road_capacity_veh={str(i):20. for i in range(1,5)}))),
        simulation=NS(T_u_sec=1.))
    state=NS(known_legsplit_route_state=dict(cohorts=rows), urban_storage_release_buffer={})
    return state,cfg


def lane_total(state, lane):
    return sum(c['vehicles']*c['lane68']['shares'].get(str(lane),0.)
               for c in state.known_legsplit_route_state['cohorts'])


def test_same_total_movement_clears_front_blocker():
    front,back,passing=cohort(3,1.,10),cohort(3,9.,50),cohort(3,3.,30,'free')
    passing.update(local68_queue=True,downstream_steps=5)
    s,c=setup([front,back,passing]);old=deepcopy(s)
    rc._known_lateral_advance(old,c,0);advance(s,c,0)
    assert lane_total(s,2)==pytest.approx(lane_total(old,2))
    assert front['lane68']['shares'].get('3',0)==pytest.approx(0.)
    rc._known_local_queue_advance(s,c,dict(requests={}),{},0)
    rc._known_local_queue_advance(old,c,dict(requests={}),{},0)
    assert passing['vehicles']==pytest.approx(0.)
    assert old.known_legsplit_route_state['cohorts'][2]['vehicles']==pytest.approx(2.7)


def test_equal_positions_do_not_depend_on_input_order():
    a,b=cohort(3,2.,10),cohort(3,8.,10);s,c=setup([a,b]);t=deepcopy(s)
    t.known_legsplit_route_state['cohorts'].reverse()
    advance(s,c,0);advance(t,c,0)
    assert a['lane68']['shares']['2']==pytest.approx(.1)
    assert list(reversed(t.known_legsplit_route_state['cohorts']))==s.known_legsplit_route_state['cohorts']


def test_receiver_bound_and_no_two_lane_jump():
    s,c=setup([cohort(2,19.9,1),cohort(3,10.,10),cohort(4,5.,20)],rate=100.)
    advance(s,c,0)
    assert lane_total(s,2)==pytest.approx(20.)
    assert '2' not in s.known_legsplit_route_state['cohorts'][2]['lane68']['shares']
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==pytest.approx(34.9)


def test_full_receiver_cannot_borrow_future_space():
    s,c=setup([cohort(3,20.,1),cohort(4,5.,20)])
    advance(s,c,0)
    assert s.known_legsplit_route_state['cohorts'][1]['lane68']['shares']=={'4':1.}


def test_not_arrived_and_disabled_are_noops():
    s,c=setup([cohort(3,10.,1)]);s.known_legsplit_route_state['cohorts'][0]['due']=1
    before=deepcopy(s);advance(s,c,0)
    assert vars(s)==vars(before)
    c.network.known_legsplit_routes.pop('lateral_access_rate_per_sec');advance(s,c,1)
    assert vars(s)==vars(before)


def test_receiving_derivative_remains_active(monkeypatch):
    from evaluation.controllers.sdmpc_dual import Dual,Trace,MathProxy,primal,derivative
    monkeypatch.setattr(rc,'math',MathProxy())
    s,c=setup([cohort(2,Dual(10.,{0:1.},Trace([.01])),1),cohort(3,10.,2)])
    advance(s,c,0)
    x=s.known_legsplit_route_state['cohorts'][1]['lane68']['shares']['2']
    assert 0<primal(x)<1 and derivative(x)[0]<0
