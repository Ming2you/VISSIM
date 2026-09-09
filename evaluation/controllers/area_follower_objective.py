"""Use the canonical Omega endpoint for follower ranking and offset retention."""
from __future__ import annotations
import math


def enabled(cfg):
    return bool(getattr(cfg.network, "control_area_enabled", False))


def install_runtime(cfg):
    if not enabled(cfg):
        if hasattr(cfg.mpc, "_control_area_fallback_ttt_before"):
            cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt = cfg.mpc._control_area_fallback_ttt_before
            del cfg.mpc._control_area_fallback_ttt_before
        return {}
    if not hasattr(cfg.mpc, "_control_area_fallback_ttt_before"):
        cfg.mpc._control_area_fallback_ttt_before = cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt
    # Its existing objective comparator handles negative J additively and keeps
    # severe terminal/completion checks. Avoid a second, global-TTT veto.
    cfg.mpc.stackelberg_fallback_guard_use_rollout_ttt = False
    from src.controllers.wu_faithful_follower import WuFaithfulFollower
    cls = WuFaithfulFollower
    if getattr(cls._rollout_horizon_ttt, "_control_area_follower_objective", False):
        return {"control_area_follower_objective_installed": 1.0, "control_area_fallback_uses_objective": 1.0}
    original_rollout = cls._rollout_horizon_ttt
    original_solve = cls.solve

    def rollout(self, state, control, forecast):
        if not enabled(self.cfg):
            return original_rollout(self, state, control, forecast)
        from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
        point = evaluate_price_point(state, control, forecast, (), ObjectiveSpec(
            cfg=self.cfg, depth_override=max(1, int(self.cfg.mpc.horizon_steps)),
            box_walk=False, score_mode="raw", split_ttt=True))
        area = getattr(point, "control_area", None)
        if not isinstance(area, dict):
            raise ValueError("Omega follower requires the canonical area endpoint")
        values = {
            "objective_veh_h": float(point.objective),
            "ttt_veh_h": float(area["ttt_veh_h"]),
            "ttd_veh": float(area["ttd_veh"]),
            "near_score_veh_h": float(area["near_score_veh_h"]),
            "additional_cost_veh_h": float(area["additional_cost_veh_h"]),
            "global_freeway_ttt_veh_h": float(point.freeway_ttt),
            "global_urban_ttt_veh_h": float(point.urban_ttt),
        }
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("nonfinite Omega follower endpoint result")
        control.diagnostics.update({"control_area_follower_" + k: v for k, v in values.items()})
        events = getattr(self, "_control_area_follower_events", None)
        if events is not None:
            events.append(values)
        # The first component is a ranking score in Omega mode. The two split
        # components retain their global TTT meaning; never reward TD twice.
        return values["objective_veh_h"], values["global_freeway_ttt_veh_h"], values["global_urban_ttt_veh_h"]

    def solve(self, *args, **kwargs):
        if not enabled(self.cfg):
            return original_solve(self, *args, **kwargs)
        absent = object()
        previous_events = getattr(self, "_control_area_follower_events", absent)
        previous_margin = self.offset_keep_margin
        self._control_area_follower_events = events = []
        # A relative threshold on possibly negative TTT-beta*TD is invalid.
        # The existing guard now retains only a strict J improvement (>1e-9).
        self.offset_keep_margin = 0.0
        try:
            result = original_solve(self, *args, **kwargs)
        finally:
            self.offset_keep_margin = previous_margin
            if previous_events is absent:
                del self._control_area_follower_events
            else:
                self._control_area_follower_events = previous_events
        if not events:
            raise ValueError("Omega follower solve produced no canonical endpoint score")
        final = events[-1]
        diagnostics = result.control.diagnostics
        diagnostics["distributed_response_rollout_ttt"] = final["global_freeway_ttt_veh_h"] + final["global_urban_ttt_veh_h"]
        diagnostics["control_area_follower_objective_active"] = 1.0
        diagnostics["control_area_offset_keep_margin"] = 0.0
        # The canonical solve invokes on/off twice only when its offset guard
        # runs, then evaluates the chosen result once. Preserve honest TTT labels
        # and expose the score that actually governed retention separately.
        guard_ran = len(events) == 3 and "wu_faithful_offset_ttt_on" in diagnostics
        if guard_ran:
            for suffix, values in zip(("on", "off"), events[:2]):
                diagnostics["wu_faithful_offset_ttt_" + suffix] = values["global_freeway_ttt_veh_h"] + values["global_urban_ttt_veh_h"]
                for key in ("objective_veh_h", "ttt_veh_h", "ttd_veh"):
                    diagnostics["control_area_offset_" + suffix + "_" + key] = values[key]
        elif "wu_faithful_offset_ttt_on" in diagnostics or "wu_faithful_offset_ttt_off" in diagnostics:
            raise ValueError("unrecognized Omega offset guard endpoint sequence")
        diagnostics["control_area_offset_guard_evaluated"] = float(guard_ran)
        result.diagnostics.update(diagnostics)
        return result

    rollout._control_area_follower_objective = True
    solve._control_area_follower_objective = True
    cls._rollout_horizon_ttt = rollout
    cls.solve = solve
    return {"control_area_follower_objective_installed": 1.0, "control_area_fallback_uses_objective": 1.0}


def install_controller(controller):
    """Called by the canonical builder; workers also reinstall from their cfg."""
    return install_runtime(controller.cfg)
