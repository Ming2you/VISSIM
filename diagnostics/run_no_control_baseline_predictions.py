"""Fresh-process, 60-second bounded calls to the installed fidelity probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "evaluation/runs/codex_nc5400_r01_baseline_s13"
CONFIG = ROOT / "diagnostics/contract_observer_off_configs_v3/n7_area_beta0.json"
CONFIG_SHA = "201b7b6d5c759736201dd9a08b036dd3cd4891501a9d2de922b59651d3fd910d"
PROBE = ROOT / "diagnostics/probe_corrected_prediction_fidelity.py"
OUT = ROOT / "diagnostics/no_control_5400_baseline_prediction_v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory(inputs):
    paths = {Path(p).resolve() for p in inputs}
    paths.update((ROOT / "evaluation/controllers").glob("*.py"))
    paths.update((ROOT / "vendor/NumSim-mine/src").rglob("*.py"))
    paths.update((ROOT / "plant/src").rglob("*.py"))
    paths.update((ROOT / "diagnostics").glob("*.py"))
    visited = set()
    def visit(value):
        if isinstance(value, dict):
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)
        elif isinstance(value, str) and value.startswith(("diagnostics/", "evaluation/", "outputs/", "network/")):
            path = (ROOT / value).resolve()
            if path.is_file() and path.is_relative_to(ROOT) and path not in visited:
                visited.add(path)
                paths.add(path)
                if path.suffix == ".json":
                    visit(json.loads(path.read_text(encoding="utf-8-sig")))
    visit(json.loads(CONFIG.read_text(encoding="utf-8-sig")))
    return {str(p.resolve()): sha(p) for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", type=int, choices=(900, 1500, 2700, 4500), required=True)
    args = parser.parse_args()
    if sha(CONFIG) != CONFIG_SHA:
        raise ValueError("Use the original201b NC model configuration unchanged")
    folder = RUN / ("decisions_" + RUN.name)
    snapshot = folder / ("state_000900.json" if args.anchor == 900 else f"anchor_{args.anchor:06d}.json")
    previous = folder / ("action_000001.json" if args.anchor == 900 else "action_000900.json")
    action = folder / "action_000900.json"
    segments = RUN / ("bottleneck_segments_" + RUN.name + ".csv")
    raw = json.loads(snapshot.read_text(encoding="utf-8-sig"))
    if raw["sim_sec"] != args.anchor or raw["control_interval_sec"] != 150:
        raise ValueError("Unexpected actual snapshot/horizon")
    OUT.mkdir(exist_ok=True)
    case = OUT / f"t{args.anchor:04d}"
    case.mkdir(exist_ok=False)
    before = inventory([Path(__file__), PROBE, CONFIG, snapshot, previous, action])
    future_stat = (segments.stat().st_size, segments.stat().st_mtime_ns)
    command = [sys.executable, "-B", "-X", "utf8", str(PROBE), "--config", str(CONFIG), "--snapshot", str(snapshot),
               "--previous", str(previous), "--action", str(action), "--segments", str(segments), "--output", str(case / "prediction.json")]
    evidence = {"anchor_sec": args.anchor, "horizon_sec": 150, "command": command, "cwd": str(ROOT),
                "timeout_sec": 60, "RW_environment": {k: v for k, v in os.environ.items() if k.startswith("RW_")},
                "source_sha256_before": before, "future_CSV_pre_prediction_metadata_only": future_stat,
                "scope": "Installed run() uses an actual snapshot and action JSON; no search or newly computed control. Future CSV observations are read inside run() only after endpoint completion."}
    save(case / "invocation.json", evidence)
    started = time.perf_counter()
    with (case / "stdout.txt").open("wb") as stdout, (case / "stderr.txt").open("wb") as stderr:
        try:
            child = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=60)
            evidence["exit_code"] = child.returncode
            evidence["status"] = "endpoint_completed" if child.returncode == 0 else "failed_preserved_no_source_repair"
        except subprocess.TimeoutExpired:
            evidence.update(status="timeout_child_killed_and_waited", exit_code=None)
    evidence["elapsed_sec"] = time.perf_counter() - started
    evidence["source_changes"] = [p for p, h in before.items() if sha(p) != h]
    evidence["future_CSV_stat_unchanged"] = future_stat == (segments.stat().st_size, segments.stat().st_mtime_ns)
    if evidence["source_changes"] or not evidence["future_CSV_stat_unchanged"]:
        evidence["status"] = "source_or_validation_input_changed"
    if evidence["status"] == "endpoint_completed":
        result = json.loads((case / "prediction.json").read_text(encoding="utf-8-sig"))
        source_rows = {(ROOT / p).resolve(): h for p, h in result["source_sha256"].items()}
        # The future observations have a metadata guard until after prediction;
        # their content SHA is then recorded by the original probe.
        uncovered = [str(p) for p in source_rows if str(p) not in before and p != segments.resolve()]
        mismatches = [str(p) for p, h in source_rows.items() if str(p) in before and before[str(p)] != h]
        evidence.update(probe_loaded_source_prehash_uncovered=uncovered, probe_source_pin_mismatches=mismatches,
                        prediction_sha256=sha(case / "prediction.json"))
        if uncovered or mismatches:
            evidence["status"] = "endpoint_completed_source_coverage_requires_review"
    save(case / "invocation.json", evidence)
    print(json.dumps({k: evidence.get(k) for k in ("anchor_sec", "status", "elapsed_sec", "exit_code", "source_changes", "probe_loaded_source_prehash_uncovered", "probe_source_pin_mismatches")}), flush=True)
    return 0 if evidence["status"] == "endpoint_completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
