"""Ten-second shared-lane service must preserve travel, space and labels."""
from copy import deepcopy
import pytest
from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
from evaluation.controllers.multirate_urban_boundary import advance_shared_interval


def make(initial, *, lanes=None):
    lanes = lanes or {'1': dict(capacity_veh=30., service_veh_h=3600., movements=['straight'])}
    entries = {'city': [dict(lane='1', movement='straight', share=1., delay_sec=5)]}
    packets = [dict(lane=lane, source=source, movement=movement, vehicles=n, ready_sec=due)
               for lane, source, movement, n, due in initial]
    return SharedSignalApproach(lanes, entries, packets, 100)


def profile(windows):
    def fractions(start, duration):
        return {lane: sum(max(0., min(start+duration, b)-max(start, a)) for a,b in spans)/duration
                for lane, spans in windows.items()}
    return fractions


def total(rows):
    return sum(row['vehicles'] for row in rows)


def test_two_second_green_survives_one_ten_second_update():
    a=make([('1','city','straight',10.,100)])
    out=advance_shared_interval(a,100,10,profile({'1':[(100,102)]}),{'straight':20.})
    assert total(out)==2. and a.stock()==8. and a.time==110
    assert a.last_interval_segments==1  # no hidden ten one-second replays
    assert a.residence_veh_h==pytest.approx(90./3600.)  # declared uniform interval approximation
    a.assert_conserved()


def test_late_packet_cannot_spend_green_that_ended_before_arrival():
    a=make([('1','off10491','straight',10.,105)])
    out=advance_shared_interval(a,100,10,profile({'1':[(100,102)]}),{'straight':20.})
    assert out==[] and a.stock()==10. and a.time==110
    assert a.last_interval_segments==2
    assert a.residence_veh_h==pytest.approx(100./3600.)


def test_late_packet_can_use_only_later_green_with_labels_retained():
    a=make([('1','off10491','straight',10.,105)])
    out=advance_shared_interval(a,100,10,profile({'1':[(100,102),(106,109)]}),{'straight':20.})
    assert total(out)==3. and a.stock()==7.
    assert {(r['lane'],r['source'],r['movement']) for r in out}=={('1','off10491','straight')}


def test_two_lanes_share_one_receiver_once_across_ready_events():
    lanes={str(i):dict(capacity_veh=30.,service_veh_h=3600.,movements=['straight']) for i in (1,2)}
    a=make([('1','city','straight',10.,100),('2','off10491','straight',10.,105)],lanes=lanes)
    out=advance_shared_interval(a,100,10,profile({'1':[(100,110)],'2':[(100,110)]}),{'straight':6.})
    assert total(out)==pytest.approx(6.) and a.stock()==pytest.approx(14.)
    assert sum(r['vehicles'] for r in out if r['lane']=='1')==pytest.approx(5.5)
    assert sum(r['vehicles'] for r in out if r['lane']=='2')==pytest.approx(.5)
    a.assert_conserved()


def test_fifo_head_blocking_remains_even_if_another_turn_has_space():
    lanes={'1':dict(capacity_veh=30.,service_veh_h=3600.,movements=['straight','left'])}
    a=make([('1','off10491','left',2.,100),('1','city','straight',10.,100)],lanes=lanes)
    out=advance_shared_interval(a,100,10,profile({'1':[(100,110)]}),{'straight':20.,'left':0.})
    assert out==[] and a.stock()==12.


def test_future_fifo_head_is_not_bypassed_and_endpoint_not_early():
    a=make([('1','off10491','straight',2.,110),('1','city','straight',10.,100)])
    assert advance_shared_interval(a,100,10,profile({'1':[(100,110)]}),{'straight':20.})==[]
    out=advance_shared_interval(a,110,10,profile({'1':[(110,112)]}),{'straight':20.})
    assert total(out)==2. and a.stock()==10.


def test_full_adjacent_lane_cannot_borrow_other_lane_space():
    lanes={'1':dict(capacity_veh=10.,service_veh_h=3600.,movements=['straight']),
           '2':dict(capacity_veh=10.,service_veh_h=3600.,movements=['left'])}
    a=make([('1','city','left',3.,100),('2','off10491','left',10.,100)],lanes=lanes)
    assert advance_shared_interval(a,100,10,profile({'1':[],'2':[]}),{'straight':20.,'left':20.})==[]
    assert a.stock('1')==3. and a.stock('2')==10. and a.last_lateral==[]


def test_default_and_explicit_one_second_are_identical():
    a=make([('1','city','straight',10.,100)]); b=deepcopy(a)
    x=a.advance(100,{'1':.2},{'straight':20.})
    y=b.advance(100,{'1':.2},{'straight':20.},duration_sec=1)
    assert x==y and vars(a)==vars(b)


@pytest.mark.parametrize('duration',[0,3,11,True])
def test_invalid_macro_duration_does_not_mutate(duration):
    a=make([('1','city','straight',10.,100)]);before=deepcopy(vars(a))
    with pytest.raises(ValueError):advance_shared_interval(a,100,duration,profile({'1':[]}),{'straight':20.})
    assert vars(a)==before


def test_invalid_later_signal_interval_fails_before_advancing_any_stock():
    a=make([('1','city','straight',10.,105)]); before=deepcopy(vars(a))
    def wrong(start,duration):return {'1':0. if start==100 else float('nan')}
    with pytest.raises(ValueError):advance_shared_interval(a,100,10,wrong,{'straight':20.})
    assert vars(a)==before


def test_signal_clock_view_integrates_the_exact_event_interval(monkeypatch):
    from types import SimpleNamespace as NS
    from src.models.state import SimulationConfig
    from evaluation.controllers import signal_actuation_contract as signals
    from evaluation.controllers.multirate_urban_boundary import signal_intervals
    cfg=NS(simulation=SimulationConfig(T_u=1),network=NS())
    control=object(); calls=[]
    def physical(action,view,spec,index):
        assert action is control and view.network is cfg.network
        duration=view.simulation.T_u_sec;start=index*duration
        calls.append((start,duration))
        # Real native discrete event integration; GREEN only[100,102).
        return signals._finite_fraction(150.,0.,100.,102.,duration,start,start+duration)
    monkeypatch.setattr(signals,'phase_fraction',physical)
    green=signal_intervals(control,cfg,{'1':{'phase':'SC1001_p1'}})
    a=make([('1','city','straight',10.,105)])
    assert advance_shared_interval(a,100,10,green,{'straight':20.})==[]
    assert calls==[(100.,5),(105.,5)] and cfg.simulation.T_u_sec==1


def test_coarse_service_keeps_reverse_derivative_of_flow_and_waiting(monkeypatch):
    from evaluation.controllers import sdmpc_tangent_reverse as ad
    from evaluation.controllers import multirate_urban_boundary as boundary, lane_offramp_runtime as lanes
    # Match the isolated worker's numeric math imports; never cast AD stock.
    monkeypatch.setattr(boundary,'math',ad.MathProxy())
    monkeypatch.setattr(lanes,'math',ad.MathProxy())
    a=make([('1','city','straight',20.,100)])
    trace=ad.Trace([1.]);green=ad.Dual(.4,{0:1.},trace)
    out=advance_shared_interval(a,100,10,lambda start,duration:{'1':green},{'straight':30.})
    values=[total(out),a.stock(),a.residence_veh_h]
    jac=trace.jacobian(values,workers=1)
    assert jac[:,0]==pytest.approx([10.,-10.,-50./3600.])


def test_no_unused_green_or_receiving_credit_enters_next_interval():
    a=make([('1','city','straight',10.,105)])
    assert advance_shared_interval(a,100,5,profile({'1':[(100,105)]}),{'straight':20.})==[]
    assert advance_shared_interval(a,105,5,profile({'1':[]}),{'straight':20.})==[]
    out=advance_shared_interval(a,110,5,profile({'1':[(110,115)]}),{'straight':1.})
    assert total(out)==1. and a.stock()==9.
