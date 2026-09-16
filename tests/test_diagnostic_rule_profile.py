"""Rule semantics and physical command contracts; no VISSIM or plant rollout."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from evaluation.controllers import diagnostic_profile as policy


VSL_RULE = {"flow_threshold_vph_per_lane": 1600, "occupancy_threshold_pct": 15,
            "speed_thresholds_kph": [60, 80], "speed_commands_kph": [60, 80, 100]}


class Action:
    @classmethod
    def uncontrolled(cls, cfg):
        result = cls()
        result.vsl, result.ramp_metering, result.diagnostics = {}, {}, {}
        result.N_UF_star = 0
        return result

    def copy(self):
        return deepcopy(self)


def fixture(arm="both"):
    service = {str(g): g*144.0 for g in range(2, 10)}
    service.update({"0": 0.0, "10": 1512.0})
    rows = {f"RM_{i}": {"id": f"RM_{i}", "sc_no": i+1, "sg_no": 1,
                        "capacity_vph": 1800.0, "cycle_sec": 10,
                        "model_ramp_key": f"RM_{i}",
                        "service_by_green_veh_h": deepcopy(service)} for i in range(8)}
    mapping = {"ramp_meters": list(deepcopy(rows).values()), "segments": [
        {"model_link": link, "model_segment_index": 0, "dsds": [{"dsd_no": i+1}]}
        for i, link in enumerate(("FW_E", "FW_W"))]}
    physical = {"ramps": rows, "cycle_sec": 10, "max_green_change_sec": 2,
                "minimum_green_sec": 2, "legacy_groups": [], "writer_mapping": mapping["ramp_meters"]}
    net = SimpleNamespace(physical_ramp_branches=physical, ramps=list(rows),
                          ramp_capacity_veh_h={mid: 1512.0 for mid in rows},
                          freeway_links=["FW_E", "FW_W"],
                          freeway_vsl_zone_heads={"FW_E": [0], "FW_W": [0]},
                          freeway_vsl_zone_head_of_cell={"FW_E": [0, 0], "FW_W": [0]})
    cfg = SimpleNamespace(network=net, freeway_follower=SimpleNamespace(vsl_set=[60, 80, 100, 120]))
    tuning = {"diagnostic": {"rule_profile": {"enabled": True, "arm": arm,
        "reference_speed_kph": 100, "vsl_rule": deepcopy(VSL_RULE), "alinea": {
            "gain_vph_per_pct": 70, "target_occupancy_pct": 20,
            "min_rate_vph": 288, "max_rate_vph": 1512}}}}
    observation = {"occupancy_unit": "percent", "flow_unit": "veh/h/lane", "speed_unit": "km/h",
                   "vsl_zones": {f"{link}__seg0": {"flow_vph_per_lane": 1800,
                       "occupancy_pct": 30, "speed_kph": 55} for link in net.freeway_links},
                   "ramps": {mid: {"flow_vph_per_lane": 1800, "occupancy_pct": 30,
                                   "speed_kph": 55} for mid in rows}}
    return cfg, tuning, mapping, observation


class RuleProfileTests(unittest.TestCase):
    def build(self, arm="both", **overrides):
        cfg, tuning, mapping, observation = fixture(arm)
        return policy.build_control(overrides.get("cfg", cfg), Action,
                                    overrides.get("tuning", tuning), mapping, "60,80,100,120",
                                    rule_observation=overrides.get("observation", observation),
                                    rule_history=overrides.get("history"))

    def test_photo_boundary_decisions(self):
        for flow, occupancy, speed, expected in (
                (1600, 15, 0, 100), (1600, 15.01, 60, 60),
                (1600.01, 0, 60, 60), (1601, 15, 60.01, 80),
                (1601, 15, 80, 80), (1601, 15, 80.01, 100)):
            with self.subTest(flow=flow, occupancy=occupancy, speed=speed):
                self.assertEqual(policy.rule_vsl_speed({"flow_vph_per_lane": flow,
                    "occupancy_pct": occupancy, "speed_kph": speed}, VSL_RULE), expected)

    def test_reference_arm_starts_without_observation_at_100_and_all_open(self):
        control = self.build("none", observation=None)
        self.assertEqual(set(control.vsl.values()), {100.0})
        self.assertEqual(set(control.diagnostics["diagnostic_physical_meter_green_sec"].values()), {10.0})

    def test_missing_rule_speed_fails_before_first_feedback(self):
        cfg, _, _, _ = fixture("none")
        cfg.freeway_follower.vsl_set = [80, 100, 120]
        with self.assertRaisesRegex(ValueError, "rule commands.*60"):
            self.build("none", cfg=cfg, observation=None)

    def test_single_lever_arms_leave_the_other_at_reference(self):
        vsl = self.build("vsl")
        self.assertEqual(vsl.vsl["FW_E__seg1"], 60)
        self.assertEqual(set(vsl.diagnostics["diagnostic_physical_meter_green_sec"].values()), {10.0})
        rm = self.build("rm")
        self.assertEqual(set(rm.vsl.values()), {100.0})
        self.assertEqual(set(rm.diagnostics["diagnostic_physical_meter_green_sec"].values()), {8.0})

    def test_occupancy_units_and_unphysical_values_fail(self):
        for field, value in (("occupancy_unit", "fraction"), ("flow_unit", "veh/h")):
            _, _, _, observed = fixture()
            observed[field] = value
            with self.assertRaisesRegex(ValueError, "explicit detector units"):
                self.build(observation=observed)
        for occupancy in (-1, 101, float("nan"), True):
            _, _, _, observed = fixture()
            observed["ramps"]["RM_0"]["occupancy_pct"] = occupancy
            with self.assertRaises(ValueError):
                self.build(observation=observed)

    def test_rate_request_green_model_service_and_csv_encoding_are_distinct(self):
        cfg, tuning, mapping, _ = fixture()
        control = self.build()
        audit = control.diagnostics["diagnostic_rule_meter_audit"]["RM_0"]
        self.assertEqual(audit["bounded_requested_rate_vph"], 812.0)
        self.assertEqual(audit["applied_green_sec"], 8.0)
        self.assertEqual(audit["applied_service_ceiling_vph"], 1152.0)
        self.assertEqual(audit["csv_command_rate_vph"], 1440.0)
        self.assertEqual(audit["next_integrator_rate_vph"], 1152.0)
        actuation = policy.fixed_actuation({"real_world_ramp_metering": {
            "cycle_sec": 10, "amber_sec": 0}}, tuning)
        commands = policy.physical_meter_actions(control, cfg, actuation, mapping)
        self.assertEqual(commands["RM_0"]["green_sec"], 8)
        self.assertEqual(commands["RM_0"]["rate_vph"], 1440)
        self.assertEqual(commands["RM_0"]["group_rate_vph"], 1152)
        self.assertFalse(actuation["real_world_signal_control"]["enabled"])

    def test_integrator_accumulates_within_quantization_interval(self):
        cfg, tuning, _, observed = fixture("rm")
        tuning["diagnostic"]["rule_profile"]["alinea"]["gain_vph_per_pct"] = 1
        history = {"actual_green_sec": dict.fromkeys(cfg.network.ramps, 8),
                   "requested_rate_vph": dict.fromkeys(cfg.network.ramps, 1152)}
        for _ in range(8):
            control = self.build("rm", tuning=tuning, observation=observed, history=history)
            history = control.diagnostics["diagnostic_rule_next_history"]
        self.assertEqual(history["actual_green_sec"]["RM_0"], 7)
        self.assertEqual(history["requested_rate_vph"]["RM_0"], 1072)

    def test_saturation_and_release_respect_actual_green_trust_region(self):
        cfg, tuning, _, observed = fixture("rm")
        history = {"actual_green_sec": dict.fromkeys(cfg.network.ramps, 2),
                   "requested_rate_vph": dict.fromkeys(cfg.network.ramps, 288)}
        for row in observed["ramps"].values():
            row["occupancy_pct"] = 100
        low = self.build("rm", observation=observed, history=history)
        self.assertEqual(low.diagnostics["diagnostic_rule_meter_audit"]["RM_0"]["bounded_requested_rate_vph"], 288)
        for row in observed["ramps"].values():
            row["occupancy_pct"] = 0
        high = self.build("rm", observation=observed, history=history)
        self.assertEqual(high.diagnostics["rw_meter_green_RM_0"], 4)
        self.assertEqual(high.diagnostics["diagnostic_rule_next_history"]["requested_rate_vph"]["RM_0"], 576)

    def test_partial_history_and_wrong_controller_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "all eight"):
            self.build(history={"actual_green_sec": {"RM_0": 10}, "requested_rate_vph": {}})
        with self.assertRaisesRegex(ValueError, "requires --controller"):
            policy.validate_controller(policy.CONTROLLER, fixture()[1])


if __name__ == "__main__":
    unittest.main()
