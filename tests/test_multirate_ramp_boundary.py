from copy import deepcopy
import pytest
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, LaneResolvedRampBoundary
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope
from evaluation.controllers import known_wout_causal_response as causal
from evaluation.controllers.multirate_ramp_boundary import service_integral


def make(lanes=1,positions=(60.,60.,60.,60.),causal_entry=False):
    cls=PhysicalRampBoundary if lanes==1 else LaneResolvedRampBoundary
    extra={} if lanes==1 else {'lane_arrival_shares':(.5,.5)}
    b=cls(connector_id='10681',length_m=72.,head_position_m=60.,lanes=lanes,
          spacing_m=6.,travel_speed_kmh=36.,time_sec=100.,
          initial_cohorts=[(p,0.,1) for p in positions],**extra)
    if causal_entry:
        for child in getattr(b,'_lane_buffers',[b]):
            causal.attach(child,3.);child._causal_receiving_enabled=True
    return b


def run(b,dt=5.,budget=100.,mode='OFF',service=4.,green=None,arrivals=0.,**kw):
    return b.advance_coarse_interval(start_sec=b.time_sec,duration_sec=dt,cycle_sec=10.,
        receiving_budget_veh=budget,service_veh=service,mode=mode,green_sec=green,
        request_arrivals_veh=arrivals,**kw)


def test_integrates_green_overlap_and_cycle_wrap_without_unused_credit():
    assert service_integral(8.,5.,10.,6.,'GREEN',2.)==6.
    assert service_integral(11.,5.,10.,6.,'GREEN',2.)==3.
    assert service_integral(3.,5.,10.,6.,'GREEN',2.)==0.
    assert service_integral(8.,5.,10.,6.,'OFF',None)==3.


def test_one5s_update_keeps_head_departure_and_merge_distinct(monkeypatch):
    b=make();calls=[];original=b.begin_interval
    def begin(*args,**kw):calls.append(args);return original(*args,**kw)
    monkeypatch.setattr(b,'begin_interval',begin)
    first=run(b)
    assert len(calls)==1 and calls[0]==(100.,5.)
    assert first['accepted_merge_veh']==0. and first['head_service_veh']==2.
    assert first['connector_ttt_veh_h']==pytest.approx(4.*5./3600.)
    assert first['local_receipts']==[] and first['local_step_sec']==5.
    second=run(b,mode='RED',service=0.)
    assert second['accepted_merge_veh']==2. and second['head_service_veh']==0.
    assert abs(second['conservation_residual_veh'])<1e-10


def test_actual_merge_limited_by_ready_stock_and_receiving_not_green():
    b=make(positions=(71.,71.,71.))
    r=run(b,budget=.3,mode='RED',service=0.)
    assert r['accepted_merge_veh']==pytest.approx(.3)
    assert b.snapshot()['connector_veh']==pytest.approx(2.7)


def test_current_arrivals_do_not_instantly_become_head_service_or_merge():
    b=make(positions=())
    r=run(b,arrivals=2.,service=100.)
    assert r['head_service_veh']==r['accepted_merge_veh']==0.
    assert r['admitted_arrivals_veh']==2.
    assert b.snapshot()['upstream_travelling_veh']==2.


def test_causal_history_uses_seconds_not_array_indices_and_cannot_double_spend():
    b=make(positions=(),causal_entry=True)
    first=run(b,arrivals=1.)
    m=b._spatial_entry
    assert m['departure_times']==[0,5.]
    assert len(m['departures'])==2 and first['admitted_arrivals_veh']==1.
    before=b.current_admission_space();b.admit_current(min(.2,before))
    assert b.current_admission_space()==pytest.approx(max(0.,before-.2))
    run(b);assert m['departure_times']==[0,5.,10.]


def test_timestamp_receiving_interpolates_only_closed_past_intervals():
    e=ReceivingEnvelope(6.,6.,10.,3.,[6.]) # backward travel2s
    got=e.offer(6.,1.,0.,[0.,1.],departure_times=[0.,5.])
    expected=min(e.qmax,e.initial_bound(6.),.8)
    assert got==pytest.approx(expected)
    with pytest.raises(ValueError,match='unresolved'):
        e.offer(6.,5.,0.,[0.],departure_times=[0.])
    with pytest.raises(ValueError,match='Noncausal'):
        e.offer(6.,1.,0.,[0.,1.],departure_times=[0.,6.])


def test_full_ramp_exposes_no_inaccessible_posthead_room_under_red():
    b=make(positions=tuple(6.*i for i in range(1,11)),causal_entry=True)
    for _ in range(4):
        r=run(b,mode='RED',service=0.,arrivals=1.)
        assert r['admitted_arrivals_veh']==0.
    assert b.snapshot()['connector_veh']==10.
    assert b.snapshot()['outside_component_backlog_veh']==4.


def test_one_lane_cannot_borrow_other_lane_head_service_or_merge_budget():
    b=make(lanes=2)
    r=run(b,service=4.)
    assert r['head_service_veh']==1.
    assert r['lane_receipts'][1]['head_service_veh']==0.
    r=run(b,service=0.,mode='RED',budget=2.,receiving_budget_by_lane_veh=[0.,2.])
    assert r['accepted_merge_veh']==0.
    assert r['end']['connector_veh']==4.


def test_coarse_then_fine_history_is_contiguous_and_copy_independent():
    b=make(causal_entry=True);clone=deepcopy(b)
    run(b);b.begin_interval(105.,1.);b.commit_merge(0.)
    b.apply_head_service(0.,mode='RED');b.finish_interval(0.)
    assert b._spatial_entry['departure_times']==[0,5.,6.]
    assert clone.time_sec==100. and 'departure_times' not in clone._spatial_entry


def test_existing1s_api_still_has_legacy_history_and_exact_receipt():
    b=make(causal_entry=True);copy=deepcopy(b)
    r=b.advance_local_interval(start_sec=100.,duration_sec=1.,cycle_sec=10.,
        receiving_budget_veh=2.,service_veh=4.,mode='OFF',green_sec=None,
        request_arrivals_veh=0.,allow_partial_cycle=True)
    s=run(copy,dt=1.,budget=2.)
    for k in ('accepted_merge_veh','head_service_veh','connector_ttt_veh_h','end'):
        assert r[k]==s[k]
    assert 'departure_times' not in b._spatial_entry


def test_too_long_wave_step_rejected_before_any_mutation():
    b=PhysicalRampBoundary(connector_id='short',length_m=12.,head_position_m=6.,
        lanes=1,spacing_m=6.,travel_speed_kmh=36.,time_sec=100.,initial_cohorts=[])
    causal.attach(b,3.);b._causal_receiving_enabled=True
    before=deepcopy(vars(b))
    with pytest.raises(ValueError,match='wave lag'):run(b)
    assert b.snapshot()['time_sec']==100. and b._phase=='idle'
    assert b._spatial_entry['departures']==before['_spatial_entry']['departures']
