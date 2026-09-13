"""Installed global direct/signal capacity tests against the real scheduler."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "diagnostics")]
from probe_model_area_integration import build_projected
from evaluation.controllers.observation_projection import install_direct_branch_capacity_runtime


class GlobalBranchReceiving(unittest.TestCase):
    def setUp(self):
        nc = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
        self.cfg, self.state, *_ = build_projected(ROOT / "evaluation/configs/n21_n7_20260908.json", nc / "state_000900.json", nc / "action_000001.json")
        self.state.urban_movement_queue = {key: 0.0 for key in self.state.urban_movement_queue}
        self.dt = self.cfg.simulation.T_f_h
        from src.models import urban_queue_model
        self.uqm = urban_queue_model
        self.original = getattr(urban_queue_model, "_direct_branch_capacity_original", urban_queue_model.off_ramp_capacity_by_freeway_link)

    def test_full_direct_tail_used_to_reject_removed_stock_now_flow_is_blocked_before_departure(self):
        off = "OR_D_W"
        signal = self.cfg.network.off_ramp_storage_link[off]
        direct = self.cfg.network.offramp_direct_tail_by_offramp[off]
        share = self.cfg.network.offramp_direct_share_by_offramp[off]
        self.state.urban_link_storage[signal] = self.cfg.network.urban_link_storage_veh[signal]
        self.state.urban_link_storage[direct] = 0.0
        old_cap = self.original(self.state, self.cfg, interval_h=self.dt)[off]
        proposed_veh = min(10.0, old_cap * self.dt)
        legacy = self.state.copy()
        accepted, rejected = self.uqm.schedule_offramp_arrivals(legacy, self.cfg, off, proposed_veh, 0)
        self.assertAlmostEqual(rejected, proposed_veh * share)
        self.assertAlmostEqual(-proposed_veh + accepted, -rejected)
        self.assertGreater(rejected, 0)
        self.cfg.network.local_landing_state = True
        install_direct_branch_capacity_runtime(self.cfg)
        new_cap = self.uqm.off_ramp_capacity_by_freeway_link(self.state, self.cfg, interval_h=self.dt)[off]
        self.assertEqual(new_cap, 0)
        accepted, rejected = self.uqm.schedule_offramp_arrivals(self.state, self.cfg, off, min(10.0, new_cap*self.dt), 0)
        self.assertEqual((accepted, rejected), (0, 0))

    def test_partial_direct_room_and_signal_room_both_constrain_without_rejection(self):
        off = "OR_D_W"
        self.cfg.network.off_ramps = [off]
        self.cfg.network.offramp_direct_share_by_offramp[off] = .4
        signal = self.cfg.network.off_ramp_storage_link[off]
        direct = self.cfg.network.offramp_direct_tail_by_offramp[off]
        self.state.urban_link_storage[signal] = 6
        self.state.urban_link_storage[direct] = 2
        self.cfg.network.local_landing_state = True
        install_direct_branch_capacity_runtime(self.cfg)
        cap = self.uqm.off_ramp_capacity_by_freeway_link(self.state, self.cfg, interval_h=self.dt)[off]
        self.assertAlmostEqual(cap*self.dt, 5)
        accepted, rejected = self.uqm.schedule_offramp_arrivals(self.state, self.cfg, off, cap*self.dt, 0)
        self.assertAlmostEqual(accepted, 5)
        self.assertAlmostEqual(rejected, 0)
        self.assertAlmostEqual(self.state.urban_link_storage[signal], 3)
        self.assertAlmostEqual(self.state.urban_link_storage[direct], 0)

    def test_shared_direct_receiver_reserves_space_once(self):
        offs = ["OR_D_W", "OR_F_W"]
        self.cfg.network.off_ramps = offs
        direct = self.cfg.network.offramp_direct_tail_by_offramp[offs[0]]
        for off in offs:
            self.cfg.network.offramp_direct_share_by_offramp[off] = .5
            self.cfg.network.offramp_direct_tail_by_offramp[off] = direct
            self.state.urban_link_storage[self.cfg.network.off_ramp_storage_link[off]] = 12
        self.state.urban_link_storage[direct] = 8
        self.cfg.network.local_landing_state = True
        install_direct_branch_capacity_runtime(self.cfg)
        caps = self.uqm.off_ramp_capacity_by_freeway_link(self.state, self.cfg, interval_h=self.dt)
        self.assertAlmostEqual(sum(caps[o]*self.dt*.5 for o in offs), 8)
        for off in offs:
            _, rejected = self.uqm.schedule_offramp_arrivals(self.state, self.cfg, off, caps[off]*self.dt, 0)
            self.assertAlmostEqual(rejected, 0)
        self.assertAlmostEqual(self.state.urban_link_storage[direct], 0)

    def test_disabled_cfg_delegates_and_coupling_alias_is_restored_idempotently(self):
        from src.simulation import coupling
        expected = self.original(self.state, self.cfg, interval_h=self.dt)
        self.cfg.network.local_landing_state = True
        install_direct_branch_capacity_runtime(self.cfg)
        install_direct_branch_capacity_runtime(self.cfg)
        self.assertIs(coupling.off_ramp_capacity_by_freeway_link, self.uqm.off_ramp_capacity_by_freeway_link)
        self.cfg.network.local_landing_state = False
        self.assertEqual(self.uqm.off_ramp_capacity_by_freeway_link(self.state, self.cfg, interval_h=self.dt), expected)
        self.assertIs(self.uqm._direct_branch_capacity_original, self.original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
