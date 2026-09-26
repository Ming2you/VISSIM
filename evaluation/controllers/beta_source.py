"""Complete routing-beta sources (urban.beta.source) and the runtime consistency guards they require.

A complete source (scripts/derive_routing_beta_physical.py, 2026-09-25) gives every runtime movement a beta
(0 without a physical path, otherwise its static-route relFlow share) and every approach sums to 1 BEFORE any
runtime renormalisation. With such a source the steps that move or renormalise beta afterwards must be no-ops:
  - install_leg_ramp_split_fold      folds non-kept on-ramp movements onto W_out / siblings   -> their beta is 0
  - install_merged_movements         merges exit twins, drops own-leg U-turns, renormalises    -> sums already 1
  - install_offramp_direct_landing   zeroes *_to_W_RAMP / *_to_W and renormalises siblings    -> already 0
  - area_dynamic_routes.configure    removes an own-leg U-turn and installed the offline NC13 prior (a realised
                                     share) on the retained branches -> the U-turn is 0 and the retained
                                     branches keep the table (relFlow) values, which must carry the approach
  - apply_dead_phase_beta_zero       (urban.movements.dead_phase_beta_zero, off in SDMPC-31; the call after the
                                     measured beta) zeroes dead-phase movements and renormalises per origin
                                     -> their beta is 0 and the sums are already 1. It judges the DECLARED phases
                                     before the physical phase authority, so with a complete source it would move the
                                     relFlow share of SC7 E / E_SC16 -> N_SC11 (declared p3, served in p4):
                                     install_measured_turn_beta refuses the switch with a complete source (2026-09-26);
                                     check_complete_beta_runtime covers green on the runtime phases
Each of them calls the guards below, which do nothing unless the configured source is complete. The adapter's
install_measured_turn_beta decides "complete" with the same predicate (complete_beta_source) and refuses a
disagreement, and requires the tuning's movement declaration (urban.movements.nonexistent_declaration) and phase
authority (urban.movements.physical_phase_authority, phase_correction, merge_exits) to be the ones the table was
derived with (2026-09-26: the v3b declaration makes SC7 E / E_SC16 -> N_SC11 exist, served in their head's phase p4);
check_complete_beta_runtime then compares the table's network with the snapshot, the runtime's flowless phases with
the derivation's, and refuses flow in a phase without native green in the selected plan.
NOT covered (open, see PLANT_PORTING_GUIDE.md): urban.sc2001_corridor splits the link-78 outflow (to the R_D_E /
R_D_W ramps and outside_125) by its own offline NC13 completed-cohort prior (scenario/sc2001_corridor_nc13_2d0c62.json,
a realised share of another network lineage). No relFlow applies there (no routing decision on 78 / 10703 / 10774 /
124); what value it should carry is a user decision.
route_choice_corridor.configure (keep += removed) is NOT guarded: it runs after configure_topology_repair, which
rewrites SC107 S from its own pinned relFlow evidence (primary route x continuation, e.g. SC107_S_to_W_SC1004), and
the corridor then merges that designed split back. The complete table itself gives every removed twin 0.
The switch is the existing config key urban.beta.source (no new flag, no environment variable).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

COMPLETE_BETA_SOURCES = frozenset({"routing_v3b2"})
COMPLETE_BETA_SCHEMA = "movement_beta_routing_physical/v1"
COMPLETE_BETA_TOL = 1.0e-9


def _section(tuning: Mapping[str, Any] | None) -> Mapping[str, Any]:
    urban = (tuning or {}).get("urban") if isinstance(tuning, Mapping) else None
    beta = urban.get("beta") if isinstance(urban, Mapping) else None
    return beta if isinstance(beta, Mapping) else {}


def is_enabled_value(flag: Any) -> bool:
    """The adapter's _is_enabled_value (vissim_stackelberg_adapter.py): bool as is, a number != 0, or one of the
    strings 1/true/yes/on. Duplicated here (the adapter imports this module) and pinned equal by a test."""
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, (int, float)):
        return float(flag) != 0.0
    return str(flag).strip().lower() in {"1", "true", "yes", "on"}


def complete_beta_source(tuning: Mapping[str, Any] | None) -> bool:
    """urban.beta.measured is on (the adapter's predicate) and urban.beta.source names a complete source."""
    section = _section(tuning)
    return is_enabled_value(section.get("measured")) and str(section.get("source") or "") in COMPLETE_BETA_SOURCES


def require_zero_moved_beta(tuning: Mapping[str, Any] | None, where: str, moved: Mapping[str, Any]) -> None:
    """With a complete source, beta that the runtime moves onto another movement must be 0."""
    if not complete_beta_source(tuning):
        return
    bad = {str(m): float(v or 0.0) for m, v in moved.items() if abs(float(v or 0.0)) > COMPLETE_BETA_TOL}
    if bad:
        raise ValueError("%s: complete beta source moves a non-zero share: %s" % (where, sorted(bad.items())[:6]))


def require_unit_approach_sums(tuning: Mapping[str, Any] | None, where: str, specs: Mapping[str, Any]) -> None:
    """With a complete source, every approach sums to 1 before renormalisation (the renormalisation is identity)."""
    if not complete_beta_source(tuning):
        return
    sums: dict[tuple[str, str], float] = {}
    for spec in specs.values():
        if not isinstance(spec, Mapping):
            continue
        key = (str(spec.get("signal", "")), str(spec.get("approach", "")))
        sums[key] = sums.get(key, 0.0) + float(spec.get("beta") or 0.0)
    bad = {"%s|%s" % k: v for k, v in sums.items() if abs(v - 1.0) > COMPLETE_BETA_TOL}
    if bad:
        raise ValueError("%s: complete beta source approach sums differ from 1 before renormalisation: %s"
                         % (where, sorted(bad.items())[:6]))
