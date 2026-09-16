"""Offline physical ramp invariants; no VISSIM, COM, or native-file mutation."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary


def make(**overrides):
    args = dict(connector_id="10490", length_m=120., head_position_m=60., lanes=1,
                spacing_m=6., travel_speed_kmh=36., time_sec=0.)
    args.update(overrides)
    return PhysicalRampBoundary(**args)


def step(model, *, service=0., request=0., mode="RED", accepted=None):
    ready = model.begin_interval(model.time_sec)["eligible_merge_veh"]
    model.commit_merge(ready if accepted is None else accepted)
    model.apply_head_service(service, mode=mode)
    return model.finish_interval(request)


class RampBoundaryTests(unittest.TestCase):
    def test_01_passed_head_is_unaffected_by_new_red(self):
        rows = [[60., 0., 1], [90., 20., 1]]
        red = make(initial_cohorts=rows)
        green = make(initial_cohorts=rows)
        red_receipt = step(red)
        green_receipt = step(green, service=1., mode="GREEN")
        self.assertEqual(red_receipt["accepted_merge_veh"], 1.)
        self.assertEqual(green_receipt["accepted_merge_veh"], 1.)
        self.assertEqual(red_receipt["head_service_veh"], 0.)
        self.assertEqual(green_receipt["head_service_veh"], 1.)
        self.assertEqual(step(red)["accepted_merge_veh"], 0.)
        self.assertEqual(step(green)["accepted_merge_veh"], 1.)

    def test_02_full_storage_holds_unadmitted_demand(self):
        model = make(initial_cohorts=[[60., 0., 1]]*20)
        receipt = step(model, request=7.)
        self.assertEqual(receipt["admitted_arrivals_veh"], 0.)
        self.assertEqual(receipt["end"]["outside_component_backlog_veh"], 7.)
        self.assertEqual(receipt["end"]["connector_veh"], 20.)
        self.assertEqual(receipt["connector_ttt_veh_h"], 20.*10./3600.)
        step(model, service=3., mode="OFF")
        receipt = step(model)
        self.assertEqual(receipt["accepted_merge_veh"], 3.)
        self.assertEqual(receipt["admitted_arrivals_veh"], 3.)
        self.assertEqual(receipt["end"]["outside_component_backlog_veh"], 4.)
        self.assertEqual(receipt["end"]["connector_veh"], 20.)
        self.assertEqual(receipt["conservation_residual_veh"], 0.)

    def test_03_positive_post_head_travel_prevents_early_merge(self):
        model = make(length_m=300., head_position_m=60., initial_cohorts=[[60., 0., 1]])
        self.assertEqual(step(model, service=1., mode="GREEN")["accepted_merge_veh"], 0.)
        self.assertEqual(step(model)["accepted_merge_veh"], 0.)  # ETA34, end20.
        self.assertEqual(step(model)["accepted_merge_veh"], 0.)  # end30.
        self.assertEqual(step(model)["accepted_merge_veh"], 1.)  # end40.

    def test_04_receiving_acceptance_not_eligibility_drives_transfers(self):
        model = make(initial_cohorts=[[120., 30., 1]]*3)
        receipt = step(model, accepted=.75)
        self.assertEqual(receipt["eligible_merge_veh"], 3.)
        self.assertEqual(receipt["accepted_merge_veh"], .75)
        self.assertEqual(receipt["end"]["merge_ready_veh"], 2.25)
        self.assertEqual(receipt["end"]["cumulative_merge_veh"], .75)
        self.assertEqual(step(model)["accepted_merge_veh"], 2.25)

    def test_05_arrivals_do_not_teleport_through_head(self):
        model = make()
        receipt = step(model, service=100., mode="OFF", request=1.)
        self.assertEqual(receipt["head_service_veh"], 0.)
        self.assertEqual(receipt["end"]["upstream_travelling_veh"], 1.)
        self.assertEqual(step(model, service=100., mode="OFF")["accepted_merge_veh"], 0.)
        self.assertEqual(step(model)["accepted_merge_veh"], 1.)

    def test_06_invalid_values_sequence_and_overacceptance_fail_closed(self):
        for value in (-1., math.nan, math.inf, True, 5e-324):
            with self.subTest(value=value), self.assertRaises(ValueError):
                make(travel_speed_kmh=value)
        for row in ([121., 10., 1], [60., -1., 1], [60., 10., 2], [60., 10., 1.5]):
            with self.subTest(row=row), self.assertRaises(ValueError):
                make(initial_cohorts=[row])
        with self.assertRaises(ValueError):
            make(initial_cohorts=[[60., 0., 1]]*21)
        with self.assertRaises(ValueError):
            make(head_position_m=120.)
        model = make(initial_cohorts=[[120., 10., 1]])
        with self.assertRaises(ValueError):
            model.commit_merge(0.)
        with self.assertRaises(ValueError):
            model.begin_interval(1.)
        model.begin_interval(0.)
        for value in (-1., math.nan, math.inf, 1.00001):
            before = model.snapshot()
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.commit_merge(value)
            self.assertEqual(model.snapshot(), before)
        model.commit_merge(1.)
        for service, mode, green in ((1., "RED", None), (1., "OFF", 10.),
                                      (1., "GREEN", 0.), (1., "AMBER", None)):
            before = model.snapshot()
            with self.assertRaises(ValueError):
                model.apply_head_service(service, mode=mode, green_sec=green)
            self.assertEqual(model.snapshot(), before)
        model.apply_head_service(0., mode="RED")
        before = model.snapshot()
        with self.assertRaises(ValueError):
            model.finish_interval(math.nan)
        self.assertEqual(model.snapshot(), before)
        model.finish_interval(0.)
        with self.assertRaises(ValueError):
            model.begin_interval(0.)

    def test_07_fractional_storage_conservation_and_connector_cost(self):
        model = make(length_m=123., initial_backlog_veh=4.)
        residence = 0.
        requests = 0.
        for i in range(90):
            start = model.snapshot()
            request = .25 + (i % 7)*.31
            requests += request
            ready = model.begin_interval(model.time_sec)["eligible_merge_veh"]
            model.commit_merge(min(ready, .57))
            model.apply_head_service(.73, mode="GREEN", green_sec=4.)
            receipt = model.finish_interval(request)
            residence += start["connector_veh"]*10./3600.
            state = receipt["end"]
            self.assertLessEqual(state["connector_veh"], 20.5 + 1e-12)
            self.assertAlmostEqual(4.+requests, state["connector_veh"]+
                                   state["outside_component_backlog_veh"]+state["cumulative_merge_veh"], places=10)
            self.assertAlmostEqual(model.connector_ttt_veh_h, residence, places=12)
        self.assertGreater(model.backlog_veh, 0.)

    def test_08_actual_c10490_geometry_initial_cohort_smoke(self):
        profile = json.loads((HERE/"port_profile.json").read_text(encoding="utf-8"))
        cohorts_path = HERE/"seed13_observations/port_cohorts_30s.json"
        cohorts = json.loads(cohorts_path.read_text(encoding="utf-8"))["1350"]["10490"]
        model = make(length_m=279.03213017760226, head_position_m=272.60355928160652,
                     travel_speed_kmh=profile["travel_speed_kmh"]["10490"], time_sec=1350.,
                     initial_cohorts=cohorts)
        initial = model.snapshot()
        self.assertEqual(initial["connector_veh"], len(cohorts))
        self.assertAlmostEqual(model.metadata()["post_head_travel_sec"], .7142034060702027,
                               places=12)
        expected = sum(pos > model.head_position_m for pos, _, _ in cohorts)
        receipt = step(model)
        self.assertEqual(receipt["accepted_merge_veh"], expected)
        self.assertEqual(receipt["head_service_veh"], 0.)
        self.assertAlmostEqual(receipt["end"]["connector_veh"], len(cohorts)-expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
