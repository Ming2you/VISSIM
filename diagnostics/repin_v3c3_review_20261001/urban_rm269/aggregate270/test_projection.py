from copy import deepcopy
import pytest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.project_saved import project


def case():
    geometry = dict(ramp='RM_C10681', road_capacity_veh={'1':10.,'2':10.},
                    connector_entries={'10625':dict(lanes=[1],capacity_per_lane_veh=5.)})
    network = dict(known_legsplit_routes=dict(storage='W_out',entry_lane_receiving=geometry,
                   future_choice_weights={'RM_C10681':.6,'free':.2,'RM_C10646':.2}),
                   urban_link_storage_veh={'W_out':100.})
    cohorts = [dict(target='RM_C10681', vehicles=3., due=13,
                    lane68=dict(shares={'1':.5,'2':.5},exit_step=13)),
               dict(target='prechoice',vehicles=2.,due=14,
                    connector68=dict(link='10625',shares={'1':1.},ready_step=12)),
               dict(target='free',vehicles=1.,due=15)]
    state = dict(time_sec=10.,known_legsplit_route_state=dict(cohorts=cohorts),
                 urban_link_storage={'W_out':94.})
    return state, network


def test_projection_preserves_owned_mass_routes_lanes_and_stage_timing():
    result=project(*case(),horizon=20)
    assert result['projected_mass_veh']==result['sole_owner_mass_veh']==6.
    assert all(v==0. for v in result['target_error_veh'].values())
    assert result['road68']['by_lane_veh']=={'1':1.5,'2':1.5}
    assert result['road68']['stage_eligible_veh']==0.
    assert result['connectors']['10625']['stock_veh']==2.
    assert result['tail']['stock_veh']==1.


def test_projection_rejects_disagreement_with_the_sole_physical_owner():
    state, network=case();state['urban_link_storage']['W_out']=93.
    with pytest.raises(ValueError,match='sole W_out owner'):project(state,network)


def test_projection_does_not_clip_stock_to_make_capacity_pass():
    state, network=case();network['known_legsplit_routes']['entry_lane_receiving']['road_capacity_veh']['1']=1.
    with pytest.raises(ValueError,match='exceeds'):project(state,network)


def test_projection_preserves_prechoice_rather_than_applying_future_ratio_now():
    state, network=case()
    network['known_legsplit_routes']['future_choice_weights']={'RM_C10681':1.,'free':0.,'RM_C10646':0.}
    result=project(state,network)
    assert result['connectors']['10625']['stock_veh']==2.
    assert result['target_error_veh']['prechoice']==0.
    assert result['target_error_veh']['RM_C10681']==0.


def test_projection_size_independent_of_packet_fragmentation():
    state, network=case();before=project(state,network)
    cohorts=state['known_legsplit_route_state']['cohorts']
    c=cohorts.pop(0)
    for _ in range(100):cohorts.append({**deepcopy(c),'vehicles':c['vehicles']/100})
    after=project(state,network)
    assert after['source_cohorts']>before['source_cohorts']
    assert after['road68']['future_shape']==before['road68']['future_shape']
    assert after['projected_mass_veh']==pytest.approx(before['projected_mass_veh'])


def test_passed_road_tag_does_not_keep_borrowing_road_storage():
    state, network=case()
    state['known_legsplit_route_state']['cohorts'][-1]['lane68']=dict(shares={'1':1.},exit_step=9)
    result=project(state,network)
    assert result['tail']['stock_veh']==1.
    assert result['road68']['stock_veh']==3.
