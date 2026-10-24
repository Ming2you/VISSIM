"""One thin positional extraction per CLOSED run; no new traffic metrics."""
import ctypes
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
A = HERE.parent
OUT = Path("E:/VISSIM_analysis/20261010_gatearrival291")
NATIVE = Path("E:/VISSIM_analysis/20261010_urbanrm269_cityonly289")
PATHS = {
    "hold": Path("E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/vissim_eval/sdmpc31_g_2400_hold_s29_001.fzp"),
    "city": Path("E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/vissim_eval/sdmpc31_g_2400_selected_s29_001.fzp"),
}


def read(p):
    return json.loads(Path(p).read_bytes())


def extract(path, links):
    before = path.stat()
    digest = hashlib.sha256()
    index = None
    frames = []
    current = None
    rows_total = rows_window = 0
    last = -1
    wanted = ("SIMSEC", "NO", "LANE\\LINK\\NO", "LANE\\INDEX", "POS", "SPEED",
              "ROUTDECNO", "ROUTENO", "NEXTLINK\\NO")
    with path.open("rb") as file:
        for raw in file:
            digest.update(raw)
            line = raw.strip()
            if line.startswith(b"$VEHICLE:"):
                assert index is None
                names = [x.strip().decode("ascii").upper() for x in line.split(b":", 1)[1].split(b";")]
                index = {k: names.index(k) for k in wanted}
                assert index["SIMSEC"] == 0
                continue
            if not line or line.startswith((b"*", b"$")):
                continue
            assert index is not None
            sec = float(line.split(b";", 1)[0])
            assert sec >= last
            last = sec
            rows_total += 1
            if not 2395.1 - 1e-7 <= sec <= 2850:
                continue
            if current is None or current["sec"] != sec:
                if current is not None:
                    assert abs(sec - current["sec"] - 5) < 1e-7
                current = dict(sec=sec, rows=[])
                frames.append(current)
            row = line.split(b";")
            assert len(row) == len(names)
            rows_window += 1
            link = int(row[index["LANE\\LINK\\NO"]])
            if link in links:
                current["rows"].append([
                    int(row[index["NO"]]), link, int(row[index["LANE\\INDEX"]]),
                    float(row[index["POS"]]), float(row[index["SPEED"]]),
                    row[index["ROUTDECNO"]].decode("ascii").strip(),
                    row[index["ROUTENO"]].decode("ascii").strip(),
                    row[index["NEXTLINK\\NO"]].decode("ascii").strip(),
                ])
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    assert frames and abs(frames[0]["sec"] - 2395.1) < 1e-7 and abs(frames[-1]["sec"] - 2845.1) < 1e-7
    for frame in frames:
        ids = [r[0] for r in frame["rows"]]
        assert len(set(ids)) == len(ids)
    return dict(source=str(path), source_sha256=digest.hexdigest(), source_size_bytes=after.st_size,
        source_mtime_ns=after.st_mtime_ns, full_file_rows_visited=rows_total, window_rows_visited=rows_window,
        sample_sec=5, columns=["veh", "link", "lane", "pos_m", "speed_kph", "route_decision", "route", "next_link"],
        physical_links=sorted(links), frames=frames, rows_retained=sum(len(f["rows"]) for f in frames),
        limitations=["Only declared physical links and2395.1..2845.1 snapshots retained.",
                     "Short links can be traversed entirely between5s frames; this is not a complete crossing census."])


def main():
    assert not (OUT / "extract_intent.json").exists(), "No duplicate extraction"
    closed = read(NATIVE / "runtime_closure.json")
    summary = read(NATIVE / "cached_summary.json")
    assert closed["all_owned_processes_closed"] and closed["normal_sim_done_sec"] == 2850
    assert summary["paired_prefix_exact"] and summary["common_start_vehicle_records_exact"]
    support = read(A / "fixed_gate286/assessment.json")["physical_support"]
    links = {int(x) for k in ("pre_gate_links", "post_gate_links") for x in support[k]}
    links |= {1210012700, 1220012103, 1220013600, 1220015000}
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "extract_intent.json").write_text(json.dumps(dict(
        sources={k: str(v) for k, v in PATHS.items()}, max_source_passes=2,
        status="started_no_automatic_retry", new_native_runs=0, new_predictions=0)), encoding="utf8")
    records = {}
    for arm, source in PATHS.items():
        result = extract(source, links)
        target = OUT / (arm + ".json.gz")
        assert not target.exists()
        target.write_bytes(gzip.compress(json.dumps(result, allow_nan=False).encode("utf8")))
        records[arm] = {k: result[k] for k in ("source", "source_sha256", "source_size_bytes", "full_file_rows_visited", "rows_retained")}
        records[arm].update(cache=str(target), cache_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), frames=len(result["frames"]))
        print(arm, records[arm], flush=True)
    report = dict(status="complete_thin_closed_corridor_cache", arms=records, source_passes=2,
        new_traffic_performance_measurements=0, new_native_runs=0, new_predictions=0,
        physical_support=support, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT / "completion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
