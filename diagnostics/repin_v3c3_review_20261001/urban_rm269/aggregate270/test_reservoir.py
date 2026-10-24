import pytest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.reservoir import LaneTurnReservoir


def make():
    return LaneTurnReservoir({'1':10.,'2':10.}, [('1','ramp'),('1','through'),('2','through')], 0, 8)


def test_transit_uses_storage_without_becoming_a_ready_queue():
    r=make();r.seed('1','ramp',10.,3)
    assert r.receive(2.,{('1','ramp'):1.},4)==0.
    for _ in range(3):
        assert sum(r.step({'1':2.,'2':2.},{'ramp':2.,'through':2.}).values())==0.
    assert sum(r.step({'1':2.,'2':2.},{'ramp':2.,'through':2.}).values())==2.
    assert r.stock()==8.


def test_ramp_blockage_reduces_its_lane_not_an_independent_through_lane():
    r=make();r.seed('1','ramp',2.,0);r.seed('1','through',2.,0);r.seed('2','through',2.,0)
    out=r.step({'1':2.,'2':2.},{'ramp':0.,'through':10.})
    assert out=={('1','ramp'):0.,('1','through'):0.,('2','through'):2.}
    assert r.stock('1')==4.


def test_shared_receiving_is_not_given_in_full_to_each_lane():
    r=make();r.seed('1','through',4.,0);r.seed('2','through',4.,0)
    out=r.step({'1':2.,'2':2.},{'ramp':0.,'through':1.})
    assert out[('1','through')]==out[('2','through')]==.5
    assert r.stock()==7.


def test_empty_blocked_turn_does_not_stop_present_through_traffic():
    r=make();r.seed('1','through',2.,0)
    assert r.step({'1':2.,'2':2.},{'ramp':0.,'through':4.})[('1','through')]==2.


def test_tail_arrivals_are_conserved_without_early_discharge():
    r=make();r.seed('1','ramp',3.,100)
    for _ in range(8):r.step({'1':2.,'2':2.},{'ramp':10.,'through':10.})
    assert r.stock()==3. and r.exited==0.
    r.bins.verify()


def test_more_ramp_space_increases_accepted_flow_and_frees_upstream_storage():
    totals=[]
    for ramp_space in (0.,2.):
        r=make();r.seed('1','ramp',10.,0)
        out=r.step({'1':2.,'2':2.},{'ramp':ramp_space,'through':10.})
        admitted=r.receive(3.,{('1','ramp'):1.},2)
        totals.append((out[('1','ramp')],admitted,r.residence_veh_h))
    assert totals[1][0]>totals[0][0] and totals[1][1]>totals[0][1]
    assert totals[1][2]<totals[0][2]


def test_state_size_does_not_grow_when_arrivals_are_fragmented():
    a=make();b=make()
    a.seed('1','ramp',1.,3)
    for _ in range(1000):b.seed('1','ramp',.001,3)
    assert a.bins.future.shape==b.bins.future.shape
    assert a.stock()==pytest.approx(b.stock())
    assert len(a.bins.labels)==len(b.bins.labels)==3


@pytest.mark.parametrize('side',['service','supply'])
def test_accepted_flow_gradient_away_from_switching_boundary(side):
    from evaluation.controllers import sdmpc_dual as ad
    r=make();r.seed('1','ramp',4.,0)
    trace=ad.Trace([.001]);x=ad.Dual(1.,{0:1.},trace)
    service=x if side=='service' else 3.
    supply=x if side=='supply' else 3.
    out=r.step({'1':service,'2':2.},{'ramp':supply,'through':2.})
    assert ad.derivative(out[('1','ramp')])[0]==pytest.approx(1.)
    assert ad.derivative(r.stock())[0]==pytest.approx(-1.)
    assert ad.derivative(r.residence_veh_h)[0]==pytest.approx(-.5/3600.)


def test_nonconnecting_lane_cannot_discharge_to_ramp():
    r=LaneTurnReservoir({'1':10.,'2':10.}, [('1','ramp'),('2','ramp')],0,8)
    r.seed('2','ramp',4.,0)
    out=r.step({'1':2.,'2':2.},{'ramp':10.},allowed_exits=[('1','ramp')])
    assert sum(out.values())==0.
    moved=r.transfer_ready({(('2','ramp'),('1','ramp')):1.})
    assert sum(moved.values())==1. and r.stock()==4.
    out=r.step({'1':2.,'2':2.},{'ramp':10.},allowed_exits=[('1','ramp')])
    assert out[('1','ramp')]==1. and out[('2','ramp')]==0.


def test_lateral_moves_do_not_jump_two_lanes_or_borrow_same_step_departures():
    r=LaneTurnReservoir({'1':2.,'2':2.,'3':2.}, [(str(i),'ramp') for i in (1,2,3)],0,8)
    r.seed('2','ramp',2.,0);r.seed('3','ramp',2.,0)
    r.step({'1':0.,'2':0.,'3':0.},{'ramp':0.})
    moved=r.transfer_ready({(('3','ramp'),('2','ramp')):2.,(('2','ramp'),('1','ramp')):2.})
    assert moved[(('3','ramp'),('2','ramp'))]==0.
    assert r.stock('3')==r.stock('1')==2. and r.stock('2')==0.
    assert r.entered==r.exited==0.


def test_lateral_receiving_shared_between_sources():
    r=LaneTurnReservoir({'1':10.,'2':1.,'3':10.}, [(str(i),'ramp') for i in (1,2,3)],0,8)
    r.seed('1','ramp',2.,0);r.seed('3','ramp',2.,0)
    r.step({'1':0.,'2':0.,'3':0.},{'ramp':0.})
    moved=r.transfer_ready({(('1','ramp'),('2','ramp')):2.,(('3','ramp'),('2','ramp')):2.})
    assert list(moved.values())==[.5,.5] and r.stock()==4.


def test_lateral_receiving_does_not_admit_arrivals_before_their_eta():
    r=LaneTurnReservoir({'1':10.,'2':10.}, [('1','ramp'),('2','ramp')],0,8)
    r.seed('2','ramp',4.,5)
    assert r.transfer_ready({(('2','ramp'),('1','ramp')):4.})[(('2','ramp'),('1','ramp'))]==0.


def test_cannot_roll_beyond_fixed_horizon():
    r=make()
    for _ in range(8):r.step({'1':0.,'2':0.},{'ramp':0.,'through':0.})
    with pytest.raises(ValueError,match='fixed horizon'):
        r.step({'1':0.,'2':0.},{'ramp':0.,'through':0.})
