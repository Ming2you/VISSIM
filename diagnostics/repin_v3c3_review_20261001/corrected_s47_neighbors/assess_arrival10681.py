"""Post-hoc SC1004 head -> 10681 arrival matching from pinned native MER caches.

Completed matches describe observed trips, not all turn demand or a causal
estimate. This does not feed future observations into a forecast.
"""
import hashlib
import gzip
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def assess():
    integration = ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926"
    source = integration / "closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json"
    audit = read(source)
    result = dict(source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  new_forecasts=0, new_native_runs=0, fzp_rescans=0, future_forecast_inputs=False,
                  arms={}, input_sha256={}, limitations=[
                      "Only completed head-to-ramp pairs; head passages to other destinations and arrivals after3150 are not classified as ramp demand.",
                      "History begins2550. Unmatched arrivals are retained, not assigned a guessed origin. Unsignalized turns may lack a head detector.",
                      "Detector entries at1m and physical ramp boundary are distinct; differences/tails are reported.",
                      "Lane identity is observed at endpoints; intervening lane changes are not identified.",
                      "Native completed travel time includes traffic delay; cannot alone identify a faulty model coefficient.",
                  ])
    for arm in ("hold", "selected"):
        paths = sorted(Path(p) for p in audit["input_sha256"] if arm in Path(p).parts)
        assert len(paths) == 4
        heads = defaultdict(list)
        windows = {}
        for path in paths:
            pin = hashlib.sha256(path.read_bytes()).hexdigest()
            assert pin == audit["input_sha256"][str(path)]
            result["input_sha256"][str(path)] = pin
            raw = read(path)
            bundle = oc.load_bundle(raw)
            obs = bundle.obs
            detectors, _ = oc.read_detector_csv(obs["detector_config"]["path"], obs["detector_config"]["sha256"])
            assignment = oc.assign_window(obs, bundle.mer_rows)
            for detector in detectors:
                if detector.role == "head" and detector.link in (52, 66, 46):
                    for row in assignment.entries[detector.dcp_no]:
                        heads[row.veh].append((row, detector))
            windows[raw["sim_sec"]] = (detectors, assignment)
        rows = []
        for end, (detectors, assignment) in windows.items():
            if end <= 2700:
                continue
            origins, lanes, head_count, head_tails = Counter(), Counter(), Counter(), Counter()
            source_lanes, lags, matches, unmatched = Counter(), defaultdict(list), [], []
            arrival_detectors = [d for d in detectors if d.role == "ramp_arrival" and d.link == 10681]
            assert len(arrival_detectors) == 2
            for detector in detectors:
                if detector.role == "head" and detector.link in (52, 66, 46):
                    head_count[f"{detector.link}:{detector.lane}"] = len(assignment.entries[detector.dcp_no])
                    head_tails[f"{detector.link}:{detector.lane}"] = assignment.tails[detector.dcp_no]
            seen = set()
            for detector in arrival_detectors:
                for row in assignment.entries[detector.dcp_no]:
                    key = (row.dcp, row.ordinal)
                    assert key not in seen
                    seen.add(key)
                    lanes[str(detector.lane)] += 1
                    past = [(h, d) for h, d in heads[row.veh] if h.t_entry <= row.t_entry]
                    if not past:
                        origins["unmatched"] += 1
                        unmatched.append(dict(veh=row.veh, arrival_time=row.t_entry, lane=detector.lane))
                        continue
                    head, d = max(past, key=lambda pair: pair[0].t_entry)
                    origins[str(d.link)] += 1
                    source_lanes[f"{d.link}->{detector.lane}"] += 1
                    lags[str(d.link)].append(row.t_entry - head.t_entry)
                    matches.append(dict(veh=row.veh, head_link=d.link, head_lane=d.lane,
                                        arrival_lane=detector.lane, head_time=head.t_entry,
                                        arrival_time=row.t_entry))
            actual = audit["arms"][arm]["RM_C10681"]["actual"]["windows"][int((end - 2850) / 150)]["arrival"]
            rows.append(dict(start_sec=end-150, end_sec=end, detector_arrivals=sum(lanes.values()),
                             native_boundary_arrivals=actual, detector_minus_boundary=sum(lanes.values())-actual,
                             origins=dict(origins), lanes=dict(lanes), source_lanes=dict(source_lanes),
                             head_counts_all_destinations=dict(head_count),
                             head_tails=dict(head_tails),
                             arrival_tails=sum(assignment.tails[d.dcp_no] for d in arrival_detectors),
                             completed_trip_lag_sec={k: dict(n=len(v), mean=statistics.mean(v),
                                                            median=statistics.median(v), minimum=min(v), maximum=max(v))
                                                     for k, v in lags.items()},
                             matches=matches, unmatched=unmatched))
        result["arms"][arm] = rows
        trace_path = integration / "closedloop_recorded2700_select_check_trace10681_sc1001_corrected47" / (
            ("held_actual" if arm == "hold" else arm) + "_RM_C10681_trace.json.gz")
        result["input_sha256"][str(trace_path)] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
        trace = json.loads(gzip.decompress(trace_path.read_bytes()))
        sources = {"link52": ("movement:SC1004_E_SC1005_to_W", "movement:SC1004_E_SC107_to_W"),
                   "link66": ("movement:SC1004_S_to_W",), "link46": ("movement:SC1004_N_SC1003_to_W",)}
        for row in rows:
            transfers = [t for t in trace["transfers"] if row["start_sec"] <= t["start_sec"] < row["end_sec"]]
            row["model_receipts_to_68_by_origin"] = {
                group: sum(t["vehicles"] for t in transfers if t["source"] in names and t["target"] == "storage:SC1004_W_out")
                for group, names in sources.items()}
            row["model_arrivals_10681"] = sum(t["vehicles"] for t in transfers
                if t["source"] == "storage:SC1004_W_out" and t["target"] == "ramp:RM_C10681")
        aggregate = defaultdict(Counter)
        for row in rows:
            for match in row["matches"]:
                aggregate[str(match["head_link"])][str(match["arrival_lane"])] += 1
            for match in row["unmatched"]:
                aggregate["unmatched"][str(match["lane"])] += 1
        result.setdefault("source_lane_totals", {})[arm] = {key: dict(counts) for key, counts in aggregate.items()}
    return result


if __name__ == "__main__":
    result = assess()
    output = Path(__file__).with_name("arrival10681_native_paths.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "arms": {
        arm: [{k: v for k, v in row.items() if k not in ("matches", "unmatched")}
              for row in rows] for arm, rows in result["arms"].items()}}, ensure_ascii=False))
