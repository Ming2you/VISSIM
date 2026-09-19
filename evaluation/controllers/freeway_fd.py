"""Consistent cell FD hooks, installed by the canonical adapter after segment hooks.

This module changes no calibration. A segment VSL remains a float, carrying an
immutable FD snapshot to its consumers. This avoids reading the adapter's shared
last-segment context, which can belong to another candidate or another cell.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


def configure_state_response(cfg, tuning) -> dict[str, float]:
    """Explicit directional METANET response regimes; absent is an exact no-op.

    This changes relaxation/anticipation, not demand, conservation, capacity,
    merge flow, or the objective. Values travel with cfg into spawned workers.
    An enabled experiment is not evidence that these regimes improve prediction.
    """
    section = (tuning.get('freeway', {}) or {}).get('state_response')
    if section is None:
        if hasattr(cfg.network, 'freeway_state_response'):
            del cfg.network.freeway_state_response
        return {'freeway_state_response_enabled': 0.0}
    if not isinstance(section, Mapping) or not section:
        raise ValueError('state_response requires an explicit nonempty direction map')
    allowed = {'relaxation', 'anticipation', 'congested_nu_multiplier'}
    values = {}
    for road, row in section.items():
        if road not in cfg.network.freeway_links or not isinstance(row, Mapping) or not row or set(row)-allowed:
            raise ValueError('Invalid state_response direction or fields: ' + str(road))
        values[road] = {}
        for key, value in row.items():
            if key == 'congested_nu_multiplier':
                members = {'factor': value}
            else:
                expected = ({'acceleration_sec', 'deceleration_sec'} if key == 'relaxation'
                            else {'downstream_ge_local', 'downstream_lt_local'})
                if not isinstance(value, Mapping) or set(value) != expected:
                    raise ValueError('State response requires both branches: ' + key)
                members = value
            parsed = {}
            for name, number in members.items():
                if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                    raise ValueError('State response values must be finite numeric values')
                lower = cfg.simulation.T_f_h * 3600 if key == 'relaxation' else 0.0
                if number < lower or (key != 'anticipation' and number <= 0):
                    raise ValueError('Invalid state response value: ' + name)
                parsed[name] = float(number)
            values[road][key] = parsed['factor'] if key == 'congested_nu_multiplier' else parsed
    cfg.network.freeway_state_response = values
    return {'freeway_state_response_enabled': 1.0, 'freeway_state_response_directions': float(len(values))}


def state_response_coefficients(spec, speed, desired, rho, downstream, critical, tau_h, nu):
    """Evaluate regimes from this model step, never future observations.

    Equality uses the acceleration and downstream-ge branches; at rho==critical
    there is no congested multiplier. No correction is added to vehicle flows.
    """
    if not spec:
        return tau_h, nu
    if 'relaxation' in spec:
        branch = 'acceleration_sec' if desired >= speed else 'deceleration_sec'
        tau_h = spec['relaxation'][branch] / 3600.0
    if 'anticipation' in spec:
        branch = 'downstream_ge_local' if downstream >= rho else 'downstream_lt_local'
        nu = spec['anticipation'][branch]
    if 'congested_nu_multiplier' in spec and rho > critical:
        nu *= spec['congested_nu_multiplier']
    return tau_h, nu


@dataclass(frozen=True)
class FDParameters:
    v_free: float
    rho_crit: float
    rho_jam: float

    def validate(self) -> None:
        if not all(math.isfinite(v) for v in (self.v_free, self.rho_crit, self.rho_jam)):
            raise ValueError("two-branch FD parameters must be finite")
        if self.v_free <= 0.0 or not 0.0 < self.rho_crit < self.rho_jam:
            raise ValueError("two-branch FD requires v_free > 0 and 0 < rho_crit_two_branch < rho_max")

    def free_speed(self, cap: float, active: bool) -> float:
        if not active:
            return self.v_free
        if not math.isfinite(float(cap)) or float(cap) <= 0.0:
            raise ValueError("active VSL must be finite and positive")
        return min(self.v_free, float(cap))

    def critical(self, cap: float, active: bool) -> float:
        speed = self.free_speed(cap, active)
        wave = self.v_free * self.rho_crit / (self.rho_jam - self.rho_crit)
        return wave * self.rho_jam / (speed + wave)

    def desired_speed(self, rho: float, cap: float, active: bool) -> float:
        speed = self.free_speed(cap, active)
        if float(rho) <= self.critical(cap, active):
            return speed
        wave = self.v_free * self.rho_crit / (self.rho_jam - self.rho_crit)
        return max(0.0, wave * (self.rho_jam - float(rho)) / float(rho))


class SegmentVSL(float):
    """Numeric VSL with call-local FD data; never stored in shared mutable context."""

    def __new__(cls, value, fd, active, nu_free, nu_cong):
        result = super().__new__(cls, value)
        result.fd = fd
        result.active = active
        result.nu_free = nu_free
        result.nu_cong = nu_cong
        return result

    def __reduce__(self):
        return (type(self), (float(self), self.fd, self.active, self.nu_free, self.nu_cong))


def cell_parameters(net, link=None, index=None) -> FDParameters:
    table = getattr(net, "freeway_segment_params", {}) or {}
    rows = table.get(str(link), ()) if isinstance(table, Mapping) else ()
    row = rows[index] if isinstance(rows, (tuple, list)) and index is not None and 0 <= index < len(rows) else {}
    row = row if isinstance(row, Mapping) else {}
    by_direction = (getattr(net, "rho_crit_two_branch_by_direction", {}) or {}
                    if getattr(net, "vsl_fd_two_branch", False) else {})
    result = FDParameters(
        float(row.get("v_free", net.v_free)),
        float(by_direction.get(str(link), getattr(net, "rho_crit_two_branch", 0.0))),
        float(row.get("rho_max", net.rho_max)),
    )
    result.validate()
    return result


def _segment_value(value, cfg, link, index):
    net = cfg.network
    rows = (getattr(net, "freeway_segment_params", {}) or {}).get(str(link), ())
    row = rows[index] if 0 <= index < len(rows) else {}
    active = float(value) < max(cfg.freeway_follower.vsl_set) - 0.5
    return SegmentVSL(
        float(value), cell_parameters(net, link, index), active,
        float(row.get("metanet_nu_km2_h", net.metanet_nu_km2_h)),
        float(row.get("metanet_nu_cong_km2_h", net.metanet_nu_cong_km2_h)),
    )


def install_freeway_fd_runtime(a, w, cfg, tuning=None) -> dict[str, float]:
    """Install after adapter segment/zones hooks, in parent and price workers.

    `a` is the canonical adapter module; `w` is src.controllers.wu_faithful_follower.
    The existing two-branch installer loads values into cfg.network first.
    Disabled configurations perform no mutations, even after another cfg enabled
    these process-wide wrappers. Every wrapper checks its own call's config/flag.
    """
    if not getattr(cfg.network, "vsl_fd_two_branch", False):
        return {"freeway_fd_consistent_enabled": 0.0}
    section = ((tuning or {}).get("freeway") or {}).get("two_branch") or {}
    if section.get("enabled") and "rho_crit_two_branch" not in section:
        raise ValueError("enabled two-branch FD requires explicit rho_crit_two_branch")
    cell_parameters(cfg.network)
    for link, rows in (getattr(cfg.network, "freeway_segment_params", {}) or {}).items():
        for index in range(len(rows)):
            cell_parameters(cfg.network, link, index)

    from src.models import metanet as mn, state as st

    if getattr(mn.effective_rho_crit, "_rw_consistent_two_branch", False):
        return {"freeway_fd_consistent_enabled": 1.0, "freeway_fd_consistent_installed": 0.0}

    old_sv = st.segment_vsl
    old_desired = mn.effective_desired_speed_kmh
    old_critical = mn.effective_rho_crit
    old_nu = mn.select_anticipation_nu
    old_release = w.WuFaithfulFollower._local_ramp_release

    def segment_vsl(control, link, index, cfg_):
        value = old_sv(control, link, index, cfg_)
        if not getattr(cfg_.network, "vsl_fd_two_branch", False):
            return value
        return _segment_value(value, cfg_, link, index)

    def effective_desired_speed_kmh(rho, v_free, rho_crit, vsl, alpha_vsl=0.0,
                                    vsl_active=True, a=1.867, two_branch=False,
                                    rho_jam=0.0, rho_crit_tb=0.0):
        if not two_branch:
            return old_desired(rho, v_free, rho_crit, vsl, alpha_vsl, vsl_active,
                               a, two_branch, rho_jam, rho_crit_tb)
        fd = vsl.fd if isinstance(vsl, SegmentVSL) else FDParameters(
            float(v_free), float(rho_crit_tb), float(rho_jam))
        fd.validate()
        return fd.desired_speed(rho, float(vsl), vsl_active)

    def effective_rho_crit(net, vsl):
        if not getattr(net, "vsl_fd_two_branch", False):
            return old_critical(net, vsl)
        if isinstance(vsl, SegmentVSL):
            return vsl.fd.critical(vsl, vsl.active)
        # Scalar diagnostics/buffer consumers have no cell identity or VSL set.
        # A cap above global free speed is naturally nonbinding after clamping.
        fd = cell_parameters(net)
        return fd.critical(net.v_free if vsl is None else vsl, vsl is not None)

    def select_anticipation_nu(rho, net, vsl=None):
        if not getattr(net, "vsl_fd_two_branch", False):
            return old_nu(rho, net, vsl)
        if isinstance(vsl, SegmentVSL):
            nu_free, nu_cong = vsl.nu_free, vsl.nu_cong
        else:
            nu_free, nu_cong = net.metanet_nu_km2_h, net.metanet_nu_cong_km2_h
        if a._FW_SEG_CTX.get('armed'):
            a._FW_SEG_CTX['response_rho_crit'] = effective_rho_crit(net, vsl)
        if getattr(net, "capacity_drop_anticipation", False) and rho > effective_rho_crit(net, vsl):
            return float(nu_cong)
        return float(nu_free)

    def local_ramp_release(self, link, rhos, ramp_queue, candidate_control, demand):
        net = self.cfg.network
        if not getattr(net, "vsl_fd_two_branch", False):
            return old_release(self, link, rhos, ramp_queue, candidate_control, demand)
        model = self._local_freeway_models[link]
        dt_h = self.cfg.simulation.T_f_h
        q_cap = net.freeway_capacity_veh_h * getattr(demand, "incident_capacity_factor", 1.0)
        release = {}
        for ramp in model.owned_ramps:
            index = model.ramp_merge_idx[ramp]
            rho = rhos[index] if index < len(rhos) else net.rho_crit
            value = segment_vsl(candidate_control, link, index, self.cfg)
            critical = effective_rho_crit(net, value)
            receiving = min(1.0, max(0.0, (net.rho_max - rho) / max(net.rho_max - critical, 1.0e-9)))
            cap = net.ramp_capacity_veh_h[ramp]
            requested = min(cap, max(0.0, candidate_control.ramp_metering.get(ramp, cap)))
            available = max(0.0, ramp_queue.get(ramp, 0.0) / max(dt_h, 1.0e-9))
            release[ramp] = min(available, cap, q_cap * receiving, requested)
        return release

    for name, old, new in (
        ("segment_vsl", old_sv, segment_vsl),
        ("effective_desired_speed_kmh", old_desired, effective_desired_speed_kmh),
        ("effective_rho_crit", old_critical, effective_rho_crit),
        ("select_anticipation_nu", old_nu, select_anticipation_nu),
    ):
        # Preserve existing adapter markers so its repeated installer does not
        # wrap these hooks again and overwrite the FD hooks on the next decision.
        new.__dict__.update(getattr(old, "__dict__", {}))
        if name == "segment_vsl" and getattr(cfg.network, "freeway_vsl_zone_head_of_cell", None):
            # The legacy segment wrapper masks the inner zone wrapper's marker.
            # A repeated zone install would remap cell9 to head5 *before* this
            # wrapper sees the cell, attaching head5's FD to cell9.
            new._rw_vsl_zone = True
        new._rw_consistent_two_branch = True
        a._fw_rebind(name, old, new)
    w.WuFaithfulFollower._local_ramp_release = local_ramp_release
    return {"freeway_fd_consistent_enabled": 1.0, "freeway_fd_consistent_installed": 1.0}
