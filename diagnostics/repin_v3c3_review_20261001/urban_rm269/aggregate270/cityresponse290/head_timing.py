"""Use closed native detector events to separate timing from future arrivals."""
from collections import defaultdict
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit as a


def main():
    out = HERE / "head_timing.json"
    assert not out.exists()
    prior = a.read(HERE / "assessment.json")
    initial = a.read(a.RUNS["hold"] / "state_002400.json")["vehicle_records"]
    assert initial["complete"]
    ids = {int(r["veh_no"]) for r in initial["records"]}
    initial_location = {int(r["veh_no"]): r for r in initial["records"]}
    a.head_reader.LINKS = dict(SC6_S=1210018302, SC101_S=1220011503)
    counts, traces = {}, {}
    for arm in ("hold", "city"):
        totals = defaultdict(lambda: dict(count=0, head_time_cost=0., initial_vehicle_count=0,
                                         initial_vehicle_time_cost=0., new_vehicle_count=0, new_vehicle_time_cost=0.,
                                         observed_counter_count=0, unresolved_id_count=0,
                                         unresolved_time_cost_low=0., unresolved_time_cost_high=0.))
        trace = defaultdict(list)
        for end in (2550, 2700, 2850):
            heads, events = a.head_reader.heads_and_entries(a.RUNS[arm], end)
            for group in ("SC6_S", "SC101_S"):
                full_count = sum(x["crossings"] for x in heads[group]["rows"] if int(x["lane"]) <= 3)
                known_count = sum(lane <= 3 for lane, veh, sec in events[group])
                missing = full_count - known_count
                assert missing >= 0
                totals[group]["observed_counter_count"] += full_count
                totals[group]["unresolved_id_count"] += missing
                totals[group]["unresolved_time_cost_low"] -= missing * (2850 - (end - 150)) / 3600
                totals[group]["unresolved_time_cost_high"] -= missing * (2850 - end) / 3600
                # Both approaches' SG8 heads on lanes1..3 are p1. SC6's right
                # turn shares that group: its head time is not a pure Omega exit.
                for lane, veh, sec in events[group]:
                    if lane > 3:
                        continue
                    key = group
                    cost = -(2850 - sec) / 3600
                    z = totals[key]
                    z["count"] += 1
                    z["head_time_cost"] += cost
                    known = int(veh) in ids
                    prefix = "initial_vehicle" if known else "new_vehicle"
                    z[prefix + "_count"] += 1
                    z[prefix + "_time_cost"] += cost
                    trace[key].append(dict(veh=int(veh), sec=sec, initial=known,
                                          initial_link=initial_location[int(veh)]["link_no"] if known else None))
        counts[arm], traces[arm] = dict(totals), dict(trace)
    response_paths = dict(
        hold=a.A / "matched280/authority/hold.response.json.gz",
        city=a.A / "citysplit287/forecast2400/city_only.response.json.gz")
    model = {}
    for arm, path in response_paths.items():
        r = json.loads(gzip.decompress(a.pin(path)))
        movements = {
            "SC101_S": {"movement:SC101_S_SC1_to_N_SC2005"},
            "SC6_S": {"movement:SC6_S_SC12_to_N_SC103", "movement:SC6_S_SC12_to_E_SC104"},
        }
        model[arm] = {key: dict(
            count=sum(t["vehicles"] for t in r["transfers"] if t["source"] in sources),
            head_time_cost=-sum(t["vehicles"] * sum(x["dt_h"] for x in r["residence"] if x["end_sec"] >= t["end_sec"] - 1e-7)
                               for t in r["transfers"] if t["source"] in sources))
            for key, sources in movements.items()}
    delta, matched = {}, {}
    for group in ("SC6_S", "SC101_S"):
        delta[group] = dict(native={k: counts["city"][group][k] - counts["hold"][group][k] for k in counts["hold"][group]},
                            model={k: model["city"][group][k] - model["hold"][group][k] for k in model["hold"][group]})
        delta[group]["native_head_time_cost_bounds"] = [
            delta[group]["native"]["head_time_cost"] + counts["city"][group]["unresolved_time_cost_low"] - counts["hold"][group]["unresolved_time_cost_high"],
            delta[group]["native"]["head_time_cost"] + counts["city"][group]["unresolved_time_cost_high"] - counts["hold"][group]["unresolved_time_cost_low"],
        ]
        # Same initial vehicle, same physical head group in both arms. Vehicles
        # never seen at both heads are censored; do not assign them a made-up delay.
        pairs = {arm: {x["veh"]: x for x in traces[arm][group] if x["initial"]} for arm in ("hold", "city")}
        for arm in pairs:
            assert len(pairs[arm]) == sum(x["initial"] for x in traces[arm][group]), "Repeated head event"
        common = set(pairs["hold"]) & set(pairs["city"])
        dt = {veh: pairs["city"][veh]["sec"] - pairs["hold"][veh]["sec"] for veh in common}
        by_initial_link = defaultdict(lambda: dict(count=0, sum_city_minus_hold_sec=0.))
        for veh, secs in dt.items():
            key = str(pairs["hold"][veh]["initial_link"])
            by_initial_link[key]["count"] += 1
            by_initial_link[key]["sum_city_minus_hold_sec"] += secs
        matched[group] = dict(common_initial_vehicles=len(common), only_hold=len(set(pairs["hold"]) - common),
            only_city=len(set(pairs["city"]) - common), paired_head_time_delta_veh_h=sum(dt.values()) / 3600,
            by_initial_link=dict(by_initial_link))
    result = dict(status="complete_same_initial_vehicle_head_timing", counts=counts, model=model, delta=delta,
        matched_initial_vehicles=matched, source_pins=a.PINS, new_forecasts=0, new_native=0, new_fzp_scans=0,
        limitations=["Head timing weights are a timing diagnostic, not actual Omega TTT or automatically Omega boundary exits.",
                     "Counter crossings lacking vehicle/time detail are bounded within their150s window, not imputed as identified events.",
                     "SC6 p1 includes straight and right turns; head observations do not separate those destinations.",
                     "Native exact crossing timestamps versus model10s endpoint accounting; no future observations used as input.",
                     "Censored unmatched vehicles and new arrivals are reported separately; common-vehicle subsets are not total traffic."])
    a.pin(Path(__file__))
    a.PINS.update(a.head_reader.PINS)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")
    print(json.dumps(dict(delta=delta, matched=matched), ensure_ascii=False))


if __name__ == "__main__":
    main()
