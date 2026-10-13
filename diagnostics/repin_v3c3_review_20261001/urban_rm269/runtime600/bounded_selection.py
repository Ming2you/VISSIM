"""One explicitly budgeted offline comparison; no live/native parameter edits.

Use canonical verification with one PFO and one coordination iteration. All
other canonical parameters, three control blocks, caps, finite RM neighbors,
and feasibility checks remain active. This is a changed search budget, not an
equivalent-optimizer claim. Serialized workers receive this effective policy.
"""
import json
from copy import deepcopy
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]

if __name__ == '__main__':
    from evaluation import parameters
    document = parameters.load()
    changes = json.loads((HERE/'bounded_iterations.json').read_bytes())
    assert set(changes) == {'sdmpc', 'sdmpc_pfo_cap'}
    for section, values in changes.items():
        assert values == {'max_iterations': 1}
        assert document[section]['max_iterations'] == 2
        document[section]['max_iterations'] = values['max_iterations']
    # Use the SAME applied historical prices in both offline comparisons.
    # Validate their receipt against the original two-iteration policy, then
    # explicitly label this one-interval budget experiment. Never rewrite the
    # saved action, receipt, or production policy hash acceptance rule.
    from evaluation.controllers import sdmpc
    load_prices = sdmpc.load_prices
    def common_history(path, state, policy):
        assert policy['max_iterations'] == policy['pfo_cap_options']['max_iterations'] == 1
        previous_policy = deepcopy(policy)
        previous_policy['max_iterations'] = 2
        previous_policy['pfo_cap_options']['max_iterations'] = 2
        prices, receipt = load_prices(path, state, previous_policy)
        receipt = dict(receipt, offline_iteration_budget_change=changes,
                       validated_against_previous_policy=True)
        return prices, receipt
    sdmpc.load_prices = common_history
    print(json.dumps(dict(offline_iteration_budget=changes,
        native_runs=0, canonical_parameters_modified=False)), flush=True)
    script = ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv[0] = str(script)
    runpy.run_path(str(script), run_name='__main__')
