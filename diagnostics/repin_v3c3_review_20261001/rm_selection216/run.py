"""Bounded saved-state RM activation diagnosis; no optimizer or native run."""
import copy
import ctypes
import ctypes.wintypes
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
DEC = Path("D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29")
EAST = ("RM_C10639", "RM_C10681", "RM_C10490", "RM_C10484")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, data):
    (HERE/name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")

def run(captured, reference, coord, options, evaluate, selected_path, output, **unused):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence, sdmpc_pfo
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint

    cfg, state = captured["cfg"], captured["state"]
    assert state.time_sec == 4500 and len(captured["forecast"]) == 3
    saved = json.loads(selected_path.with_suffix(".joint.json").read_bytes())["selection"]
    binding = json.loads(selected_path.with_suffix(".joint_written.json").read_bytes())
    assert binding["written_command_binding_passed"]
    assert binding["action_json"]["sha256"] == sha(selected_path)
    selected = adapter.control_from_json(selected_path, cfg, ControlAction)
    if sequence.KEY not in selected.diagnostics:
        selected = sequence.pack(sequence.actions(selected, 3))
    coord.validate(selected)
    original = sequence.actions(selected, 3)
    assert all(c.diagnostics["rw_meter_green_"+r] == 10 for c in original for r in cfg.network.ramps)
    z = coord.encode(selected)
    changed = []
    for j, axis in enumerate(coord.axes):
        if axis["kind"] == "meter" and axis["key"] in EAST:
            value = 8-2*axis["block"]
            assert value in axis["allowed"] and reference.diagnostics["rw_meter_green_"+axis["key"]] == 10
            z[j] = (value-10)/axis["scale"]
            changed.append((axis["block"], axis["key"]))
    assert set(changed) == {(b,r) for b in range(3) for r in EAST}
    trial = coord.decode(z, selected)
    coord.validate(trial)
    for b,(before,after) in enumerate(zip(original,sequence.actions(trial,3))):
        assert before.green_times == after.green_times and before.offsets == after.offsets
        assert before.vsl == after.vsl
        assert before.N_P_star == after.N_P_star and before.N_UF_star == after.N_UF_star
        for r in cfg.network.ramps:
            assert after.diagnostics["rw_meter_green_"+r] == (8-2*b if r in EAST else 10)
            if r not in EAST:
                assert before.ramp_metering[r] == after.ramp_metering[r]
    save("native_selection_evidence.json", dict(
        selected_objective=saved["selected_objective"],held_objective=saved["held_objective"],
        constraints=saved["final_constraints"],budget=saved["budget_initialization"],
        meter_gradients=[x for x in saved["gradient_rows"] if x["kind"]=="meter"],
        freeway_local_steps=[x for x in saved["local_rows"] if x["owner"] in ("FW_E","FW_W")],
        finite_neighbor_audit=saved["finite_neighbor_audit_performed"],
        prediction_model=saved["prediction_model"],
        execution_model_evaluated=saved["execution_model_evaluated"],
        pfo_summary={k:saved["pfo_warm_start"][k] for k in
                     ("max_iterations","executed_iterations","accepted_iterations","converged")},
        policy=saved["policy"],output=str(output)))
    follower = adapter._PHASE_VECTOR_FOLLOWER["ref"]
    def budget(action, quantities):
        return constraints.shared_quantity_constraints(follower, action, quantities,
            start_sec=state.time_sec,horizon_steps=3,
            np_mode="cap",target_np_veh=saved["final_constraints"]["np"]["target"],
            np_tolerance_veh=saved["final_constraints"]["np"]["tolerance"],
            nuf_mode="cap",target_nuf_veh_h=saved["final_constraints"]["nuf"]["target"],
            nuf_tolerance_veh_h=saved["final_constraints"]["nuf"]["tolerance"])
    results = {}
    for name,action in (("selected",selected),("east_progressive",trial)):
        begun = time.perf_counter()
        item = evaluate([action], derivatives=False)[0]
        surrogate = dict(ttt=item["objective_veh_h"],budget=budget(action,item["quantities"]),
            physical_feasible=sdmpc_pfo.model_feasible(item, options["shared_tolerance"]),
            costs=item["sdmpc_omega_partition"]["costs"],seconds=time.perf_counter()-begun)
        if name == "selected":
            assert abs(surrogate["ttt"]-saved["selected_objective"]) < 1e-7, (surrogate["ttt"],saved["selected_objective"])
        save(name+"_surrogate.json",surrogate)
        begun = time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point = endpoint.evaluate_price_point(state, action, copy.deepcopy(captured["forecast"]), (),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode="raw"),capture_response=True)
        seconds = time.perf_counter()-begun
        assert visits == [0,1,2] and not point.aborted and len(point.states) == 3
        response = point.control_area_response
        costs, outside, flows = {}, {}, {}
        for row in response["residence"]:
            for k,n in row["inside_veh"].items():
                costs[k] = costs.get(k,0.)+row["dt_h"]*n
                extra = row["model_stock_veh"][k]-n
                assert extra >= -1e-7
                outside[k] = outside.get(k,0.)+row["dt_h"]*max(0.,extra)
        assert abs(sum(costs.values())-point.ttt) < 1e-7
        stocks = []
        for snapshot in (state,*point.states):
            inv = model_inventory(snapshot,cfg)
            get_ledger(snapshot).assert_stocks(inv)
            stocks.append(dict(time_sec=snapshot.time_sec,stock=inv))
        for event in response["transfers"]:
            key=(event["source"],event["target"])
            flows[key]=flows.get(key,0.)+event["vehicles"]
        transfers=[dict(source=k[0],target=k[1],vehicles=n) for k,n in flows.items()]
        first,last=stocks[0]["stock"],stocks[-1]["stock"]
        residuals={k:last.get(k,0.)-first.get(k,0.)
                   -math.fsum(t["vehicles"] for t in transfers if t["target"]==k)
                   +math.fsum(t["vehicles"] for t in transfers if t["source"]==k)
                   for k in first.keys()|last.keys()}
        mass=max(map(abs,residuals.values()))
        resources=max((x["exceedance_veh"] for x in response["resource_allocations"]),default=0.)
        assert mass < 1e-7 and resources < 1e-7
        q=constraints.shared_urban_quantities(follower,response,start_sec=state.time_sec,horizon_steps=3)
        exact=dict(ttt=point.ttt,costs=costs,outside=outside,budget=budget(action,q),
            stocks=stocks,transfers=transfers,mass_error=mass,resource_exceedance=resources,
            witness=response.get("conditional_model_feasibility_witness"),
            coverage=response.get("model_constraint_coverage"),seconds=seconds,
            intervals=probe.executed_interval_responses(state,point,cfg))
        results[name]=dict(surrogate=surrogate,execution=exact,commands=[
            dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                 meters={r:c.diagnostics["rw_meter_green_"+r] for r in cfg.network.ramps})
            for c in sequence.actions(action,3)])
        save(name+".json",results[name])
        print(json.dumps(dict(case=name,surrogate=surrogate["ttt"],exact=point.ttt,
            exact_budget_pass=exact["budget"]["feasible"],seconds=seconds)),flush=True)
    delta={kind:results["east_progressive"][kind]["ttt"]-results["selected"][kind]["ttt"]
           for kind in ("surrogate","execution")}
    save("summary.json",dict(start_sec=4500,horizon_sec=450,seed=29,delta=delta,
        results=results,source_selected_parity=True,
        selected_city_vsl_and_west_unchanged=True,current_native_caps_frozen=True,
        scalar_rollouts=2,execution_rollouts=2,optimizer_iterations=0,new_native_runs=0,
        future_observations_used=False,gain_qualified=False,
        scope="One common observed state, selected city/VSL sequence, east RM10/10/10 vs8/6/4. No claim of actual counterfactual gain."))
    print(json.dumps(dict(delta=delta)),flush=True)

def main():
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    assert not (HERE/"protocol.json").exists(), "Preserve any previous attempt"
    prior=json.loads((R/"restart_supply210/protocol.json").read_bytes())
    pins={k:sha(ROOT/k) for k in prior["source_sha256"]}
    assert pins==prior["source_sha256"]
    assert sha(Path(prior["STOP"]["path"]))==prior["STOP"]["sha256"]
    config=R/"fixedvsl9000_197/config.json"
    save("protocol.json",dict(budget={"surrogate":2,"execution":2,"optimizer":0,"native":0,"fits":0},
        seed=29,start_sec=4500,horizon_sec=450,source_sha256=pins,STOP=prior["STOP"],
        config=dict(path=str(config),sha256=sha(config)),driver_sha256=sha(Path(__file__)),
        input_sha256={str(DEC/f):sha(DEC/f) for f in
           ("state_004500.json","action_004350.json","action_004500.json","action_004500.joint.json")},
        scope="Diagnose finite RM activation, not calibration or native performance"))
    global probe
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    original=probe.probe_selected_meter
    probe.probe_selected_meter=run
    sys.argv=[str(probe.__file__),"--closedloop-recorded","--at=4500",
        "--selected-meter-check","--recorded-selection-check",
        "--warm-head-history","--replay-vsl-history","--probe-label=rm216r1",
        "--recording-dir="+str(DEC),"--tuning-json="+str(config)]
    try:
        probe.main()
    finally:
        probe.probe_selected_meter=original
    assert {k:sha(ROOT/k) for k in pins}==pins
    assert sha(Path(prior["STOP"]["path"]))==prior["STOP"]["sha256"]
    save("completion.json",dict(status="COMPLETE",source101_unchanged=len(pins)==101,STOP_unchanged=True))

if __name__=="__main__":
    main()

