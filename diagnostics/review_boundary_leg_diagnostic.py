"""Bounded source-dependency audit; no model execution or runtime mutation."""
import ast
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "vendor/NumSim-mine/src/models/state.py",
    "vendor/NumSim-mine/src/controllers/leader.py",
    "vendor/NumSim-mine/src/controllers/stackelberg_mpc.py",
    "vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py",
    "vendor/NumSim-mine/src/controllers/wu_faithful_follower.py",
    "evaluation/controllers/area_leader_objective.py",
]


def main():
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES}
    trees = {p: ast.parse((ROOT / p).read_text(encoding="utf-8-sig")) for p in FILES}
    state = trees[FILES[0]]
    methods = {n.name: n for n in ast.walk(state) if isinstance(n, ast.FunctionDef)}
    boundary, protected = methods["boundary_leg_vehicles"], methods["protected_accumulation_veh"]
    def calls(node):
        return sorted({n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)})
    assert "boundary_leg_vehicles" not in calls(protected)
    # The sum only mutates local names/its newly constructed set, not self/net attributes or containers.
    writes = [ast.unparse(n) for n in ast.walk(boundary)
              if isinstance(n, (ast.Attribute, ast.Subscript)) and isinstance(n.ctx, ast.Store)]
    assert writes == []
    exact_key_sites = []
    for root in (ROOT / "evaluation/controllers", ROOT / "vendor/NumSim-mine/src"):
        for p in root.rglob("*.py"):
            if "tests" in p.parts:
                continue
            for number, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
                if "leader_boundary_leg_excluded_veh" in line:
                    exact_key_sites.append({"path": p.relative_to(ROOT).as_posix(), "line": number, "text": line.strip()})
    a, b = 3177.0260891219514, 3177.026089121952
    changes = [p for p in FILES if hashes[p] != hashlib.sha256((ROOT / p).read_bytes()).hexdigest()]
    assert not changes
    out = {
        "schema_version": "boundary-leg-diagnostic-readback-review/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "current Omega/follower_ttt selection path only; not a general state-accumulation-mode exemption",
        "source_sha256": hashes,
        "source_changes": changes,
        "parent_reported_difference": {"first": a, "second": b, "absolute_veh": b-a,
            "ulp_at_first": math.ulp(a), "ulps": (b-a)/math.ulp(a), "independent_run_comparison": False},
        "exact_diagnostic_key_non_test_source_sites": exact_key_sites,
        "boundary_function": {"line": boundary.lineno, "attribute_or_subscript_writes": writes,
            "unordered_float_sum": "local boundary_storage_links set iterated at state.py:1382"},
        "protected_accumulation": {"line": protected.lineno, "calls": calls(protected),
            "uses_boundary_leg_vehicles": False},
        "readback_conclusion": {
            "selection": "No current-path dependency: follower_ttt chooses passed endpoint base; area normalizer preserves diagnostic but ranks endpoint J",
            "lambda": "No exact diagnostic key consumer; protected_accumulation_veh is computed separately",
            "physical_state": "boundary sum has no self/net writes and returned diagnostic is not read by transition functions",
            "metadata": "exact-key copies survive in output and may differ; strict byte comparator FAIL must remain preserved",
            "other_mode": "state_accumulation objective uses state_base containing the boundary subtraction; no exemption claimed"},
        "suggested_validation_environment": "Parent and all spawned workers inherit one explicitly recorded PYTHONHASHSEED set before interpreter startup; do not set or change it inside an existing interpreter",
        "not_performed": ["runtime edits", "sorting or resumming production data", "loosening comparator", "MPC", "endpoint", "VISSIM"],
    }
    path = ROOT / "diagnostics/boundary_leg_diagnostic_readback_review.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "exact_key_sites": len(exact_key_sites), "source_changes": changes, "new_model_evaluations": 0}))


if __name__ == "__main__":
    main()
