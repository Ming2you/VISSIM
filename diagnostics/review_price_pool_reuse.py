"""Inspect completed trace/profile files; never import a runtime controller."""
from __future__ import annotations
import hashlib
import json
import pstats
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T035232419561Z/evaluation_trace"
PROFILE = ROOT / "diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/profile"
SOURCE_PATHS = ["vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py",
                "vendor/NumSim-mine/src/controllers/priced_wu_link_controller.py",
                "diagnostics/evaluation_trace.py", "diagnostics/decision_profile.py"]


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def main():
    before = {p: digest_bytes((ROOT/p).read_bytes()) for p in SOURCE_PATHS}
    kinds = Counter()
    first_files = {}
    input_hashes = {}
    for stream in sorted(TRACE.glob("evaluation_*.jsonl")):
        with stream.open(encoding="utf-8") as f:
            first = json.loads(f.readline())
        if first["kind"] != "price_task":
            continue
        kind = first["source"]["qualname"]
        kinds[kind] += 1
        first_files.setdefault(kind, stream.with_suffix(".json"))
    samples = {}
    for kind, path in sorted(first_files.items()):
        raw = path.read_bytes()
        input_hashes[path.relative_to(ROOT).as_posix()] = digest_bytes(raw)
        trace = json.loads(raw)
        first = next(r for r in trace["rows"] if r["kind"] == "price_task" and r["event"] == "enter")
        context = trace["contexts"][first["context"]]
        ctrl = dict(context["controller"]["mapping"])
        samples[kind] = {
            "file": path.relative_to(ROOT).as_posix(), "context": first["context"],
            "value_digests": {k: digest(context[k]) for k in ("cfg", "state", "forecast", "controller")},
            "previous_digest": digest(first["input"].get("previous")),
            "controller_fields": sorted(ctrl),
            "controller_field_digests": {k: digest(v) for k,v in ctrl.items()},
            "captured_controller_is_complete": False,
            "missing_operational_fields": ["_prev_coupling", "_wu._last_offramp_flow", "_wu._has_last_offramp_flow"],
            "valid": trace["valid"], "source_changes": trace["source_changes"],
        }
    base = samples.get("_price_worker_green")
    if base:
        for value in samples.values():
            value["captured_controller_fields_different_from_green"] = sorted(k for k,v in value["controller_field_digests"].items()
                if base["controller_field_digests"].get(k) != v)
    counts = Counter()
    calls = defaultdict(list)
    worker_files = []
    bootstrap_unprofiled = []
    for path in sorted(PROFILE.glob("process_*.json")):
        if path.name.endswith(".started.json"):
            continue
        side = json.loads(path.read_bytes())
        if side.get("pid") == 46556:
            continue
        stat_path = path.with_suffix(".pstats")
        if not stat_path.exists():
            continue
        worker_files.append(path.name)
        bootstrap_unprofiled.append(side.get("bootstrap_imports_before_profile"))
        raw = stat_path.read_bytes()
        input_hashes[stat_path.relative_to(ROOT).as_posix()] = digest_bytes(raw)
        stats = pstats.Stats(str(stat_path)).stats
        for (filename,line,name),(primitive,total,self_time,cumulative,callers) in stats.items():
            tail = filename.replace("\\", "/").rsplit("/",1)[-1]
            if name in ("_price_worker_green", "_price_worker_offset_walk", "_price_worker_vsl", "_price_worker_phase"):
                counts[name] += total
            if name == "_price_worker_init" or (tail == "priced_wu_link_controller.py" and name == "__setstate__") or name == "install_price_worker_runtime_patches":
                calls[tail + ":" + name].append({"process":path.stem,"calls":total,
                    "self_profile_seconds":self_time,"inclusive_profile_seconds":cumulative})
    summary = {k:{"process_count":len(v),"calls":sum(x["calls"] for x in v),
                  "sum_inclusive_profile_seconds":sum(x["inclusive_profile_seconds"] for x in v),
                  "min_inclusive_profile_seconds":min(x["inclusive_profile_seconds"] for x in v),
                  "max_inclusive_profile_seconds":max(x["inclusive_profile_seconds"] for x in v)} for k,v in calls.items()}
    changes = [p for p,v in before.items() if digest_bytes((ROOT/p).read_bytes()) != v]
    assert changes == []
    report = {
        "schema_version":"decision-price-pool-reuse-review/v1", "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"existing files only; no new model, pool, controller or bootstrap execution",
        "source_sha256":before,"input_sha256":input_hashes,"source_changes":changes,
        "trace_worker_processes_by_kind":dict(kinds),"profile_worker_tasks_by_kind":dict(counts),
        "trace_first_worker_context_per_batch":samples,
        "worker_profile_count":len(worker_files),"worker_bootstrap_imports_before_profile":bootstrap_unprofiled,
        "profile_init_entries":summary,
        "timing_interpretation":"Worker inclusive times overlap each other and nested bootstrap entries; do not sum into saved wall time. Bootstrap imports preceded profiling. Parent shutdown attribution is invalid per prior thread-mixing audit.",
        "actual_serialized_initializer_bytes_available":False,
        "historical_comment_610KB_current_measurement":False,
        "proposal_status":"blocked_for_unqualified_pool_reuse; no production patch generated",
        "blockers":[
            "Four batches serialize the then-current full controller, not a single unchanged initializer payload; recorded controller price fields differ.",
            "V1 trace omits known mutable follower/coupling caches and does not capture full serialized initializer bytes or all process-global runtime state.",
            "Reusing only the first worker context would silently change later full payload; worker-count update tasks do not guarantee one update in every process.",
            "Per-epoch refresh requires task-bound epoch verification or per-task payload, repeat bootstrap isolation, ordered result reconstruction and cleanup/fallback parity; none has existing end-to-end evidence."
        ],
        "candidate_design":"decision-scoped process reuse only; keep batch barriers/task order; replace context from that batch's original full value snapshot on each worker before its first task; no follower candidate parallelization",
        "missing_next_gate":["full-value epoch payload and current pickle byte-size evidence", "same-process sequential bootstrap/global context parity", "exact all price task output comparison with fixed parent/worker hash seed", "failure and decision-finally cleanup proof"],
        "patch_written":False,"new_model_evaluations":0,
    }
    out=ROOT/'diagnostics/price_pool_reuse_review.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({"output":str(out),"worker_kinds":dict(kinds),"task_counts":dict(counts),"profile_init":summary,"source_changes":changes},ensure_ascii=False))


if __name__ == '__main__':
    main()
