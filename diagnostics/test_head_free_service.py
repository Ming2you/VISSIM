"""Head-free service uses only existing confirmed online transitions, no rollout."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from evaluation.controllers import signal_head_observation as observer

OPTIONS = {"enabled": True, "min_green_sec": 30, "min_crossings": 5}
MOVEMENT = "SC1005_N_SC105_to_W_SC1004"
ALIAS = "SC1005_N_SC105_to_W"


class HeadFreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.network = self.root / "network.inpx"
        self.network.write_text('''<network><links>
          <link no="403"/><link no="58"/><link no="61"/>
          <link no="10565"><fromLinkEndPt lane="403 1" pos="120"/>
            <toLinkEndPt lane="58 1" pos="0"/><lanes><lane/></lanes></link>
          <link no="10570"><fromLinkEndPt lane="403 2" pos="120"/>
            <toLinkEndPt lane="61 1" pos="0"/><lanes><lane/><lane/></lanes></link>
          </links><signalHeads>
          <signalHead no="h2" lane="403 2" pos="100" sg="1005 7" allVehTypes="true"/>
          <signalHead no="h3" lane="403 3" pos="100" sg="1005 7" allVehTypes="true"/>
          </signalHeads><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="1127" link="403"><vehRoutSta>
          <vehicleRouteStatic no="2" destLink="58"><linkSeq><intObjectRef key="10565"/></linkSeq>
          </vehicleRouteStatic></vehRoutSta></vehicleRoutingDecisionStatic>
          </vehicleRoutingDecisionsStatic></network>''', encoding="utf-8")
        expected = {"kind": "internal", "origin": "SC105_to_SC1005", "signal": "SC1005",
                    "phase": "SC1005_p1", "receiving_link": "SC1005_to_SC1004", "unsignalized": True}
        self.cfg = SimpleNamespace(network=SimpleNamespace(
            urban_movements={MOVEMENT: {**expected, "merged_from": [ALIAS, MOVEMENT]}},
            urban_link_storage_veh={"SC1005_to_SC1004": 100},
            movement_capacity_by_movement_veh_h={MOVEMENT: 200.0}, movement_capacity_veh_h=200.0))
        join = self.root / "join.json"
        self.write(join, {"by_movement": {MOVEMENT: {"status": "unique", "merged_from": [ALIAS, MOVEMENT],
            "physical_turns": [{"from_link": "403", "connector": "10565", "to_link": "58"}]}}})
        self.document = {"schema": "head-free-connector-service/v1", "network": self.pin(self.network),
            "movement_join": self.pin(join), "resources": {"10565": {"source_link": "403", "source_lanes": [1],
                "source_position_m": 120.0, "target_link": "58", "movement": MOVEMENT,
                "merged_from": [ALIAS, MOVEMENT], "expected_movement": expected,
                "native_route": {"decision": "1127", "route": "2", "path": ["403", "10565", "58"]}}}}
        self.contract = self.root / "contract.json"
        self.write(self.contract, self.document)
        self.tuning = {"urban": {"capacity": {"head_observation": OPTIONS, "head_free_service": str(self.contract)}}}
        tuning_path = self.root / "tuning.json"
        self.write(tuning_path, self.tuning)
        self.manifest = self.root / "manifest.json"
        self.write(self.manifest, {"run_id": "runA", "signal_observation": {
            "config_key": "urban.capacity.head_observation", "options": OPTIONS, "config_chain": [self.pin(tuning_path)]},
            "env": {"RW_SIGNAL_OBSERVATION": "1", "RW_QUEUE_WINDOW": "1"},
            "files": {"tuning": self.pin(tuning_path), "network": self.pin(self.network)}})
        self.config_sha = self.pin(tuning_path)["sha256"]

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def pin(path):
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def raw(self, start=0, count=13, unknown=2):
        end = start + 150
        heads = [{"head_id": "h" + str(lane), "link": "403", "lane": lane, "position_m": 100.0,
                  "sc": "1005", "sg": "7"} for lane in [2, 3]]
        return {"sim_sec": end, "network_path": str(self.network),
            "run_provenance": {"run_id": "runA", "manifest_path": str(self.manifest)},
            "local_observation": {"scan_ok": True, "link_departures_window": {"403": count + unknown},
                "signal_observation_window": {"schema": "physical-head-window/v1", "config_sha256": self.config_sha,
                    "start_sec": start, "end_sec": end, "transition_count": 150, "cadence_sec": 1,
                    "exposure_method": "actual_left_step_hold", "clock_complete": True,
                    "heads": heads, "bypass_link_exits": {"403": count}, "unknown_links": {"403": unknown}}}}

    def consume(self, raw, previous=None, *, cfg=None, enabled=True):
        cfg = deepcopy(self.cfg if cfg is None else cfg)
        observer.configure_head_free_service(cfg, self.tuning if enabled else {}, raw)
        metadata = observer.install(cfg, raw, previous, dict(cfg.network.movement_capacity_by_movement_veh_h),
                                    {}, lambda *_: None, OPTIONS)
        return cfg, metadata

    def action(self, raw, metadata, name="previous.json"):
        path = self.root / name
        self.write(path, {"run_provenance": raw["run_provenance"], "metadata": {"sim_sec": raw["sim_sec"], **metadata}})
        return path

    def pair(self):
        raw = self.raw(); _, first = self.consume(raw)
        next_raw = self.raw(150, 17, 3)
        cfg, second = self.consume(next_raw, self.action(raw, first))
        return cfg, second, self.action(next_raw, second, "second.json")

    def test_opt_out_is_exact_and_removes_stale_owned_configuration(self):
        raw = self.raw()
        original = deepcopy(self.cfg)
        expected = observer.install(original, raw, None, {MOVEMENT: 200.0}, {}, lambda *_: None, OPTIONS)
        self.cfg.network.head_free_service = {"stale": True}
        actual, metadata = self.consume(raw, enabled=False)
        self.assertEqual(metadata, expected)
        self.assertEqual(actual.network.movement_capacity_by_movement_veh_h, original.network.movement_capacity_by_movement_veh_h)
        self.assertFalse(hasattr(actual.network, "head_free_service"))

    def test_two_windows_use_data_derived_minimum_not_unknown_or_road_queue(self):
        raw = self.raw(); cfg, first = self.consume(raw)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 200)
        self.assertEqual(first["head_free_waiting_second_window_10565"], 1)
        cfg, second, _ = self.pair()
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 312)
        self.assertEqual(second["head_free_unknown_source_events_10565"], 3)
        self.assertEqual(second["head_free_saturation_unidentified_10565"], 1)
        a = self.raw(count=9); _, m = self.consume(a)
        b = self.raw(150, 11, 99); b["local_observation"]["link_stopped_counts"] = {"403": 9999}
        cfg, _ = self.consume(b, self.action(a, m))
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 216)

    def test_carry_is_observed_only_and_never_reduces_inherited_service(self):
        _, _, previous = self.pair()
        raw = self.raw(300, 0)
        cfg, _ = self.consume(raw, previous)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 312)
        self.cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT] = 500
        cfg, _ = self.consume(raw, previous)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 500)
        self.assertEqual(cfg.network.head_free_service["observations"]["10565"]["observed_only_floor_veh_h"], 312)

    def test_noncontiguous_candidate_wrong_run_and_changed_contract_do_not_pair(self):
        a = self.raw(); _, first = self.consume(a); previous = self.action(a, first)
        cfg, _ = self.consume(self.raw(200, 20), previous)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 200)
        doc = json.loads(previous.read_text()); doc["run_provenance"]["run_id"] = "other"
        self.write(previous, doc)
        cfg, _ = self.consume(self.raw(150, 20), previous)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 200)
        _, _, previous = self.pair()
        self.document["version_note"] = "different contract bytes"
        self.write(self.contract, self.document)
        cfg, _ = self.consume(self.raw(300, 20), previous)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 200)

    def test_incomplete_clock_and_insufficient_counts_cannot_create_candidate(self):
        for count, clock in [(4, True), (13, False)]:
            raw = self.raw(count=count); raw["local_observation"]["signal_observation_window"]["clock_complete"] = clock
            cfg, metadata = self.consume(raw)
            self.assertFalse(any(k.startswith("head_free_candidate_rate_") for k in metadata))
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT], 200)

    def test_malformed_window_counts_and_collector_coverage_fail(self):
        for mutation in [lambda w: w.update(cadence_sec=2), lambda w: w.update(transition_count=149),
                         lambda w: w["bypass_link_exits"].update({"403": 0.5}),
                         lambda w: w["bypass_link_exits"].update({"403": 100}),
                         lambda w: w["heads"][0].update(lane=1)]:
            raw = self.raw(); mutation(raw["local_observation"]["signal_observation_window"])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.consume(raw)

    def test_ambiguous_exit_controlled_member_or_unmerged_alias_fail(self):
        for mutation in [lambda c: c.network.urban_movements[MOVEMENT].update(unsignalized=False),
                         lambda c: c.network.urban_movements.update({ALIAS: {}})]:
            cfg = deepcopy(self.cfg); mutation(cfg)
            with self.assertRaises(ValueError): self.consume(self.raw(), cfg=cfg)
        self.network.write_text(self.network.read_text().replace('lane="403 2" pos="120"', 'lane="403 1" pos="120"'))
        self.document["network"] = self.pin(self.network); self.write(self.contract, self.document)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            observer.configure_head_free_service(self.cfg, self.tuning, self.raw())


if __name__ == "__main__":
    unittest.main()
