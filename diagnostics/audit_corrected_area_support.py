"""Quantify actual positive model stock support after the proposed observation fix."""
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "diagnostics")]
from test_observation_projection import ActualInstalledProjection
from evaluation.controllers import observation_projection
from evaluation.controllers.control_area_objective import detector_stock_supports, model_stock_values, physical_membership_from_ledger, projection_stock_cohorts


def main():
    ActualInstalledProjection.setUpClass()
    harness = ActualInstalledProjection
    adapter = harness.adapter
    from src.models.state import TrafficState
    physical = physical_membership_from_ledger(json.loads((ROOT / "diagnostics/control_area_membership.json").read_text(encoding="utf-8")))
    nc = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
    n7 = sorted((ROOT / "evaluation/runs/codex_n7_s13_6056c94_20260909").rglob("state_*.json"))
    cases = [nc / "state_000900.json"] + ([n7[-1]] if n7 else [])
    output = []
    for path in cases:
        cfg, _, detectors, tuning, raw, mapping, _ = harness.build_projected(harness.config_path, path, nc / "action_000001.json")
        detectors, metadata = observation_projection.install_physical_branch_projection(cfg, harness.overlay, detectors, link_counts=adapter._link_counts_from_local_observation(raw))
        calibration = adapter.deep_update(dict(harness.calibration), tuning.get("calibration_override", {}))
        with patch.object(adapter, "build_local_observation_summary", harness.patched_summary):
            state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState, detectors, calibration)
        supports = detector_stock_supports(detectors, off_ramp_storage_links=cfg.network.off_ramp_storage_link,
                                          freeway_chains={k: v["chain_links"] for k, v in mapping["freeway_model_links"].items()})
        stocks = model_stock_values(state, cfg.network, freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(state, cfg))
        cohorts = projection_stock_cohorts(state.local_observation_summary["projection_diagnostics"]["physical_stock_assignment_by_link"], physical)
        observed_counts = adapter._link_counts_from_local_observation(raw)
        counts, positive_counts, positive_total, active_total, rows = Counter(), Counter(), Counter(), Counter(), []
        for key, vehicles in stocks.items():
            support = supports.get(key, set())
            unknown = support - physical.keys()
            inside, outside = sorted(k for k in support if physical.get(k) is True), sorted(k for k in support if physical.get(k) is False)
            status = "no_support" if not support else "unknown_physical" if unknown else "mixed" if inside and outside else "inside" if inside else "outside"
            counts[status] += 1
            if vehicles <= 1e-9:
                continue
            positive_counts[status] += 1
            positive_total[status] += vehicles
            if status in {"mixed", "no_support", "unknown_physical"}:
                row = {"stock": key, "veh": vehicles, "status": status, "inside_links": inside, "outside_links": outside}
                row["active_inside_links"] = {k: observed_counts.get(k, 0) for k in inside if observed_counts.get(k, 0) > 0}
                row["active_outside_links"] = {k: observed_counts.get(k, 0) for k in outside if observed_counts.get(k, 0) > 0}
                active_status = "active_mixed" if row["active_inside_links"] and row["active_outside_links"] else "active_inside_only" if row["active_inside_links"] else "active_outside_only" if row["active_outside_links"] else "no_active_support"
                row["active_support_status"] = active_status
                active_total[active_status] += vehicles
                if key.startswith("movement:"):
                    row["movement_spec"] = cfg.network.urban_movements[key.split(":", 1)[1]]
                rows.append(row)
        output.append({"state": str(path.relative_to(ROOT)), "membership_inside_links": sum(physical.values()),
                       "all_stock_count": dict(counts), "positive_stock_count": dict(positive_counts), "positive_stock_veh": dict(positive_total),
                       "static_mixed_veh_by_active_support": dict(active_total),
                       "total_projected_veh": sum(stocks.values()), "raw_omega_veh": sum(v for k, v in raw["vehicle_records"]["full_network_link_counts"].items() if physical[k]),
                       "omega_projected_initial_stock_veh": sum(row["inside"] for row in cohorts.values()) + sum(v for k, v in stocks.items() if k.startswith("freeway:")),
                       "actual_initial_mixed_cohorts": {k: v for k, v in cohorts.items() if v["inside"] > 1e-9 and v["outside"] > 1e-9},
                       "unsupported_positive_stocks": sorted(rows, key=lambda r: -r["veh"]),
                       "branch_metadata": metadata})
    target = ROOT / "diagnostics/corrected_area_support.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in output:
        print(json.dumps({k: v for k, v in row.items() if k not in {"unsupported_positive_stocks", "branch_metadata"}}, ensure_ascii=True))
        print("top_unsupported", json.dumps(row["unsupported_positive_stocks"][:8], ensure_ascii=True))


if __name__ == "__main__":
    main()
