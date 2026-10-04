"""Distance-clock invariants for the bounded candidate, not gain qualification."""
import unittest
from types import SimpleNamespace as NS
from evaluation.controllers.physical_ramp_boundary import (
    PhysicalRampBoundary as Buffer, LaneResolvedRampBoundary, ramp_posthead_speed_kmh)


def make(cls=Buffer, cohorts=((80., 0., 1),)):
    return cls(connector_id='r', length_m=100., head_position_m=50., lanes=1,
        spacing_m=5., travel_speed_kmh=36., posthead_travel_speed_kmh=36., time_sec=0.,
        initial_cohorts=cohorts, **({'lane_arrival_shares':[1.]} if cls is LaneResolvedRampBoundary else {}))


def step(b, speed=None, service=0.):
    result = b.advance_local_interval(start_sec=b.time_sec, duration_sec=1., cycle_sec=10.,
        receiving_budget_veh=2., service_veh=service, mode='OFF', green_sec=None,
        request_arrivals_veh=0., allow_partial_cycle=True,
        **({} if speed is None else {'posthead_speed_kmh':speed}))
    if isinstance(b, LaneResolvedRampBoundary):
        # Its shared outer time is advanced with the lane buffers.
        assert b.snapshot()['time_sec'] == b.time_sec
    assert abs(b.snapshot()['conservation_residual_veh']) < 1e-9
    return result['accepted_merge_veh']


class ClockTests(unittest.TestCase):
    def test_nominal_exact(self):
        a,b=make(),make()
        for _ in range(10):
            self.assertEqual(step(a),step(b,36.))
            self.assertEqual(a.snapshot(),b.snapshot())

    def test_half_speed_preserves_remaining_distance(self):
        b=make()
        self.assertEqual([step(b,18.) for _ in range(4)],[0.,0.,0.,1.])

    def test_stopped_then_resume(self):
        b=make()
        self.assertEqual([step(b,0.) for _ in range(5)],[0.]*5)
        self.assertEqual([step(b,36.) for _ in range(2)],[0.,1.])

    def test_new_head_cannot_merge_in_same_second(self):
        b=make(cohorts=((50.,0.,1),))
        self.assertEqual(step(b,0.,10.),0.)
        self.assertEqual(b.snapshot()['downstream_travelling_veh'],1.)
        self.assertEqual([step(b,36.) for _ in range(5)],[0.,0.,0.,0.,1.])

    def test_lane_wrapper_forwards_cap(self):
        b=make(LaneResolvedRampBoundary)
        self.assertEqual([step(b,18.) for _ in range(4)],[0.,0.,0.,1.])

    def test_invalid_cap_is_atomic(self):
        for speed in (-1.,37.,float('nan')):
            b=make();before=b.snapshot()
            with self.assertRaises(ValueError):step(b,speed)
            self.assertEqual(b.snapshot(),before)

    def test_uses_current_merge_cell_not_command(self):
        cfg=NS(network=NS(ramp_to_freeway={'r':'E'},ramp_merge_segment_index={'r':1}))
        state=NS(freeway_speed={'E':[99.,18.]})
        self.assertEqual(ramp_posthead_speed_kmh(state,cfg,'r',36.),18.)
        state.freeway_speed['E'][1]=70.
        self.assertEqual(ramp_posthead_speed_kmh(state,cfg,'r',36.),36.)


if __name__ == '__main__':unittest.main(verbosity=2)
