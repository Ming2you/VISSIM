"""Bounded postprocess of six completed forecasts; never invokes simulation or fitting."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926"
R = HERE.parent
PINS = {}


def blob(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return raw


def read(path):
    raw = blob(path)
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def rows(path):
    return list(csv.DictReader(blob(path).decode("utf-8-sig").splitlines()))


def close(a, b, tolerance=1e-7):
    assert abs(a-b) < tolerance, (a, b)


def native43(folder, off):
    selected = [r for r in rows(folder/"ports_30s.csv") if r["connector"] == off
                and float(r["window_start_s"]) >= 2250.1-1e-7
                and float(r["window_end_s"]) <= 2700.1+1e-7]
    selected.sort(key=lambda r: float(r["window_start_s"]))
    assert len(selected) == 15
    windows = []
    for block in range(3):
        group = selected[5*block:5*block+5]
        sums = {k: sum(float(r[k]) for r in group) for k in
                ("arrivals_veh", "departures_veh", "unresolved_absences_veh", "conservation_residual_veh")}
        initial, final = float(group[0]["start_n_veh"]), float(group[-1]["end_n_veh"])
        close(sums["conservation_residual_veh"], 0)
        close(initial+sums["arrivals_veh"]-sums["departures_veh"]-sums["unresolved_absences_veh"], final)
        windows.append(dict(start_sec=2250+150*block, end_sec=2400+150*block,
                            native_phase_sec=0.1, initial_stock=initial, final_stock=final,
                            entry=sums["arrivals_veh"], balance_inferred_drain=sums["departures_veh"],
                            unresolved_absences=sums["unresolved_absences_veh"]))
    return windows


def main():
    target = HERE/"assessment.json"
    if target.exists():
        raise FileExistsError(target)
    protocol = read(HERE/"protocol.json")
    for path, sha in protocol["source_pins"].items():
        assert hashlib.sha256(blob(ROOT/path)).hexdigest() == sha
    candidate = read(HERE/"candidate_config.json")
    base = read(R/"sc105_supply/candidate_config.json")
    route_path = candidate["freeway"].pop("offramp_route_inventory")
    assert candidate == base
    assert hashlib.sha256(blob(HERE/"candidate_config.json")).hexdigest() == protocol["candidate_sha256"]
    route_sha = hashlib.sha256(blob(ROOT/route_path)).hexdigest()
    native47 = read(R/"offramp_drain_profile/eight_offramps.json")
    native_cost43 = read(R/"sc1001_route_inventory_s43/comparison.json")
    outputs = {
        "47": I/"closedloop_recorded2700_select_check_trace10681_routed_ports47",
        "43": I/"closedloop_recorded2250_lever450_trace10681_routed_ports43",
    }
    static47 = read(I/"closedloop_recorded2700_select_check_trace10681_declared_drain47/summary.json")
    assessment = {}
    wall = 0.
    max_mass = max_route = max_resource = 0.
    for seed, folder in outputs.items():
        summary = read(folder/"summary.json")
        runtime = read(folder/"runtime.json")["offramp_route_inventory"]
        assert runtime["enabled"]
        assert runtime["metadata"]["offramp_route_inventory_source_sha256"] == route_sha
        assert summary["future_observation_inputs"] is False
        assert not summary["native_started"]
        arms = (("hold", "held_actual"), ("selected", "selected")) if seed == "47" else (
            ("nc", "held_actual"), ("rm", "rm"), ("vsl", "vsl"), ("both", "both"))
        seed_report = {}
        initial_ports = initial_cells = None
        for arm, key in arms:
            result = summary["results"][key]
            trace = read(folder/(key+"_RM_C10681_trace.json.gz"))
            assert trace["future_observation_inputs"] is False
            diag = trace["offramp_network_diagnostics"]
            assert len(diag["states"]) == 4 and len(diag["descriptions"]) == 8
            # Per-road route configuration is independently evidenced in runtime.json and result checks.
            assert diag["route_runtime"] is None and diag["route_states"] == []
            checks = result["offramp_route_inventory_checks"]
            assert len(checks) == 6
            max_route = max(max_route, max(x["max_cell_residual"] for x in checks))
            validation = result["validation"]
            if validation.get("schema") == "joint-written-command-binding/v1":
                assert validation["prewrite_binding_passed"] and validation["written_command_binding_passed"]
                assert result["canonical_quantity_constraints"]["feasible"]
            else:
                assert validation["all_actuator_and_step_constraints_checked"]
            wall += result["wall_sec"]
            if seed == "47":
                assert result["commands"] == static47["results"][key]["commands"]
            elif initial_cells is None:
                initial_cells = result["physical_cell_states"][0]
            else:
                assert result["physical_cell_states"][0] == initial_cells
            ports0 = diag["states"][0]["ports"]
            if initial_ports is None:
                initial_ports = ports0
            else:
                assert initial_ports == ports0
            cache = ROOT.parent/"control-full-review/diagnostics"/(
                "dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none"
                if arm == "nc" else f"metanet_net_gain_goal_20260924/heldout43/observations/{arm}")
            port_report = {}
            for off, description in diag["descriptions"].items():
                native = native47["arms"][arm][off]["windows"] if seed == "47" else native43(cache, off)
                window_report = []
                sends = [r for r in diag["resources"] if r["kind"] == "freeway_offramp_sending" and r["resource"] == off]
                receives = [r for r in diag["resources"] if r["kind"] == "freeway_offramp_receiving" and r["resource"] == off]
                assert len(sends) == len(receives) == 450
                for idx, n in enumerate(native):
                    a, b = [diag["states"][j]["ports"][off] for j in (idx, idx+1)]
                    max_mass = max(max_mass, abs(b["stock"]-b["initial"]-b["admitted"]+b["departed"]))
                    entry, drain = b["admitted"]-a["admitted"], b["departed"]-a["departed"]
                    ss = sends[idx*150:(idx+1)*150]
                    rr = receives[idx*150:(idx+1)*150]
                    close(sum(x["accepted_total_veh"] for x in ss), entry)
                    close(sum(x["accepted_total_veh"] for x in rr), entry)
                    window_report.append(dict(native=n, model=dict(initial_stock=a["stock"],
                        final_stock=b["stock"], entry=entry, drain=drain,
                        requested=sum(x["available_veh"] for x in ss),
                        receiving_limited_seconds=sum(x["available_veh"]-x["accepted_total_veh"]>1e-8 for x in ss))))
                actual_entry = sum(x["entry"] for x in native)
                actual_drain = sum(x["balance_inferred_drain"] for x in native)
                model_final = diag["states"][-1]["ports"][off]
                port_report[off] = dict(road=description["road"], cell=description["from_cell"],
                    native_entry=actual_entry, model_entry=model_final["admitted"],
                    native_drain=actual_drain, model_drain=model_final["departed"],
                    native_final_stock=native[-1]["final_stock"], model_final_stock=model_final["stock"],
                    entry_error=model_final["admitted"]-actual_entry,
                    drain_error=model_final["departed"]-actual_drain,
                    receiving_limited_seconds=sum(x["model"]["receiving_limited_seconds"] for x in window_report),
                    windows=window_report)
                if seed == "47":
                    port_report[off]["previous_static_entry"] = native47["arms"][arm][off]["model_entry"]
                for resource in sends+receives:
                    max_resource = max(max_resource, resource["exceedance_veh"])
            seed_report[arm] = dict(ports=port_report, omega_veh_h=result["ttt_omega_veh_h"],
                entry_mae=sum(abs(p["entry_error"]) for p in port_report.values())/8,
                drain_mae=sum(abs(p["drain_error"]) for p in port_report.values())/8,
                final_stock_mae=sum(abs(p["model_final_stock"]-p["native_final_stock"]) for p in port_report.values())/8,
                road_totals={road:{k:sum(p[k] for p in port_report.values() if p["road"]==road)
                                for k in ("native_entry","model_entry","native_drain","model_drain")}
                             for road in ("FW_E","FW_W")})
            if seed == "43":
                seed_report[arm]["native_omega_veh_h"] = native_cost43["costs"][arm]["native_omega_veh_h"]
                flows = rows(cache/"flows_30s.csv")
                byroad = {}
                for road in ("FW_E","FW_W"):
                    native_cells = [r for r in flows if r["road"]==road
                                    and float(r["window_start_s"])>=2250.1-1e-7
                                    and float(r["window_end_s"])<=2700.1+1e-7]
                    assert len(native_cells)==465
                    counts = result["control_area"]["flow_counts"]
                    byroad[road] = dict(native_source=sum(float(r["source_admissions"]) for r in native_cells),
                        model_source=counts[f"origin:{road}->freeway:{road}"],
                        native_terminal=sum(float(r["terminal_exits_inferred"]) for r in native_cells),
                        model_terminal=counts[f"freeway:{road}->external:terminal:{road}"])
                seed_report[arm]["source_terminal_counts"]=byroad
        ref = "hold" if seed == "47" else "nc"
        for arm, report in seed_report.items():
            report["delta_omega_veh_h"] = report["omega_veh_h"]-seed_report[ref]["omega_veh_h"]
            if seed == "43":
                report["native_delta_omega_veh_h"] = report["native_omega_veh_h"]-seed_report[ref]["native_omega_veh_h"]
        assessment[seed] = seed_report
    assert max_mass<1e-7 and max_route<1e-7 and max_resource<1e-7
    report = dict(status="OFFRAMP_RECONCILIATION_INCOMPLETE", goal_complete=False, cases=assessment,
        completed_forecasts=6, forecast_compute_wall_sec=wall, new_native=0,new_fzp_scan=0,fit=0,optimizer_iterations=0,
        max_mass_residual_veh=max_mass,max_route_residual_veh=max_route,max_resource_exceedance_veh=max_resource,
        ranking43=dict(native=sorted(assessment["43"],key=lambda a:assessment["43"][a]["native_omega_veh_h"]),
                       model=sorted(assessment["43"],key=lambda a:assessment["43"][a]["omega_veh_h"])),
        scope=["47 city-selected comparison has unchanged RM/VSL, not a RM/VSL causal experiment.",
               "43 native cached windows have +0.1 second phase; known existing seed, not a new blind holdout.",
               "47 drain is stock-balance inferred;43 cached exits retain unresolved absences separately.",
               "Trace route_runtime field is missing due diagnostic full-config guard. Runtime enabled and 6 per-road partition checks certify actual routed prediction.",
               "Future native measurements are evaluation targets only; no input to autonomous forecasts.",
               "No capacity coefficients were fitted; candidate not enabled as default."],
        source_pins=dict(PINS))
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("cases","source_pins")},ensure_ascii=False))
    for seed, arms in assessment.items():
        for arm,r in arms.items():
            print(seed,arm,"MAE",r["entry_mae"],r["drain_mae"],"receiving limited",
                  sum(x["receiving_limited_seconds"] for x in r["ports"].values()))
    print("47 held entry/drain/stock native->model")
    for off,p in assessment["47"]["hold"]["ports"].items():
        print(off,*[(p["native_"+k],round(p["model_"+k],3)) for k in ("entry","drain","final_stock")])
    print("43 nc ports")
    for off,p in assessment["43"]["nc"]["ports"].items():
        print(off,*[(p["native_"+k],round(p["model_"+k],3)) for k in ("entry","drain","final_stock")])


if __name__ == "__main__":
    main()

