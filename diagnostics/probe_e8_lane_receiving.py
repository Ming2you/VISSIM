"""Cached lane/connector evidence plus bounded indexed trajectory snapshots."""
from __future__ import annotations
from bisect import bisect_right
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RUNS = {"NC": "codex_nc_s13_6056c94_20260909_retry", "n7": "codex_n7_pure_s13_20260910",
        "zero": "codex_signal_zero_s13_20260910", "offset10": "codex_signal_offset10_s13_20260910"}
WINDOWS = ((1050, 1500), (3150, 3450))
SNAPSHOTS = (1081, 1201, 1351, 1471, 3181, 3301, 3421)
CONNECTORS = {"10639", "10643", "10681", "10682"}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class IndexedFzp:
    """Binary search monotone SIMSEC blocks, never scan the whole FZP."""
    def __init__(self, path, max_bytes=32 * 1024 * 1024):
        self.path = path
        self.handle = path.open("rb")
        self.bytes_read = 0
        self.max_bytes = max_bytes
        self.selected = {}
        while True:
            row = self.line()
            if not row:
                raise ValueError("FZP schema absent")
            if row.startswith(b"$VEHICLE:"):
                self.names = row.decode().strip().split(":", 1)[1].split(";")
                break
        self.start = self.handle.tell()
        self.size = path.stat().st_size
        self.index = {key: self.names.index(key) for key in ("SIMSEC", "NO", "LANE\\LINK\\NO", "LANE\\INDEX", "POS", "SPEED")}
        assert self.index["SIMSEC"] == 0

    def line(self):
        row = self.handle.readline()
        self.bytes_read += len(row)
        if self.bytes_read > self.max_bytes:
            raise RuntimeError("Bounded read budget exhausted; do not full-scan")
        return row

    def seek_time(self, target):
        low, high = self.start, self.size
        while high - low > 32768:
            midpoint = (low + high) // 2
            self.handle.seek(midpoint)
            self.line()  # discard a partial row
            row = self.line()
            if not row:
                high = midpoint
                continue
            time = float(row.split(b";", 1)[0])
            if time < target:
                low = self.handle.tell()
            else:
                high = midpoint
        self.handle.seek(low)

    def snapshot(self, target):
        self.seek_time(target)
        values, digest, first_offset, last_time = {}, hashlib.sha256(), None, None
        while row := self.line():
            fields = row.rstrip(b"\r\n").split(b";")
            time = float(fields[0])
            if last_time is not None:
                assert time >= last_time
            last_time = time
            if time < target:
                continue
            if time > target:
                break
            if first_offset is None:
                first_offset = self.handle.tell() - len(row)
            digest.update(row)
            index = self.index
            veh = int(fields[index["NO"]])
            assert veh not in values
            values[veh] = (int(fields[index["LANE\\LINK\\NO"]]), int(fields[index["LANE\\INDEX"]]),
                           float(fields[index["POS"]]), float(fields[index["SPEED"]]))
        assert values, (self.path, target)
        self.selected[str(target)] = {"whole_network_vehicles": len(values), "first_byte_offset": first_offset,
                                      "selected_raw_rows_sha256": digest.hexdigest()}
        return values


def main():
    mapping_path = ROOT / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    chain = mapping["freeway_model_links"]["FW_E"]
    offsets = dict(zip(map(int, chain["chain_links"]), chain["chain_offsets_m"]))
    bounds = chain["segment_bounds_m"]
    boundary = bounds[9]
    network_path = ROOT / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
    network = ET.parse(network_path).getroot()
    physical_connectors = {}
    for key in sorted(CONNECTORS):
        link = network.find(f'./links/link[@no="{key}"]')
        ends = {tag: dict(link.find(tag).attrib) for tag in ("fromLinkEndPt", "toLinkEndPt")}
        for row in ends.values():
            source = int(row["lane"].split()[0])
            if source in offsets:
                row["freeway_chain_m"] = float(row["pos"]) + offsets[source]
                row["model_cell"] = bisect_right(bounds, row["freeway_chain_m"]) - 1
        physical_connectors[key] = {"endpoints": ends, "emergStopDist_m": link.get("emergStopDist"), "lnChgDist_m": link.get("lnChgDist")}
    routing = network.find('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no="1130"]')
    routes = {route.get("no"): {"attributes": dict(route.attrib), "via_links": [x.get("key") for x in route.findall('./linkSeq/intObjectRef')]}
              for route in routing.findall('./vehRoutSta/vehicleRouteStatic')}
    report = {"windows_sec": WINDOWS, "snapshot_times_sec": SNAPSHOTS, "cell_bounds_m": bounds[8:11],
              "physical_connectors": physical_connectors, "routing_decision_1130": routes,
              "small_source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                                      (mapping_path, network_path, Path(__file__), ROOT / "scripts/analyze_control_run.py", ROOT / "scripts/analyze_ramp_corridor.py")},
              "method": "Read cached100m/30s lane sums and150s connector ID transitions; binary-seek only selected FZP snapshot pairs, no full scan or fit",
              "definitions": {"cached_lane_density": "samples/(30/cadence_seconds)/0.1km for a full100m lane bin; time-average density, not instantaneous",
                              "cached_lane_stopped": "SPEED<5km/h", "snapshot_stopped": "both<1km/h and<5km/h counted separately",
                              "crossing": "same vehicle observed on FW_E chain at both endpoints5s apart, old chain position<4621.726...<=new position; observed lower bound, not total flow/capacity",
                              "cadence": "NC/n7 original5s times1+5k; zero/offset1s. Selected pairs use identical time endpoints for all runs."}, "runs": {}}
    for label, run in RUNS.items():
        directory = ROOT / "evaluation/runs" / run
        analysis = directory / "analysis"
        passage_meta = json.loads((analysis / "physical_connector_passages_metadata.json").read_text())
        cadence = float(passage_meta["observation_step_sec"])
        lane_rows = []
        for row in read_rows(analysis / "freeway_lane_space_time.csv"):
            time, space = int(row["time_bin_sec"]), int(row["space_bin_m"])
            if row["model_link"] == "FW_E" and 4100 <= space <= 5100 and any(a <= time < b for a, b in WINDOWS):
                lane_rows.append({"time_bin_sec": time, "space_bin_m": space, "lane": int(row["LANE\\INDEX"]),
                                  "samples": int(row["samples"]), "density_time_mean_veh_km_lane": float(row["samples"]) / (30 / cadence) / .1,
                                  "mean_speed_kph": float(row["mean_speed_kph"]), "stopped_fraction_lt5": float(row["stopped_fraction"])})
        passages = [row for row in read_rows(analysis / "physical_connector_passages.csv") if row["connector"] in CONNECTORS and any(a <= int(row["start_sec"]) and int(row["end_sec"]) <= b for a, b in WINDOWS)]
        segments = [row for row in read_rows(directory / f"bottleneck_segments_{run}.csv") if row["model_link"] == "FW_E" and row["segment_index"] in ("8", "9") and any(a <= int(row["sim_sec"]) <= b for a, b in WINDOWS)]
        files = list((directory / "vissim_eval").glob("*.fzp"))
        assert len(files) == 1
        reader = IndexedFzp(files[0])
        lane_snapshots, crossings = [], []
        for time in SNAPSHOTS:
            before, now = reader.snapshot(time - 5), reader.snapshot(time)
            group = defaultdict(list)
            for veh, (link, lane, pos, speed) in now.items():
                if link not in offsets:
                    continue
                chain_pos = pos + offsets[link]
                cell = bisect_right(bounds, chain_pos) - 1
                if cell in (8, 9):
                    group[cell, lane].append((veh, speed, chain_pos))
            for cell in (8, 9):
                for lane in range(1, 5):
                    vehicles = group[cell, lane]
                    length_km = (bounds[cell + 1] - bounds[cell]) / 1000
                    lane_snapshots.append({"sim_sec": time, "cell": cell, "lane": lane, "count": len(vehicles),
                                           "density_veh_km_lane": len(vehicles) / length_km,
                                           "mean_speed_kph": sum(v for _, v, _ in vehicles) / len(vehicles) if vehicles else None,
                                           "stopped_lt1": sum(v < 1 for _, v, _ in vehicles), "stopped_lt5": sum(v < 5 for _, v, _ in vehicles),
                                           "upstreammost_stopped_lt5_chain_m": min((p for _, v, p in vehicles if v < 5), default=None),
                                           "downstreammost_stopped_lt5_chain_m": max((p for _, v, p in vehicles if v < 5), default=None)})
            crossed = []
            for veh in before.keys() & now.keys():
                old, new = before[veh], now[veh]
                if old[0] in offsets and new[0] in offsets and old[2] + offsets[old[0]] < boundary <= new[2] + offsets[new[0]]:
                    crossed.append({"vehicle_id": veh, "lane_before": old[1], "lane_after": new[1], "old_chain_m": old[2] + offsets[old[0]], "new_chain_m": new[2] + offsets[new[0]]})
            crossings.append({"start_sec": time - 5, "end_sec": time, "observed_crossings_lower_bound": len(crossed), "crossings": crossed})
        reader.handle.close()
        cached_paths = [analysis / filename for filename in ("freeway_lane_space_time.csv", "physical_connector_passages.csv", "physical_connector_passages_metadata.json")] + [directory / f"bottleneck_segments_{run}.csv"]
        warning_path = analysis / "simulation_warning_events.csv"
        warnings = None
        if warning_path.is_file():
            warnings = [row for row in read_rows(warning_path) if row["link"] == "2" and row["kind"] == "lane_change_removal"]
            for row in warnings:
                row["freeway_chain_m"] = float(row["position_m"]) + offsets[2]
                row["in_requested_window"] = any(a <= float(row["sim_sec"]) < b for a, b in WINDOWS)
            cached_paths.append(warning_path)
        report["runs"][label] = {"run": run, "cadence_sec": cadence, "lane_bins": lane_rows, "connector_passages": passages, "whole_cells_com": segments,
                                  "link2_lane_change_removals": warnings, "warning_cache_available": warning_path.is_file(),
                                  "lane_snapshots": lane_snapshots, "observed_cell_crossings": crossings,
                                  "fzp_snapshot_provenance": {"path": str(files[0].relative_to(ROOT)), "file_size": reader.size, "mtime_ns": files[0].stat().st_mtime_ns, "bytes_read": reader.bytes_read, "selected_blocks": reader.selected},
                                  "cached_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in cached_paths}}
        print(label, "bounded_bytes", reader.bytes_read, "lane_rows", len(lane_rows), "snapshots", len(lane_snapshots), flush=True)
    (ROOT / "diagnostics/e8_lane_receiving_evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
