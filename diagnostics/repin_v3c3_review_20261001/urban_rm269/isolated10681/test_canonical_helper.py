"""Physical and derivative checks for the inactive canonical receiving helper."""
from copy import deepcopy

import pytest

from evaluation.controllers import known_wout_causal_response as c
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_order.test_candidate import (
    setup, cohort, lane_total,
)


def buffer(positions):
    b = PhysicalRampBoundary(connector_id='10681', length_m=72,
        head_position_m=60, lanes=1, spacing_m=6, travel_speed_kmh=36,
        time_sec=100, initial_cohorts=[(x, 0, 1) for x in positions])
    c.attach(b, 3)
    return b


def test_head_space_has_backward_delay_and_one_step_budget():
    b = buffer(range(6, 61, 6))
    for i in range(21):
        c.begin_receiving_interval(b, 100+i, 1)
        if i == 0:
            b.cumulative_head_service_veh = 1
        c.record_head_service(b)
        value = c.offer(b, 1)
        if i < 20:
            assert value == pytest.approx(0)
    assert 0 < value <= b._spatial_entry['envelope'].qmax
    b.cumulative_admitted_veh += value
    assert c.offer(b, 1) == pytest.approx(0)
    with pytest.raises(ValueError, match='Noncontiguous'):
        c.begin_receiving_interval(b, 123, 1)


def test_location_capacity_and_clone_stay_physical():
    entry, head = buffer([6, 12, 18, 24, 30]), buffer([36, 42, 48, 54, 60])
    for b in (entry, head):
        c.begin_receiving_interval(b, 100, 1)
    assert c.offer(entry, 5) == pytest.approx(0)
    assert c.offer(head, 5) > 0
    assert c.offer(head, .01) <= .01
    copied = deepcopy(head)
    copied._spatial_entry['departures'].append(2)
    assert head._spatial_entry['departures'] == [0.]


def test_lateral_turnover_is_adjacent_conservative_and_causal():
    state, cfg = setup([cohort(3, 4., 1), cohort(4, 5., 2)], rate=.001)
    setattr(state, c.FIELD, dict(step=-1, departed={'2': 1., '3': 2.}))
    c.advance(state, cfg, 0)
    assert lane_total(state, 2) == pytest.approx(1.)
    assert state.known_legsplit_route_state['cohorts'][1]['lane68']['shares'] == pytest.approx({'3': .4, '4': .6})
    assert sum(x['vehicles'] for x in state.known_legsplit_route_state['cohorts']) == 9.
    c.record_source_departures(state, {'2': 3.}, {'2': 2.}, 0)
    assert getattr(state, c.FIELD)['departed']['2'] == pytest.approx(1.)
    with pytest.raises(AssertionError, match='old departure'):
        c.advance(state, cfg, 2)


def test_current_source_mixture_replaces_historical_remixing():
    rows = [(dict(target='RM_C10681', lane68={'shares': {'1': .75, '2': .25}}), 2.),
            (dict(target='RM_C10681', lane68={'shares': {'2': 1.}}), 3.)]
    original = deepcopy(rows)
    counts, shares = c.mixture(rows, {'ramp': 'RM_C10681', 'ramp_lanes': {'1': 0, '2': 1}})
    assert counts == pytest.approx([1.5, 3.5])
    assert shares == pytest.approx((.3, .7))
    assert rows == original


def test_departure_derivative_survives_canonical_helper(monkeypatch):
    from evaluation.controllers.sdmpc_dual import Dual, Trace, MathProxy, primal, derivative
    monkeypatch.setattr(rc, 'math', MathProxy())
    state, cfg = setup([cohort(3, 4., 1)], rate=.001)
    setattr(state, c.FIELD, dict(step=-1, departed={'2': Dual(1., {0: 1.}, Trace([.01]))}))
    c.advance(state, cfg, 0)
    value = lane_total(state, 2)
    assert primal(value) == pytest.approx(1.)
    assert derivative(value)[0] == pytest.approx(1.)


def test_optional_configuration_and_live_source_binding_are_state_local():
    from types import SimpleNamespace as NS
    from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
    ramp = 'RM_C10681'
    storage = 'SC1004_W_out'
    geometry = {'ramp': ramp, 'ramp_lanes': {'1': 0, '2': 1}}
    spec = dict(storage=storage, entry_lane_receiving=geometry,
                connector_queue_gate=True, lateral_access_rate_per_sec=.008)
    cfg = NS(network=NS(known_legsplit_routes=spec,
        boundary_out_ramp_split={storage: {'ramps': {ramp: .5}}},
        on_ramp_to_movement={ramp: []}, gate_onramp_queue_ramps={ramp}))
    b = LaneResolvedRampBoundary(connector_id='10681', length_m=72,
        head_position_m=60, lanes=2, spacing_m=6, travel_speed_kmh=36,
        time_sec=100, initial_cohorts=[(60, 0, 1), (60, 0, 2)],
        lane_arrival_shares=(.9, .1))
    state = NS(lane_ramp_runtime=NS(buffers={ramp: b}), ramp_queue={ramp: 2.},
        known_legsplit_route_state={'plan': {'rows': [
            (dict(target=ramp, lane68={'shares': {'1': .3, '2': .7}}), 5.)]}})
    original = deepcopy(state)
    assert c.configure(cfg, {}, state) == {}
    assert all(not hasattr(lane, '_spatial_entry') for lane in b._lane_buffers)
    c.configure(cfg, {'urban': {'known_wout_causal_lane_response': {'wave_m_s': 3.}}}, state)
    assert all(hasattr(lane, '_spatial_entry') for lane in b._lane_buffers)
    assert all(not hasattr(lane, '_spatial_entry') for lane in original.lane_ramp_runtime.buffers[ramp]._lane_buffers)
    c.bind_source_request(state, spec, {ramp: 5.})
    assert b.lane_arrival_shares == pytest.approx((.3, .7))
    assert original.lane_ramp_runtime.buffers[ramp].lane_arrival_shares == (.9, .1)
    state.ramp_queue[ramp] = 3.
    with pytest.raises(ValueError, match='outside ramp backlog'):
        c.bind_source_request(state, spec, {ramp: 5.})
    # Exercise the real lifecycle hooks, including one head-history write and
    # the causal admission cap. No diagnostic monkeypatch is installed.
    for lane in b._lane_buffers:
        lane.begin_interval(100, 1)
        lane.commit_merge(0.)
        lane.apply_head_service(1., mode='GREEN', green_sec=1.)
        receipt = lane.finish_interval(1.)
        assert lane._spatial_entry['departures'] == [0., 1.]
        assert receipt['admitted_arrivals_veh'] <= lane._spatial_entry['envelope'].qmax
        assert abs(receipt['conservation_residual_veh']) < 1e-9


def test_causal_option_rejects_unqualified_routes_without_mutating_state():
    from types import SimpleNamespace as NS
    cfg, state = NS(network=NS()), NS()
    with pytest.raises(ValueError, match='connector queue'):
        c.configure(cfg, {'urban': {'known_wout_causal_lane_response': {'wave_m_s': 3.}}}, state)
    assert vars(state) == {}
