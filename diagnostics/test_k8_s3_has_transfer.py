"""K8-2 (S3): a zero-primal transfer that carries an active derivative is no longer dropped.

Declared unit tests (K8 predeclaration amendment 1 r2, section 2, K8-2 row (e), N14):
  - mass conservation of a zero-primal, active-derivative transfer (source and destination tangents balance)
  - a zero-primal tangent is kept at each of the six sites
  - N14: a zero-primal Dual transfer on route movement:X in a captures_response ledger gives one transfers row and
    accepted_event_count + 1 with served 0; a scalar 0.0 gives no row
Plus equivalence with the K8-1 lines, rebuilt here from the K8-2 source by exact text replacement: identical results
on floats (scalar rollouts unchanged) and identical branch-event records on Duals (trace metadata unchanged).

The modules are executed through the tangent runtime's own Transform, as the SDMPC workers do (forward backend for
exact tangent dictionaries, reverse backend for tape nodes and event records). No VISSIM, no subprocess, no numba.
"""
from __future__ import annotations

import ast
import itertools
import math
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_dual as fwd  # noqa: E402
from evaluation.controllers import sdmpc_tangent_reverse as rev  # noqa: E402
from evaluation.controllers import sdmpc_tangent_runtime as runtime  # noqa: E402
from evaluation.controllers.sdmpc_dual import has_tape, has_transfer  # noqa: E402

PRB = 'evaluation/controllers/physical_ramp_boundary.py'
CAO = 'evaluation/controllers/control_area_objective.py'
AFA = 'evaluation/controllers/area_freeway_accounting.py'
ALO = 'evaluation/controllers/area_leader_objective.py'

# K8-2 line -> K8-1 line (exact text; each must occur exactly once in the K8-2 source).
K81_LINES = {
    PRB: [('        if has_transfer(served):\n', '        if served:\n'),
          ('        if has_transfer(admitted):\n', '        if admitted:\n'),
          ('        if has_transfer(amount):\n', '        if amount:\n')],
    CAO: [('        if count == 0 and not has_tape(count):  # S3: a zero-primal transfer with tape is recorded\n',
           '        if count == 0:\n')],
    AFA: [('[max(0.0, receiving[i] - max(ramp_in_by_link[link][i], 0.0)) for i in range(len(rho_for_flow))]',
           '[max(0.0, receiving[i] - max(0.0, ramp_in_by_link[link][i])) for i in range(len(rho_for_flow))]'),
          ('            if delta_m > 0.0 and (ramp_in_by_link[link][i] > 0.0 or has_tape(ramp_in_by_link[link][i])):\n',
           '            if delta_m > 0.0 and ramp_in_by_link[link][i] > 0.0:\n')],
}
_COUNTER = itertools.count()
_LOADED = []


def source(rel, k81=False):
    text = (ROOT / rel).read_bytes().decode('utf-8').replace('\r\n', '\n')
    if k81:
        for new, old in K81_LINES.get(rel, ()):
            if text.count(new) != 1:
                raise AssertionError(f'K8-2 line not found exactly once in {rel}: {new!r}')
            text = text.replace(new, old)
    return text


def load(rel, backend, k81=False):
    """Execute a module through the runtime Transform with the forward or reverse AD namespace."""
    old = runtime.ad
    try:
        runtime.ad = backend
        name = f'k8_s3_test_{next(_COUNTER)}'
        module = types.ModuleType(name)
        module.__file__ = str(ROOT / rel)
        sys.modules[name] = module
        _LOADED.append(name)
        module.__dict__.update(runtime.namespace())
        tree = runtime.Transform().visit(ast.parse(source(rel, k81), filename=str(ROOT / rel)))
        exec(compile(ast.fix_missing_locations(tree), str(ROOT / rel), 'exec'), module.__dict__)
        return module
    finally:
        runtime.ad = old


def tearDownModule():
    for name in _LOADED:
        sys.modules.pop(name, None)


def d(x):
    """Forward tangent dictionary with exact zeros removed."""
    return {k: v for k, v in fwd.derivative(x).items() if v != 0.0}


def p(x):
    return fwd.primal(x)


def record(trace):
    return (dict(trace.counts), trace.exact_support, trace.discrete_support)


class PredicateTests(unittest.TestCase):
    def test_floats_are_plain_truth(self):
        for x in (0.0, -0.0, 1.0, 1e-300, -2.0, float('nan'), 0, 3):
            self.assertFalse(has_tape(x))
            self.assertEqual(has_transfer(x), bool(x))

    def test_reverse_and_forward_duals(self):
        trace = rev.Trace([.1, .1])
        seed = rev.Dual(0.0, {0: 1.0}, trace)
        self.assertTrue(has_tape(seed) and has_transfer(seed))
        inner = seed + rev.Dual(0.0, {1: 1.0}, trace)        # intermediate: node, tangent None
        self.assertIsNone(inner.tangent)
        self.assertTrue(inner.node and has_tape(inner) and has_transfer(inner))
        guard = rev.Dual._result(0.0, 0, 0, trace)            # primal-guard result: node 0, no tape
        self.assertFalse(has_tape(guard) or has_transfer(guard))
        ftrace = fwd.Trace([.1], track_stencils=False)
        self.assertTrue(has_transfer(fwd.Dual(0.0, {0: 1.0}, ftrace)))
        self.assertFalse(has_transfer(fwd.Dual(0.0, {}, ftrace)))

    def test_branch_record_is_that_of_bool(self):
        for value in (0.0, 2.5):
            records = []
            for fn in (bool, has_transfer):
                trace = rev.Trace([.1])
                fn(rev.Dual(value, {0: 1.0}, trace))
                records.append(record(trace))
            self.assertEqual(records[0], records[1])
            trace = rev.Trace([.1])
            has_tape(rev.Dual(value, {0: 1.0}, trace))
            self.assertEqual(record(trace), ({}, 0, 0))

    def test_predicate_used_only_at_the_six_declared_sites(self):
        uses = {}
        for rel in (PRB, CAO, AFA):
            tree = ast.parse(source(rel))
            uses[rel] = sorted(n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)
                               and isinstance(n.func, ast.Name) and n.func.id in ('has_transfer', 'has_tape'))
        self.assertEqual(uses, {PRB: ['has_transfer'] * 3, CAO: ['has_tape'], AFA: ['has_tape']})
        for rel in (PRB, CAO, AFA):
            source(rel, k81=True)   # every K8-2 line is present exactly once


class RampBoundaryTests(unittest.TestCase):
    def buffer(self, mod, head_m=50.0):
        cohorts = [[head_m, 0.0, 1]] if head_m else []
        b = mod.PhysicalRampBoundary(connector_id='k8', length_m=100.0, head_position_m=head_m, lanes=1,
                                     spacing_m=7.0, travel_speed_kmh=36.0, time_sec=0.0, initial_cohorts=cohorts)
        b.begin_interval(0.0, 10.0)
        b.commit_merge(0.0)
        return b

    def test_zero_head_service_keeps_tangent_and_conserves(self):
        mod = load(PRB, fwd)
        trace = fwd.Trace([.1], track_stencils=False)
        b = self.buffer(mod)
        served = b.apply_head_service(fwd.Dual(0.0, {0: 1.0}, trace), mode='GREEN', green_sec=10.0)
        self.assertEqual((p(served), d(served)), (0.0, {0: 1.0}))
        self.assertEqual(len(b._downstream), 1)
        self.assertEqual(d(b._downstream[0][1]), {0: 1.0})
        self.assertEqual(d(b._head_ready), {0: -1.0})
        self.assertEqual(d(b._head_ready + b._downstream[0][1]), {})          # connector tangent conserved
        b2 = self.buffer(load(PRB, fwd))
        b2.apply_head_service(0.0, mode='GREEN', green_sec=10.0)
        self.assertEqual(b2._downstream, [])                                   # scalar zero: no packet

    def test_zero_admission_keeps_tangent_and_conserves(self):
        for head_m in (50.0, 0.0):
            mod = load(PRB, fwd)
            trace = fwd.Trace([.1], track_stencils=False)
            b = self.buffer(mod, head_m)
            b.apply_head_service(0.0, mode='GREEN', green_sec=10.0)
            b.finish_interval(fwd.Dual(0.0, {0: 1.0}, trace))
            snap = b.snapshot()
            self.assertEqual(d(snap['connector_veh']), {0: 1.0})
            self.assertEqual(d(snap['cumulative_admitted_veh']), {0: 1.0})
            self.assertEqual(d(snap['outside_component_backlog_veh']), {})
            if head_m:
                self.assertEqual([d(n) for _, n in b._upstream], [{0: 1.0}])
            else:
                self.assertEqual(d(b._head_ready), {0: 1.0})
            b.admit_current(fwd.Dual(0.0, {0: 2.0}, trace))
            snap = b.snapshot()
            self.assertEqual(d(snap['connector_veh']), {0: 3.0})
            self.assertEqual(d(snap['cumulative_admitted_veh']), {0: 3.0})
            self.assertEqual(d(snap['cumulative_requested_veh']), {0: 3.0})

    def test_k81_lines_dropped_the_tangent(self):
        mod = load(PRB, fwd, k81=True)
        trace = fwd.Trace([.1], track_stencils=False)
        b = self.buffer(mod)
        b.apply_head_service(fwd.Dual(0.0, {0: 1.0}, trace), mode='GREEN', green_sec=10.0)
        self.assertEqual(b._downstream, [])
        self.assertEqual(d(b._head_ready), {0: -1.0})                          # the connector lost the tangent

    def test_floats_and_positive_duals_match_k81_with_same_records(self):
        """No S3 event (floats, positive Duals): K8-1 results and branch-event records exactly."""
        results = []
        for k81 in (False, True):
            mod = load(PRB, rev, k81=k81)
            out = []
            for service, request, admit in ((0.0, 0.0, 0.0), (0.6, 2.0, 1.5), (1.0, 0.0, 0.25)):
                b = self.buffer(mod)
                b.apply_head_service(service, mode='GREEN', green_sec=10.0)
                b.finish_interval(request)
                b.admit_current(admit)
                out.append(repr(b.snapshot()) + repr(b._upstream) + repr(b._downstream))
            trace = rev.Trace([.1, .1, .1])
            b = self.buffer(mod)
            b.apply_head_service(rev.Dual(0.6, {0: 1.0}, trace), mode='GREEN', green_sec=10.0)
            b.finish_interval(rev.Dual(2.0, {1: 1.0}, trace))
            b.admit_current(rev.Dual(0.5, {2: 1.0}, trace))
            out.append((len(b._upstream), len(b._downstream), len(trace.p1), record(trace)))
            results.append(out)
        self.assertEqual(results[0], results[1])


class LedgerTests(unittest.TestCase):
    MOVE = 'SC1_boundary_in'

    def ledger(self, mod):
        ledger = mod.ModelAreaLedger({'movement:' + self.MOVE: {'inside': 5.0, 'outside': 0.0}}, capture_response=True)
        ledger.begin_response_step('urban', 900.0, 901.0)
        return ledger

    def move(self, ledger, vehicles):
        ledger.transfer('movement:' + self.MOVE, 'storage:k8', vehicles, inside_to_inside=1.0, outside_to_inside=1.0,
                        route_key='movement:' + self.MOVE)

    def test_zero_transfer_keeps_tangent_and_conserves(self):
        mod = load(CAO, fwd)
        trace = fwd.Trace([.1], track_stencils=False)
        ledger = self.ledger(mod)
        self.move(ledger, fwd.Dual(0.0, {0: 1.0}, trace))
        self.assertEqual(ledger.event_count, 1)
        self.assertEqual(d(ledger.flow_counts['movement:' + self.MOVE]), {0: 1.0})
        self.assertEqual(d(ledger.stocks['storage:k8']['inside']), {0: 1.0})
        self.assertEqual(d(ledger.stocks['movement:' + self.MOVE]['inside']), {0: -1.0})
        total = ledger.stocks['storage:k8']['inside'] + ledger.stocks['movement:' + self.MOVE]['inside']
        self.assertEqual((p(total), d(total)), (5.0, {}))                         # mass and its tangent conserved
        self.assertEqual(len(ledger._response['transfers']), 1)
        for k81 in (False, True):                                                 # scalar zero: unchanged early return
            ledger = self.ledger(load(CAO, fwd, k81=k81))
            self.move(ledger, 0.0)
            self.assertEqual((ledger.event_count, dict(ledger.flow_counts), ledger._response['transfers']), (0, {}, []))
        ledger = self.ledger(load(CAO, fwd, k81=True))
        self.move(ledger, fwd.Dual(0.0, {0: 1.0}, trace))
        self.assertEqual((ledger.event_count, ledger._response['transfers']), (0, []))   # K8-1 dropped it

    def test_n14_accepted_event_count(self):
        signals = ('SC1',)
        kinds = ('boundary_in', 'off_ramp', 'boundary_out', 'on_ramp', 'internal')
        moves = {f'SC1_{k}': {'kind': k, 'signal': 'SC1', 'phase': 'SC1_p1'} for k in kinds}
        net = NS(control_area_enabled=True, signals=signals, urban_movements=moves)
        follower = NS(cfg=NS(network=net, simulation=NS(T_u_sec=1.0, T_u_h=1 / 3600, K_cu=1)),
                      _local_models={'SC1': NS(signal='SC1', movements=list(moves), kind_of={m: s['kind'] for m, s in moves.items()})})
        alo = load(ALO, fwd)
        results = {}
        for label, value in (('dual', 'dual'), ('scalar', 0.0)):
            trace = fwd.Trace([.1], track_stencils=False)
            ledger = self.ledger(load(CAO, fwd))
            self.move(ledger, fwd.Dual(0.0, {0: 1.0}, trace) if value == 'dual' else value)
            rows = ledger._response['transfers']
            response = {'schema': 'control-area-fixed-response/v1', 'transfers': rows,
                        'residence': [{'stage': 'urban', 'start_sec': 900.0, 'end_sec': 901.0, 'dt_h': 1 / 3600,
                                       'model_stock_veh': {'movement:' + m: 0.0 for m in moves}}]}
            q = alo.shared_urban_quantities(follower, response, start_sec=900.0, horizon_steps=1)
            results[label] = (len(rows), q['owners']['SC1']['accepted_event_count'],
                              p(q['served_by_movement_veh'][self.MOVE]), d(q['served_by_movement_veh'][self.MOVE]),
                              d(q['owners']['SC1']['net_inflow_veh']))
        self.assertEqual(results['dual'], (1, 1, 0.0, {0: 1.0}, {0: 1.0}))
        self.assertEqual(results['scalar'], (0, 0, 0.0, {}, {}))

    def test_same_records_and_floats_as_k81(self):
        """No S3 event (floats, positive Duals): K8-1 results and branch-event records exactly."""
        results = []
        for k81 in (False, True):
            mod = load(CAO, rev, k81=k81)
            out = []
            for v in (0.0, 1.25, 5.0):
                ledger = self.ledger(mod)
                self.move(ledger, v)
                out.append(repr((ledger.stocks, dict(ledger.flow_counts), ledger.event_count, ledger.ttd_veh,
                                 ledger.entered_veh, [r['vehicles'] for r in ledger._response['transfers']])))
            for v in (1.25, 5.0):
                trace = rev.Trace([.1])
                ledger = self.ledger(mod)
                self.move(ledger, rev.Dual(v, {0: 1.0}, trace))
                out.append((ledger.event_count, len(trace.p1), record(trace)))
            results.append(out)
        self.assertEqual(results[0], results[1])

    def test_site_test_is_a_comparison_not_bool(self):
        """CAO's test stays `count == 0` (non-discrete record); bool(count) would add a discrete comparison per transfer."""
        mod = load(CAO, rev)
        for v in (0.0, 1.25):
            trace = rev.Trace([.1])
            self.move(self.ledger(mod), rev.Dual(v, {0: 1.0}, trace))
            self.assertEqual((trace.counts.get('discrete_comparisons', 0), trace.discrete_support), (0, 0))

    def test_zero_dual_predicate_records_the_k81_comparison(self):
        """At an S3 event the site's own test records exactly the K8-1 `count == 0` comparison (not bool())."""
        for k81 in (False, True):
            trace = rev.Trace([.1])
            count = rev.Dual(0.0, {0: 1.0}, trace)
            kept = (count == 0 and not has_tape(count)) if not k81 else (count == 0)
            self.assertIs(kept, k81)
            self.assertEqual(record(trace), ({'primal_comparisons': 1, 'exact_primal_ties': 1}, 1, 0))


class FreewaySiteTests(unittest.TestCase):
    """The two edited AFA statements, taken from the module source and run through the same Transform."""

    @staticmethod
    def statements(k81=False):
        tree = ast.parse(source(AFA, k81))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_freeway_substep_events')
        assign = next(n for n in ast.walk(fn) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                      and n.targets[0].id == 'receiving_for_mainline')
        merge = next(n for n in ast.walk(fn) if isinstance(n, ast.If)
                     and ast.unparse(n.test).startswith('delta_m > 0.0 and'))
        return assign, merge

    def run_sites(self, backend, ramp_in, receiving=(30.0, 20.0, 10.0), k81=False):
        old = runtime.ad
        try:
            runtime.ad = backend
            ns = dict(runtime.namespace(), has_tape=has_tape)
        finally:
            runtime.ad = old
        assign, merge = self.statements(k81)
        net = NS(v_min=5.0, metanet_kappa_veh_km_lane=40.0,
                 freeway_segment_params={'L': [{'metanet_kappa_veh_km_lane': 40.0}] * 3})
        ns.update(receiving=list(receiving), ramp_in_by_link={'L': list(ramp_in)}, link='L', rho_for_flow=[0.0] * 3,
                  delta_m=1.0, i=1, net=net, direction_params={}, dt_h=10 / 3600, speeds=[80.0, 70.0, 60.0],
                  lengths=[0.5, 0.4, 0.3], lanes_now=[3.0, 2.0, 2.0], rho=25.0, v_new=65.0)
        for node in (assign, merge):
            module = ast.fix_missing_locations(runtime.Transform().visit(ast.Module(body=[node], type_ignores=[])))
            exec(compile(module, str(ROOT / AFA), 'exec'), ns)
        return ns['receiving_for_mainline'], ns['v_new']

    def test_zero_merge_keeps_tangent(self):
        trace = fwd.Trace([.1], track_stencils=False)
        rf, v = self.run_sites(fwd, [0.0, fwd.Dual(0.0, {0: 1.0}, trace), 0.0])
        self.assertEqual((p(rf[1]), d(rf[1])), (20.0, {0: -1.0}))
        expect = -1.0 * (10 / 3600) * 70.0 / (0.4 * 2.0 * (25.0 + 40.0))
        self.assertEqual(p(v), 65.0)
        self.assertEqual(set(d(v)), {0})
        self.assertAlmostEqual(d(v)[0], expect, places=15)
        rf, v = self.run_sites(fwd, [0.0, fwd.Dual(0.0, {0: 1.0}, trace), 0.0], k81=True)
        self.assertEqual((d(rf[1]), d(v)), ({}, {}))                            # K8-1 dropped both

    def test_floats_identical_to_k81(self):
        for r, rec in itertools.product((0.0, -0.0, 3.5, 25.0), ((30.0, 20.0, 10.0), (0.0, 0.0, 0.0), (30.0, 2.0, 1.0))):
            new = self.run_sites(fwd, [0.0, r, 0.0], rec)
            old = self.run_sites(fwd, [0.0, r, 0.0], rec, k81=True)
            self.assertEqual(repr(new), repr(old))
            self.assertEqual([math.copysign(1.0, x) for x in new[0]], [math.copysign(1.0, x) for x in old[0]])

    def test_reverse_records_identical_without_event_and_zero_merge_taped(self):
        for value in (0.0, 4.0):
            out = []
            for k81 in (False, True):
                trace = rev.Trace([.1, .1])
                rf, v = self.run_sites(rev, [0.0, rev.Dual(value, {0: 1.0}, trace), 0.0],
                                       (rev.Dual(30.0, {1: 1.0}, trace), 20.0, 10.0), k81=k81)
                out.append((repr([p(x) for x in rf]), repr(p(v)), len(trace.p1), record(trace),
                            has_tape(rf[1]), has_tape(v)))
            self.assertEqual(out[0][:2], out[1][:2])                            # same primal either way
            if value > 0:
                self.assertEqual(out[0], out[1])                                # no event: identical tape and records
            else:
                self.assertEqual(out[0][4:], (True, True))                      # K8-2 keeps the taped zero merge
                self.assertEqual(out[1][4:], (False, False))                    # K8-1 dropped it

    def test_swapped_clamp_records_the_same_comparison(self):
        """max(merge, 0.0) vs max(0.0, merge): same primal and the same branch record; only the tie keeps the merge."""
        for fast in (False, True):
            old = rev.FAST_PRIMITIVES
            rev.FAST_PRIMITIVES = fast
            try:
                for value in (0.0, 4.0, -1.0):
                    got = []
                    for order in ('merge_first', 'zero_first'):
                        trace = rev.Trace([.1])
                        r = rev.Dual(value, {0: 1.0}, trace)
                        out = rev.maximum(r, 0.0) if order == 'merge_first' else rev.maximum(0.0, r)
                        got.append((p(out), record(trace), out is r))
                    self.assertEqual(got[0][:2], got[1][:2])
                    self.assertEqual((got[0][2], got[1][2]), (value >= 0.0, value > 0.0))
            finally:
                rev.FAST_PRIMITIVES = old


if __name__ == '__main__':
    unittest.main()
