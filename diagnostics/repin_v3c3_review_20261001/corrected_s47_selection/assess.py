"""Summarize the two completed replays; no plant or simulator invocation."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INTEGRATION = ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926"
SELECT = INTEGRATION / "closedloop_recorded2700_select_sc1001_corrected47"
REPLAY = INTEGRATION / "closedloop_recorded2700_select_check_sc1001_corrected47"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ast_entries(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return {getattr(n, "name", f"index{i}"): ast.dump(n, include_attributes=False)
            for i, n in enumerate(tree.body)}


def main():
    protocol = read(HERE / "protocol.json")
    replay = read(REPLAY / "summary.json")
    joint = read(SELECT / "unused_action.joint.json")
    selection = read(SELECT / "summary.json")
    assert replay["native_started"] is False
    assert selection["native_started"] is False
    assert not replay["future_observation_inputs"]
    assert set(replay["results"]) == {"held_actual", "selected"}
    metrics = {}
    for name, row in replay["results"].items():
        stocks = row["cost_by_stock"]
        omega = row["ttt_omega_veh_h"]
        east, west = stocks["freeway:FW_E"], stocks["freeway:FW_W"]
        ramps = sum(v for k, v in stocks.items() if k.startswith("ramp:"))
        assert abs(sum(stocks.values()) - omega) < 1e-8
        quantities = row["canonical_quantity_constraints"]
        assert quantities["feasible"]
        assert row["saved_state_stock_witness"] == {"states": 4, "passed": True}
        assert row["max_resource_exceedance_veh"] < 1e-7
        residual = max(abs(r["residual"]) for r in row["ramps"].values())
        assert residual < 1e-7
        metrics[name] = dict(
            omega_veh_h=omega, east_veh_h=east, west_veh_h=west,
            ramps_veh_h=ramps, other_omega_veh_h=omega-east-west-ramps,
            tracked_outside_veh_h=row["tracked_outside_residence_veh_h"],
            omega_plus_tracked_outside_veh_h=row["ttt_with_tracked_outside_veh_h"],
            np=quantities["np"], nuf=quantities["nuf"],
            max_ramp_mass_residual_veh=residual,
            max_resource_exceedance_veh=row["max_resource_exceedance_veh"],
            saved_state_stock_witness=row["saved_state_stock_witness"],
            merge_by_ramp={k: r["merge"] for k, r in row["ramps"].items()},
            replay_wall_sec=row["wall_sec"])
    held, chosen = (replay["results"][k] for k in ("held_actual", "selected"))
    assert chosen["validation"]["written_command_binding_passed"]
    assert chosen["validation"]["native_execution_status"] == "pending"
    command_changes = []
    assert len(held["commands"]) == len(chosen["commands"]) == 3
    for block, (old, new) in enumerate(zip(held["commands"], chosen["commands"])):
        changes = {}
        for field in ("vsl", "meters", "green_times", "offsets"):
            assert old[field].keys() == new[field].keys()
            changes[field] = {k: {"held": old[field][k], "selected": new[field][k]}
                              for k in old[field] if old[field][k] != new[field][k]}
        assert not changes["vsl"] and not changes["meters"]
        command_changes.append(dict(block=block, changes=changes))
    deltas = {k: metrics["selected"][k]-metrics["held_actual"][k]
              for k in metrics["held_actual"] if k.endswith("veh_h")}
    unchanged = {}
    driver = "diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py"
    for p, expected in protocol["source_pins"].items():
        if p != driver:
            actual = sha(ROOT / p)
            assert actual == expected, p
            unchanged[p] = actual
    before = ast_entries(HERE / "probe_selected_arrival_path.before_replay.txt")
    after = ast_entries(ROOT / driver)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    assert changed == ["probe_levers"]
    artifacts = [SELECT / "summary.json", SELECT / "unused_action.joint.json",
                 SELECT / "unused_action.joint_written.json", REPLAY / "summary.json"]
    result = dict(
        status="offline_selection_and_canonical_replay_complete_not_qualified",
        seed=47, start_sec=2700, horizon_sec=450,
        metrics=metrics, deltas_selected_minus_held=deltas,
        omega_improvement_percent=-100*deltas["omega_veh_h"]/metrics["held_actual"]["omega_veh_h"],
        surrogate=replay["surrogate"],
        surrogate_vs_canonical_delta_error_veh_h=deltas["omega_veh_h"]-replay["surrogate"]["delta_ttt"],
        outside_scope=replay["outside_cost_scope"], command_changes=command_changes,
        held_meter_commands=held["commands"][0]["meters"],
        controller_wall_sec=selection["controller_wall_sec"],
        decision_budget=joint["decision_budget"],
        work_counts={k: joint["physical_response_cache"][k] for k in
                     ("requests", "cache_hits", "scalar_rollouts", "tangent_rollouts", "total_rollouts", "closed")},
        pfo={k: joint["selection"]["pfo_warm_start"][k] for k in
             ("executed_iterations", "accepted_iterations", "converged", "status")},
        sdmpc_candidates=joint["selection"]["candidates"],
        fresh_budget_initialization=joint["selection"]["budget_initialization"],
        converged=joint["selection"]["converged"],
        selection_status=joint["selection"]["selection_status"],
        known_offset_gradient_failure=True, native_gain_qualified=False,
        all_derivatives_qualified=False, new_native_runs=0, push=False,
        verification=dict(unchanged_sources=unchanged,
                          replay_harness_changed_functions=changed,
                          replay_harness_sha256=sha(ROOT / driver),
                          result_sha256={str(p.relative_to(ROOT)): sha(p) for p in artifacts}))
    (HERE / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    protocol.update(status=result["status"], canonical_replay_completed=2,
                    canonical_replay_session_exit=0,
                    canonical_replay_wall_sec=sum(v["replay_wall_sec"] for v in metrics.values()),
                    assessment_sha256=sha(HERE / "assessment.json"))
    (HERE / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "deltas": deltas,
                      "omega_improvement_percent": result["omega_improvement_percent"],
                      "source_pins_passed": len(unchanged)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
