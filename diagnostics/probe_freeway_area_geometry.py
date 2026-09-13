"""Compare observed FW geometry with the stock used by actual model continuity."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import area_freeway_accounting as accounting
from evaluation.controllers.control_area_objective import ModelAreaLedger
from src.models import metanet
from src.models.demand import DemandStep
from src.models.state import ControlAction


def totals(counts):
    return {key: sum(row) for key, row in counts.items()}


def main():
    run = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
    cfg, state, _, _, raw, _, _ = build_projected(
        ROOT / "evaluation/configs/n21_n7_20260908.json", run / "state_000900.json", run / "action_000001.json")
    action = ControlAction.uncontrolled(cfg)
    demand = adapter.demand_from_state(raw, cfg, DemandStep, 1)[0]
    physical_before = totals(adapter._freeway_vehicle_count_by_link(state, cfg))
    continuity_before = totals(accounting.continuity_vehicle_counts(state, cfg))
    lanes_before = {key: list(value) for key, value in state.freeway_effective_lanes.items()}
    original = state.copy()
    kwargs = dict(update_ramp_queues=False, ramp_release_veh_h={})
    reference = metanet.freeway_substep(original, action, demand, cfg, **kwargs)
    seed = {f"freeway:{key}": {"inside": value} for key, value in continuity_before.items()}
    seed.update({f"origin:{key}": {"outside": value} for key, value in state.mainline_origin_queue.items()})
    state._control_area_ledger = ModelAreaLedger(seed)
    cfg.network.control_area_enabled = True
    result = accounting._freeway_substep_events(state, action, demand, cfg, **kwargs)
    assert reference == result
    assert {k: v for k, v in vars(state).items() if k != "_control_area_ledger"} == vars(original)
    ledger = state._control_area_ledger
    for off in cfg.network.off_ramps:
        amount = result[1][f"offramp_flow_{off}"] * cfg.simulation.T_f_h
        ledger.transfer(f"freeway:{cfg.network.off_ramp_from_freeway[off]}", f"storage:{off}", amount,
                        inside_to_inside=1.0, outside_to_inside=1.0)
    continuity_after = totals(accounting.continuity_vehicle_counts(state, cfg))
    physical_after = totals(adapter._freeway_vehicle_count_by_link(state, cfg))
    rows = {}
    for link in cfg.network.freeway_links:
        row = {
            "raw_observed_count": sum(row["count"] for row in raw["freeway_segments"][link]),
            "raw_observed_cell_lengths_km": sorted(set(row["length_km"] for row in raw["freeway_segments"][link])),
            "legacy_helper_stock_before": physical_before[link],
            "continuity_stock_before": continuity_before[link],
            "initial_gap_veh": physical_before[link] - continuity_before[link],
            "legacy_helper_stock_after": physical_after[link],
            "continuity_stock_after": continuity_after[link],
            "ledger_stock_after": sum(ledger.stocks[f"freeway:{link}"].values()),
            "continuity_conservation_residual_veh": continuity_after[link] - sum(ledger.stocks[f"freeway:{link}"].values()),
            "legacy_helper_delta_minus_actual_flux_veh": (physical_after[link] - physical_before[link]) - (continuity_after[link] - continuity_before[link]),
            "scalar_length_km": cfg.network.freeway_segment_length_km,
            "physical_cell_lengths_km": adapter._freeway_segment_lengths_km(cfg, link, len(state.freeway_density[link])),
            "observation_physical_lanes": getattr(state, "freeway_lanes", {}).get(link),
            "continuity_lanes_before": lanes_before[link],
            "continuity_lanes_after": state.freeway_effective_lanes[link],
        }
        rows[link] = row
    output = {"source_state": str((run / "state_000900.json").relative_to(ROOT)),
              "config": "evaluation/configs/n21_n7_20260908.json",
              "scope": "one Tf=10s; existing n7 runtime; zero ramp releases; off transfers dispatched after freeway step",
              "extracted_state_matches_original": True, "rows": rows}
    path = ROOT / "diagnostics/freeway_area_geometry_audit.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: {k: v for k, v in row.items() if not isinstance(v, list)} for key, row in rows.items()}, indent=2))


if __name__ == "__main__":
    main()
