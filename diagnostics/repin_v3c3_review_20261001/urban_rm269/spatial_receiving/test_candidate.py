import copy
import pytest
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from diagnostics.repin_v3c3_review_20261001.urban_rm269.spatial_receiving.candidate import attach,offer

def buffer(positions):
    b=PhysicalRampBoundary(connector_id='10681',length_m=72,head_position_m=60,lanes=1,
        spacing_m=6,travel_speed_kmh=36,time_sec=100,initial_cohorts=[(x,0,1) for x in positions])
    attach(b,3);return b

def tick(b,n,head=0,admitted=0):
    x=b._spatial_entry;x.update(dt=1,interval_end=100+n,admitted_start=admitted)
    x['departures']=[head]*(n+1)

def test_full_lane_does_not_receive_new_head_space_instantly():
    b=buffer(range(6,61,6));tick(b,1)
    b._spatial_entry['departures'][-1]=1
    assert offer(b,1)==pytest.approx(0)

def test_space_arrives_only_after_backward_travel():
    b=buffer(range(6,61,6));tick(b,20)
    b._spatial_entry['departures']=[0]+[1]*20
    assert offer(b,1)==pytest.approx(0)
    tick(b,21);b._spatial_entry['departures']=[0]+[1]*21
    assert 0<offer(b,1)<=b._spatial_entry['envelope'].qmax

def test_same_stock_different_location_changes_initial_receiving():
    at_entry=buffer([6,12,18,24,30]);at_head=buffer([36,42,48,54,60])
    for b in (at_entry,at_head):tick(b,1)
    assert offer(at_entry,5)==pytest.approx(0)
    assert offer(at_head,5)>0

def test_repeated_commits_share_one_step_budget():
    b=buffer([]);tick(b,1);first=offer(b,10)
    b.cumulative_admitted_veh=first
    assert offer(b,10)==pytest.approx(0)

def test_actual_storage_remains_binding_and_copy_isolated():
    b=buffer([]);tick(b,1);assert offer(b,.01)==.01
    c=copy.deepcopy(b);c._spatial_entry['departures'][-1]=3
    assert b._spatial_entry['departures'][-1]==0

def test_initial_projection_preserves_vehicle_count_and_capacity():
    b=buffer([1,2,13,22,24]);e=b._spatial_entry['envelope']
    assert e.initial_prefix(60)==5
    assert all(y-x>=6-1e-9 for x,y in zip(e.positions,e.positions[1:]))
    assert e.capacity==10
