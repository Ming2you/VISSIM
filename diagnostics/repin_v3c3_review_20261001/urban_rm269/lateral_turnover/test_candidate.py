from copy import deepcopy
import pytest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_order.test_candidate import setup,cohort,lane_total
from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import advance,FIELD
from evaluation.controllers import route_choice_corridor as rc


def test_no_history_matches_old_attempt_exactly():
    s,c=setup([cohort(2,5.,1),cohort(3,4.,2),cohort(4,5.,3)])
    old=deepcopy(s);rc._known_lateral_advance(old,c,0);advance(s,c,0)
    assert s.known_legsplit_route_state==old.known_legsplit_route_state


def test_departure_creates_no_stock_and_moves_one_adjacent_lane_only():
    s,c=setup([cohort(3,4.,1),cohort(4,5.,2)],rate=.001)
    setattr(s,FIELD,dict(step=-1,departed={'2':1.,'3':2.}))
    advance(s,c,0)
    assert lane_total(s,2)==pytest.approx(1.)
    assert s.known_legsplit_route_state['cohorts'][1]['lane68']['shares']==pytest.approx({'3':.4,'4':.6})
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==9.
    assert getattr(s,FIELD)['departed']==pytest.approx({'3':1.,'4':2.})


def test_no_room_blocks_past_departure_and_does_not_borrow_current_outflow():
    s,c=setup([cohort(2,20.,1),cohort(3,20.,2),cohort(4,5.,3)])
    setattr(s,FIELD,dict(step=-1,departed={'2':5.,'3':5.}))
    old=deepcopy(s.known_legsplit_route_state);advance(s,c,0)
    assert old==s.known_legsplit_route_state


def test_expired_history_is_rejected_and_no_opportunity_accumulation():
    s,c=setup([cohort(3,4.,1)]);setattr(s,FIELD,dict(step=-2,departed={'2':10.}))
    with pytest.raises(AssertionError,match='old departure'):advance(s,c,0)
    setattr(s,FIELD,dict(step=-1,departed={'2':10.}));advance(s,c,0)
    assert lane_total(s,2)==pytest.approx(4.)
    assert '2' not in getattr(s,FIELD)['departed']


def test_departure_sensitivity_propagates(monkeypatch):
    from evaluation.controllers.sdmpc_dual import Dual,Trace,MathProxy,primal,derivative
    monkeypatch.setattr(rc,'math',MathProxy())
    s,c=setup([cohort(3,4.,1)],rate=.001)
    setattr(s,FIELD,dict(step=-1,departed={'2':Dual(1.,{0:1.},Trace([.01]))}))
    advance(s,c,0);n=lane_total(s,2)
    assert primal(n)==pytest.approx(1.) and derivative(n)[0]==pytest.approx(1.)
