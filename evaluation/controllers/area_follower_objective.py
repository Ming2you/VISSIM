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
        _finalize_link_phases(self, control, state, forecast)
        from evaluation.controllers import area_meter_finalization
        area_meter_finalization.finalize(control, self.cfg)
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
    metadata = install_runtime(controller.cfg)
    if enabled(controller.cfg):
        _install_link_phase_finalization()
        metadata["control_area_link_phase_finalization_installed"] = 1.0
    return metadata


def _finalize_link_phases(self, control, state, forecast):
    context = getattr(self, "_control_area_link_phase_context", None)
    if context is None:
        return
    if control.diagnostics.get("_control_area_phase_token") == context["token"]:
        if dict(control.green_times) != context["greens"]:
            raise ValueError("Omega scored phase vector changed after finalization")
        return
    before = dict(control.green_times)
    source = "none"
    if self.phase_price_in_gne:
        from src.models.state import phase_key
        for signal, vector in (getattr(self, "_gne_phase_override", None) or {}).items():
            for phase, value in vector.items():
                key = phase_key(signal, phase)
                if key in control.green_times:
                    control.green_times[key] = float(value)
        source = "gne_commit"
    elif self.signal_phase_price:
        # Calls the currently installed canonical refinement chain once, with
        # the same demand that the outer Link.solve would pass to it.
        context["refined_count"] = self.apply_phase_price_refinement(control, state, context["demand"])
        source = "phase_refinement"
    from evaluation.controllers import signal_actuation_contract
    if signal_actuation_contract.enabled(self.cfg.network):
        signal_actuation_contract.validate_control(control, self.cfg)
    context["greens"] = dict(control.green_times)
    control.diagnostics["_control_area_phase_token"] = context["token"]
    control.diagnostics["control_area_phase_finalized_before_score"] = 1.0
    control.diagnostics["control_area_phase_finalization_source"] = source
    control.diagnostics["control_area_phase_finalized_changed_values"] = float(sum(
        before.get(key) != value for key, value in control.green_times.items()))


def _install_link_phase_finalization():
    from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
    cls = LinkAgentWuFollower
    if getattr(cls.solve, "_control_area_link_phase_finalization", False):
        return
    original_solve = cls.solve
    original_refine = cls.apply_phase_price_refinement

    def refine(self, control, state, demand=None):
        context = getattr(self, "_control_area_link_phase_context", None)
        if (enabled(self.cfg) and context is not None and
                control.diagnostics.get("_control_area_phase_token") == context["token"]):
            if dict(control.green_times) != context["greens"]:
                raise ValueError("Omega outer phase vector differs from scored vector")
            return context.get("refined_count", 0)
        return original_refine(self, control, state, demand)

    def solve(self, state, leader, demand, *args, **kwargs):
        if not enabled(self.cfg):
            return original_solve(self, state, leader, demand, *args, **kwargs)
        absent = object()
        previous = getattr(self, "_control_area_link_phase_context", absent)
        context = {"demand": demand}
        # The diagnostics string survives ControlAction.copy for the zero arm;
        # the scope exists only for this solve and is restored on every exit.
        context["token"] = str(id(context))
        self._control_area_link_phase_context = context
        try:
            result = original_solve(self, state, leader, demand, *args, **kwargs)
            if "greens" not in context or dict(result.control.green_times) != context["greens"]:
                raise ValueError("Omega Link returned an unscored final phase vector")
            result.control.diagnostics["control_area_phase_outer_matches_scored"] = 1.0
            result.control.diagnostics.pop("_control_area_phase_token", None)
            result.diagnostics.pop("_control_area_phase_token", None)
            result.diagnostics.update(result.control.diagnostics)
            return result
        finally:
            if previous is absent:
                del self._control_area_link_phase_context
            else:
                self._control_area_link_phase_context = previous

    solve._control_area_link_phase_finalization = True
    cls.apply_phase_price_refinement = refine
    cls.solve = solve
