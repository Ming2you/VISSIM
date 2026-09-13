"""Read completed evidence only; never import or execute a controller."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T035232419561Z"
PROFILE = ROOT / "diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/profile_summary.json"
OUTPUT = ROOT / "diagnostics/v1_trace_hierarchy_review.json"


def main():
    pins = {}

    def read(path):
        raw = path.read_bytes()
        pins[path.relative_to(ROOT).as_posix()] = sha256(raw).hexdigest()
        return raw

    manifest = json.loads(read(TRACE / "manifest.json"))
    comparison = json.loads(read(TRACE / "strict_result_comparison.json"))
    action = json.loads(read(TRACE / "action.json"))
    profile = json.loads(read(PROFILE))
    assert manifest["valid"] and manifest["evaluation_trace_validation"]["valid"]
    assert manifest["source_unchanged"] and manifest["inputs_unchanged"]
    assert not manifest["surviving_worker_pids"]
    assert comparison["csv_bytes_exact"] and comparison["returned_results_exact"]
    root_pid = manifest["adapter_pid"]
    all_counts = Counter()
    channels = defaultdict(lambda: {"worker_pids": set(), "tasks": 0, "endpoints": 0})
    hierarchy = []
    endpoints = Counter()
    parent_counts = Counter()
    for path in sorted((TRACE / "evaluation_trace").glob("evaluation_*.jsonl")):
        pid = int(path.stem.split("_")[-1])
        rows = [json.loads(line) for line in read(path).splitlines()]
        enters = {row["call"]: row for row in rows if row["event"] == "enter"}
        returns = {row["call"]: row for row in rows if row["event"] == "return"}
        assert enters.keys() == returns.keys(), path
        all_counts.update(row["kind"] for row in enters.values())
        if pid == root_pid:
            parent_counts.update(row["kind"] for row in enters.values())
        for call, row in enters.items():
            parent = row["parent_call"]
            assert parent is None or parent in enters
            if row["kind"] == "price_task":
                name = row["source"]["qualname"]
                channels[name]["worker_pids"].add(pid)
                channels[name]["tasks"] += 1
            if row["kind"] == "endpoint":
                endpoints["parent" if pid == root_pid else "workers"] += 1
                ancestor = row
                while ancestor["kind"] != "price_task" and ancestor["parent_call"] is not None:
                    ancestor = enters[ancestor["parent_call"]]
                if ancestor["kind"] == "price_task":
                    channels[ancestor["source"]["qualname"]]["endpoints"] += 1
            if pid == root_pid and row["kind"] in {
                "decision", "price_refresh", "phase_refresh", "price_batch",
                "leader_pfo", "leader_proxy", "leader_full", "follower",
            }:
                result = returns[call]["result"]
                item = {
                    "call": call, "parent_call": parent,
                    "kind": row["kind"], "source": row["source"],
                    "input_index": row["input"].get("index"),
                    "inclusive_trace_wall_sec": returns[call]["timing"]["inclusive_wall_ns"] / 1e9,
                    "result_sha256": sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                }
                if row["kind"] == "follower":
                    item["objective_value"] = result["objective_value"]
                    item["iterations"] = result["iterations"]
                hierarchy.append(item)
    assert all_counts["price_task"] == manifest["evaluation_trace_validation"]["worker_task_count"]
    assert endpoints == {"parent": 36, "workers": 153}
    repeated = []
    for filename, names in {
        "signal_actuation_contract.py": ("phase_fraction", "validate_vector", "written_offset_sec"),
        "native_input_prehead.py": ("_inputs", "_blocked", "_check"),
    }.items():
        for name in names:
            entry = {"file": filename, "function": name}
            for scope, rows in profile["functions"].items():
                hits = [r for r in rows if r["file"].endswith(filename) and r["function"] == name]
                assert len(hits) == 1
                entry[scope + "_calls"] = hits[0]["calls"]
            repeated.append(entry)
    selected = {key: action["metadata"][key] for key in (
        "meta_leader_candidate_proxy_evaluated_count", "meta_leader_candidate_full_evaluated_count",
        "meta_leader_fallback_evaluated_count", "meta_leader_fallback_guard_selected_pfo",
        "leader_objective", "nash_objective",
    )}
    selected["selected_follower_trace_diagnostic_sec"] = action["diagnostics"]["wu_faithful_solve_time_sec"]
    result = {
        "schema": "completed-v1-hierarchy-review/v1",
        "scope": "Read-only completed trace/profile analysis; no controller, optimizer, endpoint, or VISSIM execution.",
        "trace_root": TRACE.relative_to(ROOT).as_posix(),
        "root_pid": root_pid,
        "validation": manifest["evaluation_trace_validation"],
        "all_boundary_calls": dict(all_counts), "parent_boundary_calls": dict(parent_counts),
        "price_channels": {name: {**info, "worker_pids": sorted(info["worker_pids"])} for name, info in channels.items()},
        "outer_endpoint_calls": dict(endpoints), "parent_hierarchy": hierarchy,
        "selected_output": selected,
        "repeated_function_counts": repeated,
        "independent_profile_process_cpu_sec": {
            "parent": profile["completed_process_cpu_sec"] - profile["worker_cpu_sec"],
            "workers": profile["worker_cpu_sec"],
        },
        "returned_result_preservation": {
            "csv_bytes_exact": comparison["csv_bytes_exact"],
            "json_exact_outside_allowlist": comparison["returned_results_exact"],
            "excluded_paths": [x["path"] for x in comparison["provenance_or_timing_differences"]],
        },
        "limitations": [
            "All hierarchy durations are inclusive observer-overhead wall time, not normal stage estimates or removable cost.",
            "Follower calls are nested in PFO/full candidates; phase batch is nested in phase refresh and overall prices.",
            "Parent cProfile caller/self/inclusive attribution is invalid in this interpreter; parent flat counts include observed non-main threads.",
            "V1 does not isolate process/controller/worker initialization, serialization, shutdown, final writer, or every local candidate.",
            "One selected follower diagnostic is not the four follower solves or the whole decision.",
            "Candidate reduction, reordered execution, altered convergence, or physics changes are outside performance preservation scope.",
        ],
        "input_sha256": pins,
    }
    changed = [name for name, expected in pins.items() if sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    result["source_changes"] = changed
    result["producer_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "calls": dict(all_counts), "source_changes": changed}))


if __name__ == "__main__":
    main()
