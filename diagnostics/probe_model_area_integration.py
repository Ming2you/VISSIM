"""Audit projected stock via shared runtime setup, without running VISSIM."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import (
    detector_stock_supports, model_stock_values, physical_membership_from_ledger,
)


def replay_provenance(tuning, *inputs):
    """Pin loaded repository Python and transitively referenced config data."""
    paths = {Path(path).resolve() for path in inputs}
    paths.add(Path(__file__).resolve())
    for module in tuple(sys.modules.values()):
        source = getattr(module, '__file__', None)
        if source:
            path = Path(source).resolve()
            if path.suffix == '.py' and path.is_relative_to(ROOT):
                paths.add(path)
    visited = set()
    def visit(value):
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str) and value.startswith(('diagnostics/', 'evaluation/', 'outputs/', 'network/')):
            path = (ROOT/value).resolve()
            if path.is_relative_to(ROOT) and path.is_file() and path not in visited:
                visited.add(path)
                paths.add(path)
                if path.suffix == '.json':
                    visit(json.loads(path.read_text(encoding='utf-8-sig')))
    visit(tuning)
    return {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path):
            hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def route_information(state, cfg):
    """Stock coverage does not establish a vehicle's already chosen route."""
    from evaluation.controllers.route_choice_corridor import diagnostics
    observed = diagnostics(state, cfg)
    return {'route_choice_diagnostics': observed,
            'route_choice_information_complete': bool(observed['route_choice_prediction_route_complete']) if observed else None,
            'scope': 'Route-choice cohorts only; this does not validate signal service, travel time, or full-network predictive accuracy.'}


def build_projected(config_path: Path, state_path: Path, previous_path: Path, *, fixture_inputs=True):
    """Initialize canonical runtime; explicit probes opt out of fixture aliases."""
    if fixture_inputs:
        from diagnostics.review_fixtures import fixture_path
        return _build_projected(config_path, fixture_path(state_path), fixture_path(previous_path))
    for path in (config_path, state_path, previous_path):
        if not Path(path).is_file():
            raise FileNotFoundError(f'Explicit production replay input is missing: {path}')
    tuning = adapter.load_optional_json(str(config_path))
    writer = tuning.get('actuation', {}).get('real_world_signal_control', {}).get('offset_writer', 'intent_only')
    with patch.dict(os.environ, {'RW_OFFSET_WRITER': writer}):
        return _build_projected(config_path, state_path, previous_path)


def _build_projected(config_path, state_path, previous_path):
    tuning = adapter.load_optional_json(str(config_path))
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    state_json = adapter.load_optional_json(str(state_path))
    mapping = adapter.load_optional_json(str(ROOT / tuning["mapping_json"]))
    detector_mapping = adapter.load_optional_json(str(ROOT / tuning["detector_mapping_json"]))
    detector_mapping, _ = adapter.filter_midblock_links_from_detector_mapping(detector_mapping, tuning)
    _, DemandStep, ControlAction, _, TrafficState, _ = adapter.repo_imports(ROOT / "vendor/NumSim-mine")
    local_observation = bool(adapter._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = adapter.build_config(
        ROOT / "vendor/NumSim-mine", float(state_json["control_interval_sec"]),
        float(state_json["sim_period_sec"]), "fast-smoke", calibration, tuning,
        local_observation=local_observation, flagship=True,
    )
    adapter.install_adapter_calibration_fingerprints(cfg, tuning)
    from evaluation.controllers.runtime_setup import configure_runtime
    state, detector_mapping, metadata = configure_runtime(
        adapter, cfg, tuning, mapping, state_json, str(previous_path), detector_mapping,
        calibration, TrafficState, physical_projection_input=None)
    return cfg, state, detector_mapping, tuning, state_json, mapping, metadata


def main():
    run = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
    state_path = run / "state_000900.json"
    previous_path = run / "action_000001.json"
    config_path = ROOT / "evaluation/configs/n21_n7_20260908.json"
    cfg, state, detectors, tuning, raw, mapping, installers = build_projected(config_path, state_path, previous_path)
    ledger = json.loads((ROOT / "diagnostics/control_area_membership.json").read_text(encoding="utf-8"))
    physical = physical_membership_from_ledger(ledger)
    supports = detector_stock_supports(
        detectors, off_ramp_storage_links=cfg.network.off_ramp_storage_link,
        freeway_chains={key: row["chain_links"] for key, row in mapping["freeway_model_links"].items()},
    )
    stocks = model_stock_values(state, cfg.network, freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(state, cfg))
    totals, numbers, rows = Counter(), Counter(), []
    for key, count in stocks.items():
        support = supports.get(key, set())
        unknown = sorted(support - physical.keys())
        inside = sorted(link for link in support if physical.get(link) is True)
        outside = sorted(link for link in support if physical.get(link) is False)
        status = ("no_support" if not support else "unknown_physical" if unknown
                  else "mixed" if inside and outside else "inside" if inside else "outside")
        numbers[status] += 1
        if count > 1.0e-9:
            totals[status] += count
            row = {"key": key, "vehicles": count, "status": status, "inside_support": inside, "outside_support": outside, "unknown_support": unknown}
            if key.startswith("movement:"):
                spec = cfg.network.urban_movements[key.split(":", 1)[1]]
                row["movement"] = {k: spec.get(k) for k in ("kind", "origin", "receiving_link", "off_ramp", "beta", "intersection", "phase")}
            rows.append(row)
    full_counts = raw["vehicle_records"]["full_network_link_counts"]
    raw_inside = sum(float(v) for k, v in full_counts.items() if physical.get(str(k)) is True)
    raw_unknown = {k: v for k, v in full_counts.items() if str(k) not in physical}
    off_rows = []
    obs = raw["local_observation"]
    for off, branches in detectors["off_ramp_connectors"].items():
        for branch in branches:
            connector = str(branch["connector"])
            dest = str(branch["to_link"])
            off_rows.append({"off_ramp": off, **branch,
                "connector_inside": physical[connector], "destination_inside": physical[dest],
                "snapshot_connector_veh": full_counts.get(connector, 0),
                "snapshot_destination_veh": full_counts.get(dest, 0),
                "window_connector_departures": obs.get("link_departures_window", {}).get(connector),
                "far_connector_volume_veh_h": obs.get("far_measurement", {}).get("link_volume_veh_h", {}).get(connector),
            })
    output = {
        "state_path": str(state_path.relative_to(ROOT)), "config_path": str(config_path.relative_to(ROOT)),
        "adapter_sha256": hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),
        "membership_sha256": hashlib.sha256((ROOT / "diagnostics/control_area_membership.json").read_bytes()).hexdigest(),
        "membership_inside_links": sum(physical.values()),
        "installation_source": "shared runtime_setup.configure_runtime; validated against fixed 6056c94 main AST",
        "physical_projection_input": None, "installed_metadata": installers,
        "stock_inventory_count": len(stocks), "stock_count_by_membership": dict(numbers),
        "positive_stock_veh_by_membership": dict(totals), "raw_omega_vehicles": raw_inside,
        "raw_unknown_links": raw_unknown, "positive_stock_rows": sorted(rows, key=lambda row: (-row["vehicles"], row["key"])),
        "off_ramp_branches": off_rows,
    }
    # A reviewable projection-only candidate: existing runtime already separates
    # signal OR storage from direct tails. Give those existing stores their
    # physical observations, instead of counting connector traffic a second time.
    overrides = {
        "10491": "OR_D_W", "10638": "OR_F_W", "10481": "OR_D_E", "10643": "OR_F_E",
        "10479": "SC1001_W_tail", "10775": "SC1001_W_tail", "125": "SC1001_W_tail",
        "10645": "SC1004_W_tail", "10773": "SC1004_W_tail", "123": "SC1004_W_tail",
    }
    candidate_detectors = json.loads(json.dumps(detectors))
    for link, origin in overrides.items():
        candidate_detectors["link_to_origins"][link] = [origin]
        candidate_detectors["link_to_movements"].pop(link, None)
    from src.models.state import TrafficState
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    candidate_state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState, candidate_detectors, calibration, physical_projection_input=None)
    candidate_stocks = model_stock_values(candidate_state, cfg.network, freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(candidate_state, cfg))
    changes = [{"key": key, "before_veh": value, "after_veh": candidate_stocks[key], "delta_veh": candidate_stocks[key] - value}
               for key, value in stocks.items() if abs(candidate_stocks[key] - value) > 1.0e-9]
    output["projection_only_candidate"] = {
        "origin_overrides": overrides, "remove_movement_projection_on_overridden_links": True,
        "changes": changes, "before_total_model_stock": sum(stocks.values()), "after_total_model_stock": sum(candidate_stocks.values()),
        "note": "Only diagnostic copied detector mapping; no production cfg/adapter changes. Requires alias provenance update for agent observations before integration.",
    }
    observed_splits = {}
    for off in cfg.network.off_ramps:
        branches = [row for row in off_rows if row["off_ramp"] == off]
        samples = {str(row["connector"]): row["window_connector_departures"] for row in branches}
        if any(value is None for value in samples.values()) or sum(samples.values()) <= 0:
            observed_splits[off] = {"status": "unidentified", "counts": samples}
        else:
            observed_splits[off] = {"status": "observed_window_estimate", "counts": samples,
                                   "shares": {key: value / sum(samples.values()) for key, value in samples.items()},
                                   "sample_total": sum(samples.values())}
    output["observed_offramp_branch_shares"] = observed_splits
    out_path = ROOT / "diagnostics/model_area_integration_probe.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("stock_inventory_count", "stock_count_by_membership", "positive_stock_veh_by_membership", "raw_omega_vehicles", "raw_unknown_links")}, indent=2))
    print("off_ramp_branches", json.dumps(off_rows, ensure_ascii=True))
    print("projection_only_candidate", json.dumps(output["projection_only_candidate"], ensure_ascii=True))
    print("observed_offramp_branch_shares", json.dumps(observed_splits, ensure_ascii=True))


if __name__ == "__main__":
    main()
