"""Finish city-only289 from saved measurements; never launch or remeasure traffic."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
from diagnostics.fast_fixed_profile_verify import prefix_digest
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import (
    controlled_reuse_area, controlled_reuse_metadata,
)
from diagnostics.repin_v3c3_review_20261001.urban_rm269.qualify_native2400 import validate_scope


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    assert not path.exists(), f"Preserve existing result: {path}"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")


def prediction_metadata(city, authority):
    assert city["status"] == authority["status"] == "complete"
    assert (city["start_sec"], city["end_sec"]) == (2400, 2850)
    assert (authority["start_sec"], authority["end_sec"]) == (2400, 2850)
    assert city["application"]["state_error"] == 0
    assert city["application"]["same_forecast"] and city["application"]["same_current_source_pins"]
    assert set(city["results"]) == {"city_only", "rm_only"}
    hold = authority["results"]["hold"]["omega_ttt_veh_h"]
    selected = city["results"]["city_only"]["omega_ttt_veh_h"]
    assert math.isfinite(hold) and math.isfinite(selected)
    return dict(delta_omega_veh_h=selected - hold,
                delta_tracked_outside_veh_h=None)


def cached_arm(output, arm):
    metrics = read(output / arm / "area_metrics.json")
    execution = read(output / arm / "execution.json")
    assert execution["native_execution_passed"]
    assert metrics["sampling"]["nominal_step_sec"] == 5
    assert metrics["sampling"]["missing_snapshot_gaps"] == 0
    with (output / arm / "area_timeseries.csv").open(encoding="utf-8-sig", newline="") as f:
        times = list(csv.DictReader(f))
    at = next(r for r in times if abs(float(r["sim_sec"]) - 2400.1) < 1e-7)
    return dict(
        native_execution_passed=True,
        lsa_passed=execution["native_lsa_com_coverage_passed"],
        TTT_0_2850_veh_h=metrics["ttt_veh_h"],
        TTT_2400p1_2850_veh_h=metrics["ttt_veh_h"] - float(at["ttt_veh_h_cumulative"]),
        Omega_TTD_events=metrics["ttd_observed_plus_terminal_events"],
        Omega_end_vehicles=metrics["censored_last_observed_inside_vehicles"],
        outside_Omega_residence_veh_h=sum(r["ttt_veh_h"] for r in metrics["physical_link_residence"].values() if not r["inside"]),
        unresolved_Omega_disappearances=metrics["unresolved_inside_disappearances"],
    ), metrics


def main():
    plan = read(HERE / "plan.json")
    post = read(HERE / "postprocess_plan.json")
    output = Path(plan["analysis_output"])
    runtime = Path(plan["runtime"])
    protocol_path = Path(plan["protocol"])
    protocol = read(protocol_path)
    assert plan["native_dispatches"] == plan["analysis_attempts"] == 1
    failed = read(runtime / "analysis_status.json")
    assert failed["stage"] == "analysis_failed_no_retry" and failed["exit_code"] == 1
    failure_text = (runtime / "analysis.log").read_text(encoding="utf-8-sig")
    assert "controlled_reuse_metadata" in failure_text and "AssertionError" in failure_text
    assert not (output / "summary.json").exists()
    closure = read(output / "runtime_closure.json")
    assert closure["all_owned_processes_closed"] and closure["owner_exit_code"] == 0
    assert Path(closure["runs_root"]).resolve() == Path(plan["results_root"]).resolve()
    for path, digest in post["source_pins"].items():
        assert sha(path) == digest, path
    for path, digest in protocol["command_pins"].items():
        assert sha(path) == digest, path
    assert (protocol["start_sec"], protocol["end_sec"], protocol["seed"]) == (2400, 2850, 29)
    assert all(row["rm_vsl_held"] for row in protocol["physical_command_check"])
    city_source = Path(protocol["prediction_summary"])
    city = read(city_source)
    authority_path = Path(city["application"]["reused_hold"]) / "summary.json"
    authority = read(authority_path)
    assert str(authority_path) in city["source_pins"]
    assert sha(authority_path) == city["source_pins"][str(authority_path)]
    adapted = prediction_metadata(city, authority)
    prediction, limitations = controlled_reuse_metadata(protocol, adapted, 2850)
    a, am = cached_arm(output, "hold")
    b, bm = cached_arm(output, "selected")
    area_path = Path(post["argv"][-1])
    area = controlled_reuse_area(protocol, area_path)
    membership = read(area_path)
    assert membership["counts"]["inside_total"] == 701
    assert membership["network"]["sha256"] == protocol["network_sha256"]

    qualification = read(protocol["reuse_native_baseline"]["summary"])
    joint_path = Path(qualification["source_summary"])
    assert sha(joint_path) == qualification["source_summary_sha256"]
    joint = read(joint_path)
    audit_path = Path(qualification["scope_audit"])
    assert sha(audit_path) == qualification["scope_audit_sha256"]
    scope = validate_scope(joint, read(audit_path))
    assert joint["paired_prefix_exact"]
    assert joint["start_sec"] == 2400 and joint["end_sec"] == 2850
    baseline = Path(protocol["reuse_native_baseline"]["run"])
    native = Path(plan["results_root"]) / "selected"
    baseline_exec = read(output / "hold/execution.json")
    selected_exec = read(output / "selected/execution.json")
    assert Path(baseline_exec["run_directory"]).resolve() == baseline.resolve()
    assert Path(selected_exec["run_directory"]).resolve() == native.resolve()
    baseline_name = read(protocol["controlled_prefix"]["provenance"])["name"]
    selected_name = "sdmpc31_g_2400_selected_s29"
    baseline_decisions = baseline / f"decisions_{baseline_name}"
    selected_decisions = native / f"decisions_{selected_name}"
    left = read(baseline_decisions / "state_002400.json")
    right = read(selected_decisions / "state_002400.json")
    assert left["vehicle_records"]["complete"] and right["vehicle_records"]["complete"]
    assert left["vehicle_records"]["records"] == right["vehicle_records"]["records"]
    for sec in (1, *range(150, 2851, 150)):
        for suffix in ("json", "csv"):
            name = f"action_{sec:06d}.{suffix}"
            assert sha(selected_decisions / name) == sha(protocol_path.parent / "selected/commands" / name)
    # The failed report did not persist its prefix digest. Reuse the pinned HOLD
    # digest, and read only the new run's raw pre-2400 prefix; no traffic remeasure.
    fzp, = (native / "vissim_eval").glob("*.fzp")
    before = fzp.stat()
    prefix = prefix_digest(fzp, 2400, recording_grid=(5, .1))
    after = fzp.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    assert prefix == joint["prefixes"]["hold"] == joint["prefixes"]["selected"]
    save(output / "cached_prefix_qualification.json", dict(
        selected_prefix=prefix, reused_baseline_prefix=joint["prefixes"]["hold"],
        source_summary=str(joint_path), source_sha256=sha(joint_path),
        selected_fzp=str(fzp), size_bytes=after.st_size, mtime_ns=after.st_mtime_ns,
        common_start_vehicle_records_exact=True, paired_prefix_exact=True,
        new_full_traffic_measurements=0, new_precontrol_prefix_hash_reads=1,
        original_older_source_history_claimed=False,
    ))

    assert abs(a["TTT_0_2850_veh_h"] - joint["arms"]["hold"]["TTT_0_2850_veh_h"]) < 1e-8
    delta = b["TTT_0_2850_veh_h"] - a["TTT_0_2850_veh_h"]
    assert abs(delta - (b["TTT_2400p1_2850_veh_h"] - a["TTT_2400p1_2850_veh_h"])) < 1e-8
    model_joint = authority["results"]["selected"]["omega_ttt_veh_h"] - authority["results"]["hold"]["omega_ttt_veh_h"]
    native_joint = joint["delta_TTT_veh_h"]
    groups = {}
    for label, links in {"road68": [68], "upstream52_58": [52, 58], "road66": [66]}.items():
        value = lambda m: sum(m["physical_link_residence"].get(str(k), {}).get("ttt_veh_h", 0) for k in links)
        groups[label] = dict(links=links, delta_residence_veh_h=value(bm) - value(am),
                             scope="All vehicles on these physical links; not stopped-queue time.")
    summary = dict(
        status="complete_from_cached_measurements", start_sec=2400, end_sec=2850,
        scope="City-only minus held; same paired native initial history and Omega701.",
        counterfactual_valid=True, paired_prefix_exact=True, common_start_vehicle_records_exact=True,
        original_older_source_history_claimed=False, arms={"hold": a, "selected": b},
        delta_TTT_veh_h=delta,
        delta_outside_Omega_residence_veh_h=b["outside_Omega_residence_veh_h"] - a["outside_Omega_residence_veh_h"],
        **prediction, physical_area=area, local_physical_link_costs=groups,
        comparison=dict(
            native_city_minus_hold_veh_h=delta, model_city_minus_hold_veh_h=adapted["delta_omega_veh_h"],
            native_joint_minus_hold_veh_h=native_joint, model_joint_minus_hold_veh_h=model_joint,
            native_joint_minus_city_veh_h=native_joint - delta,
            model_joint_minus_city_veh_h=model_joint - adapted["delta_omega_veh_h"],
            rm_scope="Entire RM vector conditional on the joint city plan, not 10681-only.",
            full_native_factorial_available=False,
        ),
        baseline_qualification=scope, new_native_runs=0, new_forecasts=0,
        new_traffic_measurement_scans=0, new_precontrol_prefix_hash_reads=1,
        failed_analysis_preserved=str(runtime / "analysis_status.json"),
        metadata_repair="Map explicitly selected city_only minus pinned reused hold; preserve original protocol and predictions.",
        source_pins={str(path): sha(path) for path in (
            Path(__file__), protocol_path, city_source, authority_path, joint_path, audit_path,
            output / "hold/area_metrics.json", output / "selected/area_metrics.json",
            output / "hold/execution.json", output / "selected/execution.json",
            output / "runtime_closure.json", output / "cached_prefix_qualification.json",
        )},
        limitations=limitations + [
            "Native LSA coverage failure is preserved; LDP execution evidence was authorized.",
            "5-second sampled residence, final 4.9-second stock hold; no invented uninserted queue-time comparison.",
            "No current-command bonus, parameter fitting, changed demand, or changed area.",
            "A same-state city/RM decomposition is not independent-seed control robustness.",
        ],
    )
    save(output / "cached_summary.json", summary)
    print(json.dumps(summary["comparison"], ensure_ascii=False))


if __name__ == "__main__":
    main()
