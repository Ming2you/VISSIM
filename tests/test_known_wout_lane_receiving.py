"""Local blockage cannot borrow room from downstream121 or independent68 lanes."""
from types import SimpleNamespace as NS
import copy
import pytest
from evaluation.controllers.route_choice_corridor import known_entry_lane_limits


class Buffer:
    def __init__(self, pre, post=0.): self.pre, self.post = pre, post
    def snapshot(self):
        return dict(upstream_travelling_veh=0., head_ready_veh=self.pre,
                    connector_veh=self.pre+self.post)


def case(pre=8., ready=4., due=10, post=0.):
    lanes=[Buffer(pre,post),Buffer(pre,post)]
    buffer=NS(_lane_buffers=lanes,lane_arrival_shares=(.5,.5),
              snapshot=lambda:dict(connector_veh=sum(b.pre+b.post for b in lanes)))
    spec=dict(ramp='R', incoming={'straight':[1,2,3], 'right':[1], 'left':[4]},
              ramp_lanes={'1':0,'2':1},capacity_veh={'1':10.,'2':10.})
    state=NS(lane_ramp_runtime=NS(buffers={'R':buffer}),ramp_queue={'R':2*(pre+post)},
        known_legsplit_route_state=dict(cohorts=[dict(target='R',vehicles=ready,due=due)]))
    cfg=NS(network=NS(known_legsplit_routes=dict(entry_lane_receiving=spec)))
    return state,cfg


def test_two_blocked_lanes_preserve_third_and_independent_fourth():
    s,c=case()
    assert known_entry_lane_limits(s,c,dict(straight=3.,right=1.,left=2.,other=8.),10)==dict(straight=1.,right=0.,left=2.,other=8.)


def test_sources_share_lane_room_instead_of_each_borrowing_it():
    s,c=case(ready=3.)
    result=known_entry_lane_limits(s,c,dict(straight=3.,right=1.),10)
    assert result==dict(straight=1.75,right=.25)


def test_ramp_release_restores_room_without_capacity_bonus():
    s,c=case(pre=3.)
    intended=dict(straight=3.,right=1.,left=2.)
    assert known_entry_lane_limits(s,c,intended,10)==intended


def test_future_arrivals_other_destinations_and_posthead_not_queue():
    s,c=case(due=11,post=100.)
    s.known_legsplit_route_state['cohorts'].append(dict(target='free',vehicles=200.,due=0))
    assert known_entry_lane_limits(s,c,dict(straight=3.,right=1.),10)==dict(straight=3.,right=1.)


def test_pending_admission_counts_once_and_no_inventory_mutation():
    s,c=case(ready=0.)
    s.ramp_queue['R']+=4.
    before=copy.deepcopy((s.ramp_queue,s.known_legsplit_route_state['cohorts']))
    assert known_entry_lane_limits(s,c,dict(straight=3.),10)==dict(straight=1.)
    assert before==(s.ramp_queue,s.known_legsplit_route_state['cohorts'])


def test_disabled_returns_exact_original_mapping():
    s,c=case();c.network.known_legsplit_routes={};intended=dict(straight=3.)
    assert known_entry_lane_limits(s,c,intended,10) is intended


def test_partial_blockage_propagates_ramp_stock_sensitivity_to_each_source():
    from evaluation.controllers.sdmpc_dual import Dual, Trace, derivative, primal
    s,c=case(ready=3.)
    s.lane_ramp_runtime.buffers['R']._lane_buffers[0].pre=Dual(8.,{0:1.},Trace([.01]))
    # The buffer and total ownership refer to the same perturbed vehicle stock.
    s.ramp_queue['R']=s.lane_ramp_runtime.buffers['R'].snapshot()['connector_veh']
    result=known_entry_lane_limits(s,c,dict(straight=3.,right=1.),10)
    assert primal(result['straight'])==1.75 and primal(result['right'])==.25
    assert derivative(result['straight'])[0]==-.5
    assert derivative(result['right'])[0]==-.5


def test_other_destination_maturation_does_not_create_ramp_blockage():
    s,c=case(ready=3.,due=11)
    s.known_legsplit_route_state['cohorts'].append(dict(target='other_ramp',vehicles=100.,due=0))
    intended=dict(straight=3.,right=1.)
    assert known_entry_lane_limits(s,c,intended,10)==intended


def test_wrong_lane_ramp_cohort_blocks_local_room_without_closing_empty_lane():
    s,c=case(ready=0.)
    local=c.network.known_legsplit_routes['entry_lane_receiving']
    local['road_capacity_veh']={'1':4.,'2':4.,'3':4.,'4':4.}
    s.known_legsplit_route_state['cohorts']=[dict(target='R',vehicles=4.,due=2,
        lane68=dict(shares={'3':1.},exit_step=3))]
    assert known_entry_lane_limits(s,c,dict(straight=3.,left=2.),10)==dict(straight=2.,left=2.)
    # Native admission debits the same cohort; the local room then recovers.
    s.known_legsplit_route_state['cohorts'][0]['vehicles']=2.
    assert known_entry_lane_limits(s,c,dict(straight=3.,left=2.),11)==dict(straight=3.,left=2.)


def test_moving_local_stock_reserves_room_but_does_not_become_ready_queue():
    s,c=case(ready=0.)
    c.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']={'3':4.}
    cohort=dict(target='free',vehicles=4.,due=100,lane68=dict(shares={'3':1.},exit_step=12))
    s.known_legsplit_route_state['cohorts']=[cohort]
    assert known_entry_lane_limits(s,c,dict(straight=3.),10)==dict(straight=2.)
    assert known_entry_lane_limits(s,c,dict(straight=3.),12)==dict(straight=3.)
    assert cohort['due']==100 and cohort['vehicles']==4.


def test_local_lane_tags_follow_connector_lanes_and_exclude_downstream121():
    from evaluation.controllers.route_choice_corridor import _known_lane68_tag
    s,c=case()
    c.simulation=NS(T_u_sec=1.)
    local=c.network.known_legsplit_routes['entry_lane_receiving']
    local.update(physical_link='68',road_length_m=118.,road_capacity_veh={str(i):20. for i in range(1,5)},
        connector_entries={'10629':dict(lanes=[1,2,3],position_m=2.,length_m=70.)})
    tag=_known_lane68_tag(c,'10629',3,50.,36.,10)['lane68']
    assert tag==dict(shares={'3':1.},exit_step=24)
    assert _known_lane68_tag(c,'121',1,20.,36.,10)=={}


def test_local_receiving_shares_preserve_scalar_and_gradient():
    from evaluation.controllers.sdmpc_dual import Dual, Trace, derivative, primal
    s,c=case(ready=0.)
    c.network.known_legsplit_routes['entry_lane_receiving']['road_capacity_veh']={'3':4.}
    n=Dual(3.5,{0:1.},Trace([.01]))
    s.known_legsplit_route_state['cohorts']=[dict(target='R',vehicles=n,due=2,
        lane68=dict(shares={'3':1.},exit_step=3))]
    accepted=known_entry_lane_limits(s,c,dict(straight=3.),10)['straight']
    assert primal(accepted)==2.5 and derivative(accepted)[0]==-1.
    shares=s.known_legsplit_route_state['entry_lane_shares']['straight']
    assert abs(primal(sum(shares.values()))-1)<1e-12
