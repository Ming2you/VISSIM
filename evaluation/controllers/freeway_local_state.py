"""Conservative state updates for the link-local freeway predictor.

The vendor implementation is kept unchanged. These hooks are installed by the
single VISSIM adapter, including in spawned price workers. Configuration travels
on the network object so hooks never capture another run's configuration.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def configure(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    section = tuning.get("freeway", {})
    section = section if isinstance(section, Mapping) else {}
    for name in ("local_lane_context", "conservative_offramp_drain"):
        value = section.get(name, False)
        if not isinstance(value, bool):
            raise ValueError(f"freeway.{name} must be a boolean")
        setattr(cfg.network, name, value)
    return {name: float(getattr(cfg.network, name)) for name in (
        "local_lane_context", "conservative_offramp_drain")}


def install(cfg, lane_context: dict[str, Any]) -> dict[str, float]:
    import src.controllers.local_freeway_plant as plant
    from src.controllers.wu_faithful_follower import WuFaithfulFollower

    if (getattr(cfg.network, "local_lane_context", False)
            and not getattr(plant._local_lane_profile, "_rw_current_lane_context", False)):
        original_profile = plant._local_lane_profile

        def current_lane_profile(model, occupancy, demand):
            lanes = original_profile(model, occupancy, demand)
            if getattr(model.cfg.network, "local_lane_context", False):
                # Each local substep owns this context. Never reuse the initial
                # global profile (or another candidate/link) after storage moves.
                lane_context["profile"] = {str(model.link): list(lanes)}
            return lanes

        current_lane_profile._rw_current_lane_context = True
        plant._local_lane_profile = current_lane_profile

    original_drain = WuFaithfulFollower._local_offramp_drain
    if (getattr(cfg.network, "conservative_offramp_drain", False)
            and not getattr(original_drain, "_rw_conservative_drain", False)):

        def conservative_drain(self, off_ramp, occupied, recv_occ, control, dt_h):
            if not getattr(self.cfg.network, "conservative_offramp_drain", False):
                return original_drain(self, off_ramp, occupied, recv_occ, control, dt_h)
            if dt_h <= 0.0:
                raise ValueError("off-ramp drain timestep must be positive")
            available_rate = max(0.0, float(occupied)) / dt_h
            if available_rate == 0.0:
                return 0.0, {}
            total, intakes = 0.0, {}
            # Match the global urban drain's beta*stock limit. Signal capacity
            # alone carries no routing fraction: an open minor turn must not
            # drain cars waiting for a blocked major turn.
            for signal, movement in self._wu._offramp_drain_flow.get(off_ramp, []):
                spec = self._wu._specs[movement]
                beta = max(0.0, float(spec.get("beta", 0.0)))
                intended = min(beta * available_rate,
                    max(0.0, float(self._wu._signal_leaving_rate(signal, movement, control))))
                link = str(spec.get("receiving_link", ""))
                capacity = float(self.cfg.network.urban_link_storage_veh.get(link, 0.0))
                if capacity > 0.0:
                    # Earlier movements have already reserved part of this
                    # receiving space, just as the global sequential update does.
                    space_rate = max(0.0, capacity - float(recv_occ.get(link, 0.0))) / dt_h
                    intended = min(intended, max(0.0, space_rate - intakes.get(link, 0.0)))
                actual = min(intended, max(0.0, available_rate - total))
                total += actual
                if link:
                    intakes[link] = intakes.get(link, 0.0) + actual
            return total, intakes

        conservative_drain._rw_conservative_drain = True
        WuFaithfulFollower._local_offramp_drain = conservative_drain

    return {name: float(getattr(cfg.network, name, False)) for name in (
        "local_lane_context", "conservative_offramp_drain")}
