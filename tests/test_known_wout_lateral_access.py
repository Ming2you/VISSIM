"""A route destination is not proof that its current lane can enter the ramp."""
from types import SimpleNamespace as NS
from copy import deepcopy
import pytest
from evaluation.controllers import route_choice_corridor as rc


def fixture(cohorts=None):
    spec=dict(storage='W',local_queue_gate=True,lateral_access_rate_per_sec=.1,
        entry_lane_receiving=dict(ramp='R',ramp_lanes={'1':0,'2':1},
            road_capacity_veh={str(i):20. for i in range(1,5)}))
    cfg=NS(network=NS(known_legsplit_routes=spec),simulation=NS(T_u_sec=1.))
    state=NS(known_legsplit_route_state=dict(cohorts=cohorts or [],plan=None),urban_storage_release_buffer={})
    return state,cfg


def cohort(lane,n=10.,target='R',due=0):
    return dict(target=target,vehicles=n,due=due,lane68=dict(shares={str(lane):1.},exit_step=0,order=(0,10.)))


def test_nonconnecting_stock_cannot_request_direct_ramp_admission():
    s,c=fixture();x=cohort(3)
    assert rc._known_ramp_lane_share(c,x)==0.
    assert rc._known_ramp_lane_share(c,cohort(2))==1.


def test_full_receiver_prevents_lateral_transfer():
    x=cohort(3);s,c=fixture([cohort(2,20),x]);before=deepcopy(s)
    rc._known_lateral_advance(s,c,0)
    assert s.known_legsplit_route_state==before.known_legsplit_route_state


def test_move_is_adjacent_one_step_and_does_not_duplicate_owned_stock():
    x=cohort(4);s,c=fixture([x]);rc._known_lateral_advance(s,c,0)
    assert x['vehicles']==10 and set(x['lane68']['shares'])=={'3','4'}
    assert sum(x['lane68']['shares'].values())==pytest.approx(1.)
    assert rc._known_ramp_lane_share(c,x)==0.
    assert x['due']==0 and not s.urban_storage_release_buffer


def test_receiving_space_shared_across_cohorts_and_no_two_lane_jump():
    a,b=cohort(3),cohort(3);s,c=fixture([cohort(2,19.9),a,b,cohort(4)])
    c.network.known_legsplit_routes['lateral_access_rate_per_sec']=100.
    rc._known_lateral_advance(s,c,0)
    moved=sum(x['vehicles']*x['lane68']['shares'].get('2',0) for x in (a,b))
    assert moved==pytest.approx(.1)
    assert '2' not in s.known_legsplit_route_state['cohorts'][-1]['lane68']['shares']


def test_arrivals_not_yet_at_branch_keep_current_location():
    x=cohort(3,due=1);s,c=fixture([x]);before=deepcopy(x)
    rc._known_lateral_advance(s,c,0)
    assert x==before


def test_debit_removes_only_connecting_lane_mass():
    x=cohort(2,4);x['lane68']['shares']={'2':.5,'3':.5};s,c=fixture([x])
    rc._known_ramp_lane_debit(c,x,1.)
    assert x['vehicles']==3.
    assert x['lane68']['shares']==pytest.approx({'2':1/3,'3':2/3})
    assert x['vehicles']*x['lane68']['shares']['3']==pytest.approx(2.)
    with pytest.raises(ValueError):rc._known_ramp_lane_debit(c,x,2.)


def test_receiving_sensitivity_preserved(monkeypatch):
    from evaluation.controllers.sdmpc_dual import Dual,Trace,MathProxy,primal,derivative
    monkeypatch.setattr(rc,'math',MathProxy())
    receiver=cohort(2,Dual(10.,{0:1.},Trace([.01])))
    source=cohort(3,10.);s,c=fixture([receiver,source]);rc._known_lateral_advance(s,c,0)
    moved=source['vehicles']*source['lane68']['shares']['2']
    assert 0<primal(moved)<1 and derivative(moved)[0]<0
    assert primal(source['vehicles'])==10


def test_disabled_helper_is_exact_noop():
    x=cohort(3);s,c=fixture([x]);c.network.known_legsplit_routes.pop('lateral_access_rate_per_sec')
    before=deepcopy(s);rc._known_lateral_advance(s,c,0)
    assert vars(s)==vars(before) and rc._known_ramp_lane_share(c,x)==1.


def test_other_lane_ramp_flow_does_not_release_wrong_lane_fifo():
    r=cohort(3,4);f=cohort(3,3,'free');f.update(local68_queue=True,downstream_steps=5)
    f['lane68']['order']=(0,30.)
    s,c=fixture([r,f]);p=dict(requests={'R':4.})
    rc._known_local_queue_advance(s,c,p,{'R':4.},0)
    assert f['vehicles']==3. and not s.urban_storage_release_buffer


def test_tiny_stock_keeps_count_without_division_underflow():
    x=cohort(3,1e-180);s,c=fixture([x]);rc._known_lateral_advance(s,c,0)
    assert x['vehicles']==1e-180
    assert sum(x['lane68']['shares'].values())==pytest.approx(1.)


def test_public_request_commit_keeps_wrong_lane_stock_in_its_owner():
    connected,wrong=cohort(2,2.),cohort(3,4.)
    s,c=fixture([connected,wrong]);spec=c.network.known_legsplit_routes
    spec['entry_lane_receiving']['road_capacity_veh']['2']=2.
    spec['physical_travel']={}
    c.network.boundary_out_ramp_split={'W':{'free':0.,'ramps':{'R':1.}}}
    c.network.urban_link_storage_veh={'W':10.}
    s.urban_link_storage={'W':4.};s.known_legsplit_route_state['departed']=0.
    assert rc.known_legsplit_requests(s,c,'W',6.,6.,0)=={'R':2.}
    s.urban_link_storage['W']+=1.
    rc.known_legsplit_commit(s,c,[('W','R',1.)],0)
    assert connected['vehicles']==1. and wrong['vehicles']==4.
    assert s.known_legsplit_route_state['departed']==1.
    assert sum(x['vehicles'] for x in s.known_legsplit_route_state['cohorts'])==5.
