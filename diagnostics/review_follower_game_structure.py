"""Read source and a completed decision; never import or execute a controller."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "diagnostics/follower_game_structure_review.json"
PREFLIGHT = "diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z"
CONFIG = "diagnostics/contract_candidate_configs_v4/n7_area_beta300.json"
SOURCES = [
    "evaluation/controllers/vissim_stackelberg_adapter.py",
    "evaluation/controllers/area_runtime.py",
    "evaluation/controllers/area_leader_objective.py",
    "evaluation/controllers/area_follower_objective.py",
    "evaluation/controllers/area_meter_finalization.py",
    "evaluation/controllers/link_predictor.py",
    "evaluation/controllers/local_signal_service.py",
    "evaluation/controllers/signal_actuation_contract.py",
    "vendor/NumSim-mine/src/controllers/priced_wu_link_controller.py",
    "vendor/NumSim-mine/src/controllers/wu_faithful_follower.py",
    "vendor/NumSim-mine/src/controllers/wu_distributed.py",
    "vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py",
    "vendor/NumSim-mine/src/controllers/stackelberg_mpc.py",
    "vendor/NumSim-mine/src/controllers/leader.py",
    "vendor/NumSim-mine/src/controllers/rollout_endpoint.py",
    "vendor/NumSim-mine/src/models/state.py",
    "vendor/NumSim-mine/src/config/default.yaml",
]


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def main():
    paths = SOURCES + [CONFIG, PREFLIGHT + "/manifest.json", PREFLIGHT + "/action.json", PREFLIGHT + "/action.csv"]
    before = {p: sha(p) for p in paths}
    cfg, action, manifest = read(CONFIG), read(PREFLIGHT + "/action.json"), read(PREFLIGHT + "/manifest.json")
    diag, metadata = action["diagnostics"], action["metadata"]
    selected = {
        k: v for k, v in diag.items()
        if k.startswith(("control_area_follower_", "control_area_offset_", "control_area_phase_",
                         "leader_selected_", "leader_lambda_", "nash_", "wu_faithful_np_pd_",
                         "wu_faithful_np_cand_"))
    }
    selected.update({k: diag[k] for k in (
        "leader_candidate_count", "leader_fallback_candidate_count",
        "leader_fallback_guard_leader_objective", "wu_b2_price_refresh_count") if k in diag})
    writer = {k: v for k, v in metadata.items() if k.startswith(("control_area_meter_", "controller_status"))}
    beta = cfg["control_area_objective"]["beta_seconds"]
    checks = {}
    for label in ("follower", "offset_on", "offset_off"):
        prefix = "control_area_" + label + "_"
        computed = diag[prefix + "ttt_veh_h"] - beta / 3600.0 * diag[prefix + "ttd_veh"]
        recorded = diag[prefix + "objective_veh_h"]
        checks[label] = {"computed_objective_veh_h": computed, "recorded_objective_veh_h": recorded,
                         "absolute_difference_veh_h": abs(computed - recorded),
                         "valid": math.isclose(computed, recorded, rel_tol=0., abs_tol=1e-10)}
    assert all(x["valid"] for x in checks.values())
    assert cfg["agent_topology"]["metering_in_gne"] is True
    assert "in_gne" not in cfg["phase_price"]
    assert diag["control_area_phase_finalization_source"] == "phase_refinement"
    assert diag["control_area_phase_outer_matches_scored"] == 1
    assert diag["control_area_phase_finalized_changed_values"] == 59
    assert diag["leader_selected_stage_fallback_pfo"] == 1
    assert diag["control_area_follower_additional_cost_veh_h"] == 0
    assert diag["nash_converged"] == 1
    # These are recorded arithmetic/flag checks, not a new equilibrium test.
    wt = cfg["phase_price"]["weight"]
    fields = [
        {"owner": "controller.nash_solver (LinkAgentWuFollower / WuFaithfulFollower)",
         "fields": ["_prev_coupling"], "scope": "active, read at each solve and written after Jacobi/offset work",
         "read": "wu_faithful_follower.py:4131", "write": "wu_faithful_follower.py:4686"},
        {"owner": "controller.nash_solver._wu (WuDistributedController)",
         "fields": ["_last_offramp_flow", "_has_last_offramp_flow", "_omega_f"],
         "scope": "active; chosen local-query off-flow cache is read by subsequent coupling/local calls",
         "read": "wu_distributed.py:250; wu_faithful_follower.py:542", "write": "link_predictor.py:500"},
        {"owner": "controller.nash_solver", "fields": ["_lambda_P", "_lambda_UF", "_np_corrector_pending",
             "_np_step_time", "_np_prev_accum", "_np_last_real_q", "_np_last_sum_nin", "_np_bias_ratio"],
         "scope": "standing dual/corrector state; mode-dependent reads and commits; PFO is leader=None",
         "read_write": "wu_faithful_follower.py:4168-4243; stackelberg_wu_metered.py:2435-2497"},
        {"owner": "controller.nash_solver", "fields": ["_seg_traj", "_gne_phase_override",
             "_phase_ctx_cache", "_phase_resolved_active_signals", "_control_area_link_phase_context"],
         "scope": "per-solve / per-local-call state; some reset or scoped-restored, not all persistent"},
        {"owner": "controller.nash_solver", "fields": ["signal_marginal_price", "signal_marginal_price_ref",
             "signal_marginal_price_weight", "signal_marginal_price_trust_sec", "metering_marginal_price",
             "metering_marginal_price_ref", "metering_marginal_price_weight", "metering_marginal_price_trust_frac",
             "vsl_marginal_price", "vsl_marginal_price_ref", "vsl_marginal_price_weight", "vsl_marginal_price_trust_kmh",
             "offset_marginal_price", "offset_marginal_price_ref", "offset_marginal_price_weight",
             "offset_marginal_price_trust_sec", "signal_phase_price", "signal_phase_price_ref",
             "signal_phase_price_weight", "green_offset_cross_price", "vsl_meter_cross_price"],
         "scope": "price surfaces/references; local derivative helpers temporarily remove selected channels"},
        {"owner": "controller", "fields": ["previous_control", "_pfo_incumbent_center", "_pfo_incumbent_eval",
             "_signal_price_last_step"], "scope": "active search/selection/refresh inputs"},
        {"owner": "controller", "fields": ["_pfo_fallback_previous_control", "_link_share_ctx", "_nuf_solve_cache"],
         "scope": "conditional base-fallback / link-share-search / candidate-dedupe inputs, dormant in reviewed path"},
        {"owner": "controller", "fields": ["_signal_price_meta"],
         "scope": "read sites found copy diagnostics into result or update reporting flags; no numeric strategy branch found"},
    ]
    after = {p: sha(p) for p in paths}
    changes = [p for p in paths if before[p] != after[p]]
    assert not changes
    report = {
        "schema_version": "follower-game-structure-review/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read-only source inspection and completed decision arithmetic; no imports of controller, endpoint, MPC or simulator",
        "source_baseline": "dd13e08 (parent-declared freeze; complete file SHA256 below)",
        "source_sha256": {p: before[p] for p in SOURCES},
        "input_sha256": {p: before[p] for p in paths if p not in SOURCES},
        "source_changes": changes,
        "recorded_preflight": {"path": PREFLIGHT, "manifest_valid": manifest.get("valid"),
            "exit_code": manifest.get("exit_code"), "source_unchanged": manifest.get("source_unchanged"),
            "inputs_unchanged": manifest.get("inputs_unchanged")},
        "selected_config": {k: cfg.get(k) for k in ("agent_topology", "phase_price", "price_parallel", "control_area_objective")},
        "selected_mpc_overrides": cfg.get("config_overrides", {}).get("mpc", {}),
        "effective_defaults_source_review": {
            "phase_price_in_gne": {"value": False, "source": "priced_wu_link_controller.py:543; no config override"},
            "price_iter_max": {"value": 1, "source": "stackelberg_wu_metered.py:339; no builder override"},
            "candidate_dedupe_enabled": {"value": False, "source": "stackelberg_wu_metered.py:247; no builder override"},
            "np_candidate_lambda": {"value": True, "source": "models/state.py:762; YAML/config do not override"},
            "np_primal_dual_iters": {"value": 4, "source": "adapter.flagship_config_overrides:6999"},
            "nuf_coordination_mode": {"value": "equality", "source": "config/default.yaml:270"}},
        "recorded_action_evidence": selected,
        "recorded_writer_evidence": writer,
        "objective_arithmetic": checks,
        "first_order_price_identity": {
            "assumptions": "same operating point, local model/control path and coordinate; finite-difference approximation",
            "external_price": "p_i = D_i J_Omega - D_i L_i",
            "local_surrogate": "L_i + w_i * p_i dot (u_i-u_i_ref)",
            "derivative": "(1-w_i) D_i L_i + w_i D_i J_Omega",
            "phase_weight": wt, "remaining_local_gradient_weight": 1.0-wt,
            "beta_double_reward_in_final_endpoint": False,
            "general_exact_cancellation_proven": False,
            "phase_zero_sum_gauge": "(n-1)/n gives a zero-mean gradient only for the actual +delta, -delta/(n-1) exchange; bound/physical projection can alter this direction while nominal delta remains in the denominator"},
        "operational_fields": fields,
        "findings": [
            {"id": "game_schedule", "status": "code-and-record-confirmed", "claim": "meter/VSL inside Jacobi; offset and full phase refinement after it; final four-lever equilibrium not certified"},
            {"id": "final_score", "status": "code-and-record-confirmed", "claim": "finalized phase and meter are scored by Omega; old stale-final-vector and global-score veto issues are already repaired"},
            {"id": "candidate_state", "status": "source-dependency-confirmed", "claim": "state.copy is not a whole follower snapshot; warm coupling and local off-flow caches persist", "not_claimed": "numerically measured candidate permutation effect"},
            {"id": "price_identity", "status": "algebra-and-code", "claim": "global-minus-local avoids simple local double counting only under matched derivative conditions; phase weight .25 deliberately blends gradients"},
            {"id": "meter_derivative_context", "status": "source-confirmed", "claim": "global meter probe holds VSL; local meter cost nests a VSL best response; subtraction is not a like-for-like partial derivative"},
            {"id": "pfo_game", "status": "source-and-record-confirmed", "claim": "PFO leader=None removes quantity target and split-meter external price, while final ranking still uses Omega J"},
            {"id": "physical_quantization", "status": "source-confirmed", "claim": "final meter quantization is aligned with endpoint/writer, but native local BR candidates are evaluated before that finalizer"},
        ],
        "not_performed": ["new local costs", "candidate reordering replay", "new endpoint", "MPC", "VISSIM",
                          "performance benchmark", "runtime mutation", "algorithm changes"],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "objective_checks": len(checks), "source_changes": changes,
                      "new_model_evaluations": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
