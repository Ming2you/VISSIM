"""Read-only call-path reproduction of the installed offset veto's score source."""
from __future__ import annotations
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from diagnostics.probe_signal_feasibility import setup
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.controllers import rollout_endpoint
from src.controllers.wu_faithful_follower import WuFaithfulFollower


def main():
    cfg, state, _, tuning, _, _, _ = setup()
    follower = adapter.build_priced_wu_link_controller(cfg, tuning).nash_solver
    from src.models.state import ControlAction
    zero = ControlAction.uncontrolled(cfg)
    on = zero.copy()
    on.offsets["SC1004"] = 10.
    source = textwrap.dedent(inspect.getsource(WuFaithfulFollower._solve_followers))
    tests = [n.test for n in ast.walk(ast.parse(source)) if isinstance(n, ast.If) and "offset_keep_margin" in ast.unparse(n.test)]
    assert len(tests) == 1
    guard = compile(ast.Expression(body=tests[0]), "actual offset guard", "eval")
    # Distinct objective/scope values expose which result fields the actual
    # installed method reads. These are counterexamples, not VISSIM predictions.
    responses = {
        False: SimpleNamespace(objective=-10., ttt=50., freeway_ttt=40., urban_ttt=60.),
        True: SimpleNamespace(objective=-30., ttt=55., freeway_ttt=41., urban_ttt=60.),
    }
    calls = []
    def endpoint(state_arg, control, forecast, schedule, spec):
        active = bool(control.offsets.get("SC1004"))
        calls.append({"nonzero_offset": active, "split_ttt": spec.split_ttt, "score_mode": spec.score_mode, "box_walk": spec.box_walk})
        return responses[active]
    with patch.object(rollout_endpoint, "evaluate_price_point", endpoint):
        cost_zero = follower._rollout_horizon_ttt(state, zero, [object()])[0]
        cost_on = follower._rollout_horizon_ttt(state, on, [object()])[0]
    veto = eval(guard, {"self": follower, "ttt_off": cost_zero, "ttt_on": cost_on})
    assert (cost_zero, cost_on) == (100., 101.)
    assert veto and responses[True].objective < responses[False].objective
    # Naively substituting negative J into the relative formula retains a
    # candidate that is worse (-100 > -100.1), contrary to the guard's intent.
    naive = eval(guard, {"self": follower, "ttt_off": -100.1, "ttt_on": -100.})
    assert not naive
    report = {
        "scope": "actual installed follower method and guard expression; mocked endpoint result fields only, no plant or performance claim",
        "follower_class": type(follower).__module__ + "." + type(follower).__name__,
        "rollout_method": follower._rollout_horizon_ttt.__func__.__qualname__,
        "guard_margin": follower.offset_keep_margin,
        "guard_expression": ast.unparse(tests[0]), "calls": calls,
        "counterexample": {"zero_global_ttt": cost_zero, "on_global_ttt": cost_on,
                           "zero_area_j": -10., "on_area_j": -30., "actual_guard_reverts_offset": bool(veto)},
        "negative_j_naive_substitution": {"zero_j": -100.1, "on_j": -100., "guard_reverts_worse_on": bool(naive)},
        "source_sha256": {str(Path(inspect.getfile(WuFaithfulFollower)).relative_to(ROOT)): hashlib.sha256(Path(inspect.getfile(WuFaithfulFollower)).read_bytes()).hexdigest()},
        "status": "REPRODUCED",
    }
    path = ROOT / "diagnostics/offset_objective_veto.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
