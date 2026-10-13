"""Scoped diagnostic of one physical branch service, no on-disk model edits.

Compile the existing method with exactly one rate expression replaced. This
isolates a source-supported counterfactual before deciding on a runtime option.
All requests, shared allocation, receipts, delays, and ledger code are original.
"""
from contextlib import contextmanager
from pathlib import Path
import ast
import hashlib
import inspect
import json
import textwrap

HERE = Path(__file__).resolve().parent
EXPRESSION = "spec['per_lane_capacity_veh_h'] * branch['lanes']"


def settings():
    option = json.loads((HERE / 'config.json').read_bytes())
    evidence_path = (HERE / option['source_assessment']).resolve()
    evidence = json.loads(evidence_path.read_bytes())
    rates = option['diagnostic_branch_service_veh_h']
    assert set(rates) == {'1129:branch:bypass'}
    assert rates['1129:branch:bypass'] == evidence['past_sample_achieved_rate_lower_bound_veh_h'] == 904
    assert all(x['high_sec'] < 2250 for x in evidence['certain_observed_crossings'])
    return rates, evidence_path


def service(spec, branch, rates):
    key = str(spec['decision']) + ':branch:' + branch['service_group']
    default = spec['per_lane_capacity_veh_h'] * branch['lanes']
    return rates[key] if key in rates else default


def compile_method(original, rates):
    source = textwrap.dedent(inspect.getsource(original))
    tree = ast.parse(source)
    match = ast.dump(ast.parse(EXPRESSION, mode='eval').body)
    class Replace(ast.NodeTransformer):
        count = 0
        def visit_BinOp(self, node):
            if ast.dump(node) == match:
                self.count += 1
                return ast.copy_location(ast.parse('_branch_service315(spec, branch)', mode='eval').body, node)
            return self.generic_visit(node)
    change = Replace()
    tree = change.visit(tree)
    assert change.count == 1, 'Reject unexpected source shape'
    ast.fix_missing_locations(tree)
    namespace = dict(original.__globals__)
    namespace['_branch_service315'] = lambda spec, branch: service(spec, branch, rates)
    exec(compile(tree, str(HERE / 'candidate.py') + ':scoped-original', 'exec'), namespace)
    return namespace[original.__name__], hashlib.sha256(source.encode()).hexdigest()


@contextmanager
def enabled():
    from evaluation.controllers.aggregate_route_corridors import Routes
    rates, evidence = settings()
    original = Routes.advance_one
    replacement, source_hash = compile_method(original, rates)
    Routes.advance_one = replacement
    try:
        yield dict(rates=rates, original_method_sha256=source_hash,
                   evidence=str(evidence), aggregate_method_only=True,
                   future_inputs=False, on_disk_production_changes=0)
    finally:
        Routes.advance_one = original
