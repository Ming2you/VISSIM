"""Separate existing52 head budget, ready-queue supply and receiving losses."""
import ast
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc, obs150_signal_clock as clock, obs150_head_window as hw


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    protocol = read(HERE / "protocol.json")
    integration = ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926"
    output = integration / "closedloop_recorded2700_select_check_trace10681_sc1004_response47"
    previous = Path(protocol["expected_reference"])
    audit_path = integration / "closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json"
    audit = read(audit_path)
    result = dict(status="complete_not_gain_qualified", forecasts=2, new_native_runs=0, new_fit=0,
                  fzp_rescans=0, optimizer_calls=0, future_forecast_inputs=False, arms={},
                  wall_forecasts_sec=0., previous_outputs_exact=True, source_pins_unchanged=True,
                  input_sha256={str(audit_path): hashlib.sha256(audit_path.read_bytes()).hexdigest()})
    for path, expected in protocol["production_pins"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    movements = ("SC1004_E_SC1005_to_W", "SC1004_E_SC107_to_W")
    for arm, native in (("held_actual", "hold"), ("selected", "selected")):
        current, old = read(output / (arm + ".json")), read(previous / (arm + ".json"))
        result["wall_forecasts_sec"] += current.pop("wall_sec")
        old.pop("wall_sec")
        assert current == old, arm
        name = arm + "_RM_C10681_trace.json.gz"
        trace = json.loads(gzip.decompress((output / name).read_bytes()))
        before = json.loads(gzip.decompress((previous / name).read_bytes()))
        extra = trace.pop("upstream_diagnostics")
        assert trace == before, arm
        service_rate = extra["head_resources"]["10629"]["installed_pool"]["service_veh_h"]
        assert service_rate > 0
        result["input_sha256"][str(output / name)] = hashlib.sha256((output / name).read_bytes()).hexdigest()
        per_step = defaultdict(dict)
        for row in extra["resources"]:
            if row["resource"] == "10629" or row["resource"] in movements:
                key = (row["kind"], row["resource"])
                assert key not in per_step[row["start_sec"]]
                per_step[row["start_sec"]][key] = row
        paths = sorted(Path(p) for p in audit["input_sha256"] if native in Path(p).parts)
        windows = []
        for index, path in enumerate(paths[1:]):
            assert hashlib.sha256(path.read_bytes()).hexdigest() == audit["input_sha256"][str(path)]
            result["input_sha256"][str(path)] = audit["input_sha256"][str(path)]
            raw = read(path)
            start, end = raw["sim_sec"] - 150, raw["sim_sec"]
            row = dict(start_sec=start, end_sec=end, model_green_sec=0., model_head_budget=0.,
                       model_actual=0., model_pre_head_shortfall=0., model_post_head_shortfall=0.,
                       model_green_low_queue_steps=0, model_queue_arrival=0., model_10565_flow=0.)
            for t, records in per_step.items():
                if not start <= t < end:
                    continue
                head = records["regular_shared_head", "10629"]
                cap, accepted = head["available_veh"], head["accepted_total_veh"]
                intended = sum(records["urban_movement_intended_limit", m]["available_veh"] for m in movements)
                queue = sum(records["urban_movement_stock", m]["available_veh"] for m in movements)
                row["model_green_sec"] += cap / service_rate * 3600
                row["model_head_budget"] += cap
                row["model_actual"] += accepted
                row["model_pre_head_shortfall"] += max(0., cap - intended)
                row["model_post_head_shortfall"] += max(0., min(cap, intended) - accepted)
                row["model_green_low_queue_steps"] += bool(cap > 0 and queue < cap)
            for transfer in extra["transfers"]:
                if start <= transfer["start_sec"] < end:
                    if transfer["target"] in tuple("movement:" + m for m in movements):
                        row["model_queue_arrival"] += transfer["vehicles"]
                    if transfer["source"] == "movement:SC1005_N_SC105_to_W_SC1004" and transfer["target"] == "storage:SC1005_to_SC1004":
                        row["model_10565_flow"] += transfer["vehicles"]
            assert abs(row["model_head_budget"] - row["model_actual"] - row["model_pre_head_shortfall"] - row["model_post_head_shortfall"]) < 1e-9
            obs = raw["obs150"]
            bundle = oc.load_bundle(raw)
            assignment = oc.assign_window(obs, bundle.mer_rows)
            detectors, _ = oc.read_detector_csv(obs["detector_config"]["path"], obs["detector_config"]["sha256"])
            sig = Path(raw["network_path"]).parent / "개포동 test-bed1004_n4dr150.sig"
            result["input_sha256"][str(sig)] = hashlib.sha256(sig.read_bytes()).hexdigest()
            signal_log = {**obs["signal_log"], "scs": ["1004"],
                "start": {k: v for k, v in obs["signal_log"]["start"].items() if k.startswith("1004-")},
                "events": [e for e in obs["signal_log"]["events"] if e[1] == "1004"]}
            clocks = clock.windows(signal_log, {"1004": clock.sig_program_from_file("1004", sig, 1)}, obs["window"], network_dir=sig.parent)
            sg = clocks["1004-6"]
            assert sg["complete"] and sg["unverified_sec"] == 0
            counts = dict(green=0, not_green=0, ambiguous=0)
            for detector in detectors:
                if detector.role == "head" and detector.link == 52 and detector.lane in (1, 2, 3):
                    assert assignment.tails[detector.dcp_no] == 0
                    classified, _ = hw.classify_entries(bundle.mer_rows, assignment.entries[detector.dcp_no], sg["green"], (start, end))
                    for key, value in classified.items():
                        counts[key] += value
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            row.update(native_head_classification=counts, native_green_intervals=sg["green"],
                       native_green_sec=sum(b-a for a,b in sg["green"]), native_10565_flow=boundaries["headfree:10565"].cross,
                       model_queue_initial=sum(extra["states"][index]["queues"][m] for m in movements),
                       model_queue_final=sum(extra["states"][index+1]["queues"][m] for m in movements))
            assert abs(row["model_queue_initial"] + row["model_queue_arrival"] - row["model_actual"] - row["model_queue_final"]) < 1e-8
            windows.append(row)
        result["arms"][arm] = dict(head_resource=extra["head_resources"]["10629"], windows=windows)
    driver = integration / "probe_selected_arrival_path.py"
    before_ast = ast.parse((HERE / "driver_before.txt").read_text(encoding="utf-8"))
    after_ast = ast.parse(driver.read_text(encoding="utf-8"))
    funcs = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    a, b = funcs(before_ast), funcs(after_ast)
    changed = [key for key in a.keys() | b.keys() if a.get(key) != b.get(key)]
    assert changed == ["probe_levers"], changed
    result["driver_changed_functions"] = changed
    result["driver_sha256"] = hashlib.sha256(driver.read_bytes()).hexdigest()
    (HERE / "driver_executed.txt").write_bytes(driver.read_bytes())
    (HERE / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("arms", "input_sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
