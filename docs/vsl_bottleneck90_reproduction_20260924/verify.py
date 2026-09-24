"""Check packaged commands, distributions and reported costs; no VISSIM run."""
import csv
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main():
    spec = load("experiment_spec.json")
    records = load("results.json")["results"]
    with (ROOT / "vsl_events.csv").open(encoding="utf-8", newline="") as stream:
        events = list(csv.DictReader(stream))
    assert [(int(r["time_s"]), r["kind"], int(r["no"]), int(r["veh_class"]), int(r["value"]))
            for r in events] == [(900, "vsl", n, c, 90) for n in (63, 64, 65, 66) for c in (10, 20, 30, 70)]
    for node in ET.parse(ROOT / "desired_speed_cdf.xml").getroot():
        points = [(float(p.get("fx")), float(p.get("x"))) for p in node.findall("./speedDistrDatPts/speedDistributionDataPoint")]
        mean = sum((b[0]-a[0])*(a[1]+b[1])/2 for a, b in zip(points, points[1:]))
        second = sum((b[0]-a[0])*(a[1]**2+a[1]*b[1]+b[1]**2)/3 for a, b in zip(points, points[1:]))
        row = next(r for r in spec["distributions"] if r["distribution_id"] == int(node.get("no")))
        assert points == [tuple(p) for p in row["cdf_points"]]
        assert math.isclose(mean, row["mean_kph"], abs_tol=1e-10)
        assert math.isclose(math.sqrt(second-mean**2), row["std_kph"], abs_tol=1e-10)
    for r in records:
        with (ROOT / "evidence" / f'seed{r["seed"]}_{r["arm"]}_native_netperf.csv').open(encoding="utf-8-sig") as stream:
            native = {x["attribute"]: float(x["value"]) for x in csv.DictReader(stream)}
        assert math.isclose(r["network_ttt_veh_h"], native["TravTmTot"]/3600, abs_tol=1e-8)
        assert math.isclose(r["external_wait_veh_h"], native["DelayLatent"]/3600, abs_tol=1e-8)
        assert math.isclose(r["network_tts_veh_h"], (native["TravTmTot"]+native["DelayLatent"])/3600, abs_tol=1e-8)
        base = next(x for x in records if x["seed"] == r["seed"] and x["arm"] == "none")
        for field, pct in (("east_local_ttt_veh_h", "east_local_change_pct"),
                           ("omega_ttt_veh_h", "omega_change_pct"), ("network_tts_veh_h", "network_tts_change_pct")):
            assert math.isclose(100*(r[field]/base[field]-1), r[pct], abs_tol=1e-9)
    assert next(r for r in records if r["seed"] == 29 and r["arm"] == "bottleneck90")["network_tts_change_pct"] < 0
    assert next(r for r in records if r["seed"] == 43 and r["arm"] == "bottleneck90")["network_tts_change_pct"] > 0
    print("PASS:16 events, exact CDFs,4 native cost records, reported deltas, and cross-seed reversal. No simulation was run.")


if __name__ == "__main__":
    main()
