"""Review the thin cache without rereading FZP or changing the predictor."""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
OUT = Path("E:/VISSIM_analysis/20261010_gatearrival291")


def main():
    target = HERE / "assessment.json"
    assert not target.exists()
    completion = json.loads((OUT / "completion.json").read_bytes())
    assert completion["status"] == "complete_thin_closed_corridor_cache"
    support = completion["physical_support"]
    pre = {int(k) for k in support["pre_gate_links"]} - {1220018301}
    post = {int(k) for k in support["post_gate_links"]} - {1220018301}
    positions = {int(k): v for k, v in support["gate_link_split_at_lane_head"].items()}
    pins = {str(OUT / "completion.json"): hashlib.sha256((OUT / "completion.json").read_bytes()).hexdigest()}

    def zone(row):
        _, link, lane, pos, *_ = row
        if link == 1220018301:
            return "pre" if pos <= positions[lane] else "post"
        if link in pre:
            return "pre"
        if link in post:
            return "post"
        return None

    results = {}
    for arm, meta in completion["arms"].items():
        path = Path(meta["cache"])
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta["cache_sha256"]
        pins[str(path)] = meta["cache_sha256"]
        frames = json.loads(gzip.decompress(data))["frames"]
        prev = None
        crossed = []
        snapshots = []
        for frame in frames:
            sec = frame["sec"]
            now = {r[0]: r for r in frame["rows"]}
            if sec >= 2400:
                by = {z: [r for r in now.values() if zone(r) == z] for z in ("pre", "post")}
                at_gate = [r for r in now.values() if r[1] == 1220018301 and zone(r) == "pre"]
                snapshots.append(dict(sec=sec,
                    pre_n=len(by["pre"]), pre_stopped=sum(r[4] < 5 for r in by["pre"]),
                    gate_n=len(at_gate), gate_stopped=sum(r[4] < 5 for r in at_gate),
                    post_n=len(by["post"]), post_stopped=sum(r[4] < 5 for r in by["post"])))
            if prev is not None:
                before_sec, before = prev
                assert abs(sec - before_sec - 5) < 1e-7
                for veh in set(before) & set(now):
                    x, y = before[veh], now[veh]
                    if zone(x) == "pre" and zone(y) == "post":
                        # Adjacent5s spatial bracket: lower-bound sampled witness,
                        # not a census nor an inferred subsecond head timestamp.
                        crossed.append(dict(veh=veh, low_sec=before_sec, high_sec=sec,
                                            before_link=x[1], after_link=y[1], after_speed=y[4]))
            prev = sec, now
        blocks = []
        for start in (2400, 2550, 2700):
            rows = [r for r in snapshots if start <= r["sec"] < start + 150]
            assert len(rows) == 30
            c = [r for r in crossed if start <= r["high_sec"] < start + 150]
            blocks.append(dict(start_sec=start, snapshots=len(rows),
                mean_pre_n=sum(r["pre_n"] for r in rows)/len(rows),
                mean_pre_stopped=sum(r["pre_stopped"] for r in rows)/len(rows),
                mean_gate_stopped=sum(r["gate_stopped"] for r in rows)/len(rows),
                max_gate_stopped=max(r["gate_stopped"] for r in rows),
                mean_post_n=sum(r["post_n"] for r in rows)/len(rows),
                mean_post_stopped=sum(r["post_stopped"] for r in rows)/len(rows),
                sampled_pre_to_post_crossings=len(c)))
        results[arm] = dict(blocks=blocks, snapshots=snapshots, sampled_pre_to_post_crossings=crossed)
    pins[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = dict(status="complete_gate_spatial_timing_diagnostic", arms=results, source_pins=pins,
        new_fzp_scans=0, new_forecasts=0, new_native=0, model_changes=0,
        limitations=["Crossings are adjacent5s pre/post spatial witnesses, not complete SC10 head counts.",
            "Late native5s samples are diagnostic; neither the positions nor future native flows were fed to the plant.",
            "Pre/post stock changes alone do not distinguish upstream supply from downstream spillback or prove a gate's causal effect."])
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:v["blocks"] for k,v in results.items()},ensure_ascii=False))


if __name__ == "__main__":
    main()
