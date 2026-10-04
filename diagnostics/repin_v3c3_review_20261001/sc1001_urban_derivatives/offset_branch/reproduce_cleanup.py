"""Small diagnostic of shared-approach mass derivatives; no traffic rollout."""
import ast
import inspect
import json
from collections import defaultdict, deque
from pathlib import Path

from evaluation.controllers import sdmpc_dual as forward, sdmpc_tangent_reverse as reverse
from evaluation.controllers.sdmpc_tangent_runtime import Transform, namespace
from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
from diagnostics.test_shared_signal_approach import fixture, packet
from diagnostics.test_sdmpc_tangent import RampZeroTransferTests


def main():
    records = []
    for backend in (forward, reverse):
        ns = dict(namespace(), math=backend.MathProxy(), defaultdict=defaultdict, deque=deque,
                  _tangent_float=backend.float_keep, _tangent_min=backend.minimum,
                  _tangent_max=backend.maximum, _tangent_math=backend.MathProxy())
        tree = Transform().visit(ast.parse(inspect.getsource(SharedSignalApproach)))
        exec(compile(ast.fix_missing_locations(tree), '<shared-queue-repro>', 'exec'), ns)
        cls = ns['SharedSignalApproach']
        for case in ('near_empty_service_packet', 'cleanup_without_lane_change'):
            trace = backend.Trace([.0005], track_stencils=False)
            if case == 'near_empty_service_packet':
                obj = fixture([packet('1', 'city', 'E', .5+1e-14)], cls=cls)
                green = backend.Dual(.5, {0:1.}, trace)
                obj.advance(0, {'1':green, '2':0., '3':0.}, dict(E=10., S=10., N=10.))
                expected = -1.
            else:
                obj = fixture(cls=cls)
                amount = backend.Dual(1e-14, {0:1.}, trace)
                obj.queues['1'].append([0, 'city', 'E', amount])
                obj.initial = amount
                obj._mandatory_lane_changes()
                expected = 1.
            error = obj.initial+obj.admitted-obj.departed-obj.stock()
            slope = lambda value: float(RampZeroTransferTests.gradient(backend, trace, value))
            records.append(dict(backend=backend.__name__, case=case,
                primal_mass_error=backend.primal(error), derivative_mass_error=slope(error),
                served_derivative=slope(obj.departed), remaining_derivative=slope(obj.stock()),
                expected_remaining_active_branch=expected))
    report = dict(scope='Synthetic reproduction of derivative loss, not proof of the complete recorded offset discrepancy.',
                  new_native_runs=0, full_rollouts=0, records=records)
    Path(__file__).with_name('cleanup_reproduction.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
