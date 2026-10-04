"""K8-3: S1 pre-signal admission space and S1-OWN meter-owner spill attribution.

Declared unit tests (K8 predeclaration amendment 1 r2 §2 K8-3 row (iv), §B.6, §G; DEFECTS.md §2.4; S1_OWNER.md §7):
  AdmissionSpaceTests  the seven S1 tests of DEFECTS §2.4 (test 6 also asserts "spill E <= rejected")
  MeterOwnerTests      T-OWN-1 ... T-OWN-14 (S1_OWNER.md §7)
Modules run through the tangent runtime's own Transform (forward backend: exact tangent dictionaries; reverse
backend: tape nodes, branch records and compiled output sweeps), or as plain imports for float rollouts. The toy
`Toy` mirrors one coupled second of the deployed order: the ramp buffer's local interval (merge, head service;
LaneRampRuntime.advance), the urban movement -> ramp loop (urban_flow_accounting.urban_substep_accounted, the lines
around the S1-OWN site 1 copied with their order), then LaneRampRuntime.finish (admit_current). The four real site
integrations are checked by the K8-3 prototype reproduction gate, not here.
T-OWN-6 reads a captured deployed request template: env K8_CAPTURED_TEMPLATE (the K8-3 gate capture, e.g.
<gates_out/k83>/out/002700/cap_k83/template.pickle); it prints the template path and sha256 and fails without it.
No VISSIM, no subprocess. The reverse sweeps need the pinned numba on PYTHONPATH (as the SDMPC workers).
"""
from __future__ import annotations

import ast
import copy
import hashlib
import itertools
import math
import os
import pickle
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

PRB = 'evaluation/controllers/physical_ramp_boundary.py'
LRR = 'evaluation/controllers/lane_ramp_runtime.py'
CAO = 'evaluation/controllers/control_area_objective.py'
SPILL = 'evaluation/controllers/meter_spill.py'
SDMPC = 'evaluation/controllers/sdmpc.py'
PASSIVE = 'PASSIVE_OMEGA'
# K8-3 line -> K8-2 line (exact text; each occurs exactly once in the K8-3 source): the pre-S1 admission rule.
K82_LINES = {PRB: [('        free = self._admission_space_veh()\n',
                    '        free = max(0.0, self.capacity_veh-self._stocks()["connector_veh"])\n'),
                   ('        return self._admission_space_veh()\n',
                    "        return max(0., self.capacity_veh-self._stocks()['connector_veh'])\n")]}
_COUNTER = itertools.count()
_LOADED = []


def source(rel, k82=False):
    text = (ROOT / rel).read_bytes().decode('utf-8').replace('\r\n', '\n')
    if k82:
        for new, old in K82_LINES.get(rel, ()):
            if text.count(new) != 1:
                raise AssertionError(f'K8-3 line not found exactly once in {rel}: {new!r}')
            text = text.replace(new, old)
    return text


def load(rel, backend, k82=False):
    """Execute a module through the runtime Transform with the forward or reverse AD namespace."""
    old = runtime.ad
    try:
        runtime.ad = backend
        name = f'k8_s1_test_{next(_COUNTER)}'
        module = types.ModuleType(name)
        module.__file__ = str(ROOT / rel)
        sys.modules[name] = module
        _LOADED.append(name)
        module.__dict__.update(runtime.namespace())
        tree = runtime.Transform().visit(ast.parse(source(rel, k82), filename=str(ROOT / rel)))
        exec(compile(ast.fix_missing_locations(tree), str(ROOT / rel), 'exec'), module.__dict__)
        return module
    finally:
        runtime.ad = old


def tearDownModule():
    for name in _LOADED:
        sys.modules.pop(name, None)


def modules(backend=None):
    """PRB, LaneRampRuntime, ledger and meter_spill modules: plain imports (backend None) or transformed."""
    if backend is None:
        from evaluation.controllers import physical_ramp_boundary, lane_ramp_runtime, control_area_objective
        from evaluation.controllers import meter_spill, sdmpc
        return NS(prb=physical_ramp_boundary, lrr=lane_ramp_runtime, cao=control_area_objective,
                  spill=meter_spill, sdmpc=sdmpc, backend=None)
    return NS(prb=load(PRB, backend), lrr=load(LRR, backend), cao=load(CAO, backend), spill=load(SPILL, backend),
              sdmpc=load(SDMPC, backend), backend=backend)


def p(x):
    return fwd.primal(x)


def d(x):
    return {k: v for k, v in fwd.derivative(x).items() if v != 0.0}


def record(trace):
    return (len(trace.p1), dict(trace.counts), trace.exact_support, trace.discrete_support)


def buffer(mods, *, head_ready=0, posthead=0, upstream=0, length=120., head=60., lanes=1, spacing=6.,
           speed=36., t=0.):
    """10490-like connector: capacity 20, pre-head capacity 10 for the defaults."""
    rows = ([[head, 0., 1]] * head_ready + [[head + 1., 0., 1]] * posthead + [[head - 30., 0., 1]] * upstream)
    return mods.prb.PhysicalRampBoundary(connector_id='k8', length_m=length, head_position_m=head, lanes=lanes,
                                         spacing_m=spacing, travel_speed_kmh=speed, time_sec=t, initial_cohorts=rows)


def interval(b, *, service=0., mode='RED', request=0., accepted=None):
    ready = b.begin_interval(b.time_sec)['eligible_merge_veh']
    b.commit_merge(ready if accepted is None else accepted)
    b.apply_head_service(service, mode=mode, green_sec=None if mode != 'GREEN' else 10.)
    return b.finish_interval(request)


def lane_runtime(mods, buffers):
    rt = object.__new__(mods.lrr.LaneRampRuntime)
    rt.buffers = dict(buffers)
    rt.predebited = None
    rt.receiving_nodes, rt.lane_coupling = {}, {}
    return rt


class Toy:
    """One metered ramp fed by urban movements, one coupled second per step (see the module docstring).

    k7=True replaces the S1 room by the pre-S1 whole-connector room (the K7 rule) on this buffer only, for the
    counterfactual rollouts of T-OWN-2. spill=False makes the six S1-OWN site entry points no-ops (rule off)."""
    RAMP = 'RM_C10490'
    OWNERS = {'ramp:RM_C10490': 'FW_E', 'ramp:RM_C10482': 'FW_W', 'ramp:RM_C10484': 'FW_E', 'ramp:RM_C10480': 'FW_W'}

    def __init__(self, mods, *, queues=None, head_ready=10, posthead=0, green=2., cycle=10., service=2.,
                 cap_flow=1800., merge_budget=5., k7=False, spill=True, ramp=None):
        self.mods, self.ramp = mods, ramp or self.RAMP
        self.buffer = buffer(mods, head_ready=head_ready, posthead=posthead)
        if k7:
            self.buffer._admission_space_veh = self.buffer.total_admission_space
        self.green, self.cycle, self.service, self.cap_flow, self.merge_budget = green, cycle, service, cap_flow, merge_budget
        self.queues = dict({'SC1001_W_to_onE': 10.} if queues is None else queues)
        conn = float(head_ready + posthead)
        stocks = {'movement:' + m: {'inside': q, 'outside': 0.} for m, q in self.queues.items()}
        stocks['ramp:' + self.ramp] = {'inside': conn, 'outside': 0.}
        self.ledger = mods.cao.ModelAreaLedger(stocks, capture_response=True)
        self.state = NS(ramp_queue={self.ramp: conn}, urban_movement_queue=dict(self.queues),
                        lane_ramp_runtime=lane_runtime(mods, {self.ramp: self.buffer}),
                        _control_area_ledger=self.ledger)
        self.cfg = NS(network=NS(signals=('SC1001',), freeway_links=('FW_W', 'FW_E'),
                                 sdmpc_cost_ownership=dict(self.OWNERS)))
        self.spill = mods.spill if spill else NS(**{n: (lambda *a, **k: None) for n in (
            'movement_virtual', 'movement_commit', 'shared_branch', 'sc2001_branches', 'legsplit_request',
            'legsplit_accepted')})
        self.t = 0.
        self.log = []

    def requests(self):
        T_u_h = 1. / 3600.
        return {m: min(max(0.0, self.state.urban_movement_queue.get(m, 0.0)), T_u_h * 1.0 * self.cap_flow)
                for m in self.queues}

    def step(self, *, mode='GREEN'):
        state, b, ramp, L = self.state, self.buffer, self.ramp, self.ledger
        L.begin_response_step('urban', self.t, self.t + 1.)
        green = self.green if mode == 'GREEN' else None
        r = b.advance_local_interval(start_sec=self.t, duration_sec=1., cycle_sec=self.cycle,
                                     receiving_budget_veh=self.merge_budget, service_veh=self.service, mode=mode,
                                     green_sec=green, request_arrivals_veh=0., allow_partial_cycle=True)
        merged = r['accepted_merge_veh']
        state.ramp_queue[ramp] = state.ramp_queue[ramp] - merged
        L.transfer('ramp:' + ramp, None, merged, inside_to_inside=0., outside_to_inside=0., route_key='merge:' + ramp)
        # urban_flow_accounting.urban_substep_accounted: movement -> ramp (S1-OWN site 1), same statement order
        requests = self.requests()
        requested_total = sum(requests.values())
        ramp_space = state.lane_ramp_runtime.receiving_space(state, ramp)
        scale = 1.0 if requested_total <= ramp_space else ramp_space / max(requested_total, 1.0e-9)
        spill_virtual = self.spill.movement_virtual(state, self.cfg, ramp, requests, ramp_space)
        released_total = 0.0
        before_spill = {m: self.entry('movement:' + m) for m in requests}
        actuals = {}
        for movement, requested in requests.items():
            actual = requested * scale
            before = max(0.0, state.urban_movement_queue.get(movement, 0.0))
            actual = min(before, actual)
            state.urban_movement_queue[movement] = max(0.0, before - actual)
            released_total += actual
            self.spill.movement_commit(state, ramp, movement, spill_virtual, actual)
            L.transfer('movement:' + movement, 'ramp:' + ramp, actual, inside_to_inside=1., outside_to_inside=1.,
                       route_key='movement:' + movement)
            actuals[movement] = actual
        state.ramp_queue[ramp] = max(0.0, state.ramp_queue[ramp] + released_total)
        # LaneRampRuntime.finish
        pending = state.ramp_queue[ramp] - b.snapshot()['connector_veh']
        b.admit_current(max(0., pending))
        L.residence(tuple(L.stocks), 1. / 3600.)
        self.log.append(dict(t=self.t, requests=requests, actual=actuals, space=ramp_space, virtual=spill_virtual,
                             spill_before=before_spill, spill_after={m: self.entry('movement:' + m) for m in requests}))
        self.t += 1.

    def entry(self, feeder, ramp=None):
        return (getattr(self.ledger, 'meter_spill', None) or {}).get(ramp or self.ramp, {}).get(feeder)

    def ramp_stock(self):
        return self.state.ramp_queue[self.ramp]

    def queue(self, m='SC1001_W_to_onE'):
        return self.state.urban_movement_queue[m]

    def costs(self):
        point = NS(control_area_response={'residence': self.ledger._response['residence']},
                   control_area={'ttt_veh_h': self.ledger.ttt_veh_h})
        return self.mods.sdmpc.omega_costs(point, self.cfg)


# ======================================================================================================================
class AdmissionSpaceTests(unittest.TestCase):
    """DEFECTS §2.4: S1 admission space = min(total free, h*lanes/spacing - (upstream travelling + head ready))."""

    def test_s1_1_prehead_full_posthead_empty_admits_zero(self):
        mods = modules()
        b = buffer(mods, head_ready=10)                      # pre-head 10/10 full, post-head 0/10 empty
        interval(b)
        self.assertEqual(b.snapshot()['connector_veh'], 10.)
        self.assertEqual(b.current_admission_space(), 0.)
        self.assertEqual(b.total_admission_space(), 10.)      # the K7 rule would have lent post-head storage
        b2 = buffer(mods, head_ready=10)
        receipt = interval(b2, request=4.)
        self.assertEqual((receipt['admitted_arrivals_veh'], receipt['end']['outside_component_backlog_veh']), (0., 4.))
        with self.assertRaises(ValueError):
            b.admit_current(1e-3)

    def test_s1_2_admits_only_what_head_service_frees(self):
        mods = modules()
        b = buffer(mods, head_ready=10)
        interval(b, service=3., mode='GREEN')                 # head ready 7, post-head 3
        snap = b.snapshot()
        self.assertEqual((snap['head_ready_veh'], snap['downstream_travelling_veh']), (7., 3.))
        self.assertEqual(b.current_admission_space(), 3.)
        self.assertEqual(b.total_admission_space(), 10.)
        with self.assertRaises(ValueError):
            b.admit_current(3. + 1e-6)
        b.admit_current(3.)
        self.assertEqual(b.current_admission_space(), 0.)
        b2 = buffer(mods, head_ready=10)
        receipt = interval(b2, service=3., mode='GREEN', request=5.)
        self.assertEqual((receipt['admitted_arrivals_veh'], receipt['end']['outside_component_backlog_veh']), (3., 2.))

    def test_s1_3_head_zero_unchanged(self):
        """h = 0 keeps the point-queue convention (identical to the K8-2 rule); with h > 0 the two rules agree
        exactly when the post-head compartment is full, and S1 admits less otherwise."""
        cases = [dict(head=0., head_ready=4, posthead=0, merge=None), dict(head=0., head_ready=0, posthead=7, merge=None),
                 dict(head=0., head_ready=12, posthead=0, merge=None),
                 dict(head=60., head_ready=3, posthead=10, merge=0.), dict(head=60., head_ready=2, posthead=5, merge=None)]
        for backend in (None, rev):
            mods = modules(backend)
            old = load(PRB, backend or fwd, k82=True)
            for case in cases:
                head = case['head']
                post = 119. if case['merge'] == 0. else head + 1.
                rows = ([[head, 0., 1]] * case['head_ready'] + [[post, 0., 1]] * case['posthead'])
                for request in (0., 2.5, 30.):
                    out = []
                    for mod in (mods.prb, old):
                        b = mod.PhysicalRampBoundary(connector_id='k8', length_m=120., head_position_m=head, lanes=1,
                                                     spacing_m=6., travel_speed_kmh=36., time_sec=0.,
                                                     initial_cohorts=rows)
                        receipt = interval(b, request=request, accepted=case['merge'])
                        space = 'backlog' if p(b.backlog_veh) else repr(b.current_admission_space())
                        out.append((repr(receipt['admitted_arrivals_veh']), space, repr(b.snapshot())))
                    with self.subTest(case=case, request=request, backend=backend):
                        if case is cases[-1]:              # post-head drained: pre-head room 8 < whole room 18
                            expect = {0.: (('0.0', '8.0'), ('0.0', '18.0')), 2.5: (('2.5', '5.5'), ('2.5', '15.5')),
                                      30.: (('8.0', 'backlog'), ('18.0', 'backlog'))}[request]
                            self.assertEqual((out[0][:2], out[1][:2]), expect)
                        else:
                            self.assertEqual(out[0], out[1])

    def test_s1_4_initial_excess_preserved(self):
        mods = modules()
        b = buffer(mods, head_ready=14)                      # observed pre-head excess 14 > 10 (whole 14 <= 20)
        self.assertEqual(b.snapshot()['connector_veh'], 14.)
        interval(b)
        self.assertEqual(b.snapshot()['connector_veh'], 14.)  # never deleted
        self.assertEqual(b.current_admission_space(), 0.)
        interval(b, service=3., mode='GREEN')                 # head ready 11: still above the pre-head capacity
        self.assertEqual(b.current_admission_space(), 0.)
        interval(b, service=2., mode='GREEN')                 # head ready 9: one free pre-head place
        self.assertEqual(b.snapshot()['head_ready_veh'], 9.)
        self.assertEqual(b.current_admission_space(), 1.)
        self.assertEqual(b.snapshot()['conservation_residual_veh'], 0.)

    def test_s1_5_lane_min(self):
        """A full lane cannot lend storage to the declared arrival mixture: min over lanes of room / share."""
        mods = modules()
        rows = [[60., 0., 1]] * 10                                       # lane 1 pre-head full, lane 2 empty
        def make(shares):
            return mods.prb.LaneResolvedRampBoundary(lane_arrival_shares=shares, connector_id='k8', length_m=120.,
                head_position_m=60., lanes=2, spacing_m=6., travel_speed_kmh=36., time_sec=0., initial_cohorts=rows)
        self.assertEqual(make((0.5, 0.5)).current_admission_space(), 0.)
        self.assertEqual(make((0.0, 1.0)).current_admission_space(), 10.)
        self.assertEqual(make((0.5, 0.5)).total_admission_space(), 20.)   # K7: lane 1 room 10 / 0.5
        lane_one = buffer(mods, head_ready=10, lanes=1)
        self.assertEqual(lane_one.current_admission_space(), 0.)

    def test_s1_6_rejected_urban_traffic_conserved(self):
        """Rejected urban traffic stays with its upstream owner (mass conserved); the spill E <= rejected."""
        toy = Toy(modules(), queues={'SC1001_W_to_onE': 12.})
        start = toy.queue() + toy.ramp_stock()
        merged = 0.
        rejected = 0.
        for _ in range(30):
            before_merge = toy.buffer.cumulative_merge_veh
            toy.step()
            merged = toy.buffer.cumulative_merge_veh
            row = toy.log[-1]
            req = row['requests']['SC1001_W_to_onE']
            rejected += req - row['actual']['SC1001_W_to_onE']
            self.assertAlmostEqual(toy.queue() + toy.ramp_stock() + merged, start, places=12)
            self.assertAlmostEqual(toy.ledger.stocks['movement:SC1001_W_to_onE']['inside'], toy.queue(), places=12)
            e = toy.entry('movement:SC1001_W_to_onE')
            if e is not None:
                self.assertLessEqual(e, rejected + 1e-12)              # E <= rejected (amendment 1 §B.6)
                self.assertLessEqual(e, toy.queue() + 1e-12)
            self.assertGreaterEqual(merged, before_merge)
        self.assertGreater(rejected, 1.)                                # the pre-head limit did bind
        self.assertIsNotNone(toy.entry('movement:SC1001_W_to_onE'))

    def test_s1_7_forward_reverse_dual_agree(self):
        """d(admission space, admitted)/d(head service, request) in the pre-head-binding regime, both AD backends."""
        results = {}
        for name, backend in (('fwd', fwd), ('rev', rev)):
            mods = modules(backend)
            trace = (fwd.Trace([.1, .1], track_stencils=False) if backend is fwd else rev.Trace([.1, .1]))
            s = backend.Dual(3.0, {0: 1.0}, trace)
            q = backend.Dual(5.0, {1: 1.0}, trace)
            b = buffer(mods, head_ready=10)
            receipt = interval(b, service=s, mode='GREEN', request=q)
            b2 = buffer(mods, head_ready=10)
            interval(b2, service=s, mode='GREEN')
            space = b2.current_admission_space()
            outs = [space, receipt['admitted_arrivals_veh'], receipt['end']['outside_component_backlog_veh']]
            if backend is fwd:
                results[name] = [p(x) for x in outs], [[d(x).get(k, 0.) for k in (0, 1)] for x in outs]
            else:
                jac = trace.jacobian(outs, workers=1)
                results[name] = [p(x) for x in outs], jac.tolist()
        self.assertEqual(results['fwd'][0], [3.0, 3.0, 2.0])
        self.assertEqual(results['fwd'][0], results['rev'][0])
        for a, b in zip(results['fwd'][1], results['rev'][1]):
            for x, y in zip(a, b):
                self.assertLessEqual(abs(x - y), 1e-12)
        self.assertEqual(results['fwd'][1][0], [1.0, 0.0])            # head service frees pre-head room 1:1
        self.assertEqual(results['fwd'][1][1], [1.0, 0.0])            # admitted = pre-head room
        self.assertEqual(results['fwd'][1][2], [-1.0, 1.0])           # backlog = request - admitted


# ======================================================================================================================
class MeterOwnerTests(unittest.TestCase):
    """S1_OWNER.md §7 T-OWN-1 ... T-OWN-14."""

    # T-OWN-1
    def test_spill_absent_without_prehead_binding(self):
        on = Toy(modules(), head_ready=2, queues={'SC1001_W_to_onE': 3.})
        off = Toy(modules(), head_ready=2, queues={'SC1001_W_to_onE': 3.}, spill=False)
        for _ in range(10):
            on.step(); off.step()
        self.assertFalse(hasattr(on.ledger, 'meter_spill'))
        self.assertTrue(all('meter_spill_veh' not in row for row in on.ledger._response['residence']))
        self.assertEqual(repr(on.costs()), repr(off.costs()))
        self.assertNotIn('meter_spill_veh_h', on.costs()[1])

    # T-OWN-2
    def test_spill_equals_k7_counterfactual(self):
        s1 = Toy(modules(), queues={'SC1001_W_to_onE': 10.})
        k7 = Toy(modules(), queues={'SC1001_W_to_onE': 10.}, k7=True, spill=False)
        created = False
        for _ in range(30):
            s1.step(); k7.step()
            e = s1.entry('movement:SC1001_W_to_onE')
            e = 0. if e is None else e
            created |= e > 0
            self.assertLessEqual(abs(e - (k7.ramp_stock() - s1.ramp_stock())), 1e-12)
            self.assertLessEqual(abs(e - (s1.queue() - k7.queue())), 1e-12)
            if s1.log[-1]['spill_before']['SC1001_W_to_onE'] is not None:       # T-OWN-4 (capped feeder)
                row = s1.log[-1]
                old, a0 = row['spill_before']['SC1001_W_to_onE'], row['virtual']['SC1001_W_to_onE'][1]
                self.assertEqual(e, max(0., old + a0 - row['actual']['SC1001_W_to_onE']))
        self.assertTrue(created)
        self.assertGreater(k7.ramp_stock() - s1.ramp_stock(), 1.)

    # T-OWN-3
    def test_spill_release_and_keep_entry(self):
        toy = Toy(modules(), queues={'SC1001_W_to_onE': 10.})
        for _ in range(30):
            toy.step()
        e0 = toy.entry('movement:SC1001_W_to_onE')
        self.assertGreater(e0, 1.)
        toy.service = 50.                              # meter OFF: the pre-head compartment drains, no arrivals
        history = [e0]
        for _ in range(40):
            toy.step(mode='OFF')
            row = toy.log[-1]
            new = toy.entry('movement:SC1001_W_to_onE')
            self.assertIsNotNone(new)
            if row['virtual'] is not None and new > 0.:
                old, a0, ready, _ = row['virtual']['SC1001_W_to_onE']
                self.assertEqual(new, old + a0 - row['actual']['SC1001_W_to_onE'])      # exact, unclamped
            history.append(new)
        self.assertTrue(all(b <= a for a, b in zip(history, history[1:])))
        self.assertEqual(history[-1], 0.0)
        self.assertIn('movement:SC1001_W_to_onE', toy.ledger.meter_spill[toy.ramp])

    # T-OWN-4
    def test_spill_capped_by_ready(self):
        """legsplit (proportional request R = c*Y): every update E <= max(0, Y - A), and a W_out drained by the
        other exit makes that cap bind. A capped feeder (movement) never reaches it: E' = max(0, E + A0 - A)."""
        mods = modules()
        toy = Toy(mods, queues={})
        state, spill, ramp, rt = toy.state, mods.spill, toy.ramp, toy.state.lane_ramp_runtime
        link = 'SC1001_W_out'
        updates, binding = 0, 0
        for arrived in (40., 40., 40., 6., 2., 0.5):
            toy.ledger.begin_response_step('urban', toy.t, toy.t + 1.)
            share, rate, conn = 0.5, 0.25, 3.0
            reach = min(arrived, arrived * rate)
            request = reach * share
            space = rt.receiving_space(state, ramp)
            allowed = min(request, min(space, conn))
            old = toy.entry('storage:' + link)
            e_old = 0. if old is None else old
            room = max(0., rt.total_receiving_space_primal(state, ramp) - e_old)    # stage 1 = stage 2 here
            c = reach / arrived
            pre0 = min(max(0., request - c * e_old), conn, room)
            a0 = pre0 * (min(1., room / pre0) if pre0 > 0 else 1.)
            ready = request / c                                                 # Y = R / c = arrived * share
            unclamped = max(0., e_old + a0 - allowed)
            memo = {}
            spill.legsplit_request(state, memo, link, ramp, request, reach, arrived, conn, allowed, space)
            accepted = [(link, None, reach * (1 - share))] + ([(link, ramp, allowed)] if allowed > 0. else [])
            spill.legsplit_accepted(state, memo, accepted)
            state.ramp_queue[ramp] += allowed
            toy.buffer.admit_current(allowed)
            new = toy.entry('storage:' + link)
            if new is not None:
                updates += 1
                self.assertLessEqual(new, max(0., ready - allowed))
                self.assertLessEqual(abs(new - min(unclamped, max(0., ready - allowed))), 1e-12)
                binding += max(0., ready - allowed) < unclamped
            toy.t += 1.
        self.assertGreater(updates, 2)
        self.assertGreater(binding, 0)                  # the ready cap bound once the W_out drained
        capped = Toy(modules(), queues={'SC1001_W_to_onE': 10.})
        for _ in range(40):
            capped.step()
            row = capped.log[-1]
            old = row['spill_before']['SC1001_W_to_onE']
            new = row['spill_after']['SC1001_W_to_onE']
            if old is not None:
                a0, ready = row['virtual']['SC1001_W_to_onE'][1:3]
                actual = row['actual']['SC1001_W_to_onE']
                self.assertEqual(new, max(0., old + a0 - actual))
                self.assertLessEqual(new, max(0., ready - actual))

    # T-OWN-5
    def test_partition_moves_cost_not_omega(self):
        mods = modules()
        dt = 1. / 3600.
        cfg = NS(network=NS(signals=('SC1001',), freeway_links=('FW_W', 'FW_E'),
                            sdmpc_cost_ownership={'ramp:RM_C10490': 'FW_E'}))
        for step, inside, expect in ((0.25, 8., 4.), (0.25, 0., 0.), (dt, 8., 4.)):
            row = {'stage': 'urban', 'dt_h': step, 'inside_veh': {'movement:F': inside, 'ramp:RM_C10490': 2.},
                   'model_stock_veh': {'movement:F': 10., 'ramp:RM_C10490': 2.},
                   'meter_spill_veh': {'RM_C10490': {'movement:F': 5.}}}
            ttt = step * (inside + 2.)
            point = NS(control_area_response={'residence': [row]}, control_area={'ttt_veh_h': ttt})
            local, part = mods.sdmpc.omega_costs(point, cfg)
            self.assertEqual(part['costs']['FW_E'], math.fsum([step * 2., step * expect]))   # o(r) += 4 dt
            self.assertEqual(part['costs'][PASSIVE], step * inside - step * expect)          # o(f) = (8 - 4) dt
            self.assertEqual(part['meter_spill_veh_h'], {'RM_C10490': {'movement:F': step * expect}})
            if step == 0.25:                                   # binary-exact numbers: the ledger TTT repr exactly
                self.assertEqual(repr(part['total_veh_h']), repr(ttt))
            else:                                              # float dt: within the partition's own check
                self.assertLessEqual(abs(part['total_veh_h'] - ttt), 1e-10 * ttt)
        row = {'stage': 'urban', 'dt_h': dt, 'inside_veh': {'movement:F': 8.}, 'model_stock_veh': {'movement:F': 10.}}
        point = NS(control_area_response={'residence': [row]}, control_area={'ttt_veh_h': dt * 8.})
        self.assertNotIn('meter_spill_veh_h', mods.sdmpc.omega_costs(point, cfg)[1])

    # T-OWN-6
    def test_ramp_owner_mapping(self):
        path = os.environ.get('K8_CAPTURED_TEMPLATE')
        self.assertTrue(path and Path(path).is_file(), 'K8_CAPTURED_TEMPLATE must name a captured deployed template')
        data = Path(path).read_bytes()
        print(f'K8_CAPTURED_TEMPLATE {path} sha256 {hashlib.sha256(data).hexdigest()}')
        request = pickle.loads(data)
        follower = request['owned'][0]
        net = follower.cfg.network
        table = net.sdmpc_cost_ownership
        order = list(request['costs_order'])
        ramps = sorted(net.ramps)
        self.assertEqual(len(ramps), 8)
        owners = {r: table['ramp:' + r] for r in ramps}
        self.assertEqual(owners, dict(net.ramp_to_freeway))
        self.assertEqual(sorted(r for r, o in owners.items() if o == 'FW_W'),
                         ['RM_C10480', 'RM_C10482', 'RM_C10644', 'RM_C10646'])
        self.assertEqual(sorted(r for r, o in owners.items() if o == 'FW_E'),
                         ['RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10681'])
        self.assertEqual((order.index('FW_W'), order.index('FW_E'), order.index(PASSIVE)), (17, 18, 19))
        feeders = {}
        for m, spec in net.urban_movements.items():
            if str(spec.get('ramp', '')):
                feeders.setdefault(str(spec['ramp']), []).append('movement:' + m)
        sc = getattr(net, 'sc2001_corridor', None)
        if sc:
            for branch in sc['branches'].values():
                if branch['target_kind'] == 'ramp':
                    feeders.setdefault(branch['target'], []).append('storage:' + sc['storage'])
        shared = getattr(net, 'shared_approach', None)
        if shared:
            for branch in shared['branches'].values():
                if branch['target_kind'] == 'ramp':
                    feeders.setdefault(branch['target'], []).append('storage:' + shared['storage'])
        for link, spec in (getattr(net, 'boundary_out_ramp_split', None) or {}).items():
            for ramp in (spec.get('ramps') or {}):
                feeders.setdefault(str(ramp), []).append('storage:' + str(link))
        pairs = {(r, f) for r, fs in feeders.items() for f in fs}
        self.assertTrue(pairs)
        self.assertEqual({table.get(f, PASSIVE) for _, f in pairs}, {PASSIVE})
        self.assertLessEqual({r for r, _ in pairs}, set(ramps))
        # a rollout cannot create an entry outside these site pairs (I-7): every site keys E by its own feeder
        self.assertEqual({('RM_C10482', 'movement:SC1001_W_to_onW'), ('RM_C10490', 'movement:SC1001_W_to_onE')}
                         <= pairs, True)

    # T-OWN-7
    def test_multi_ramp_feeder_cap(self):
        mods = modules()
        row = {'dt_h': 0.25, 'inside_veh': {'storage:SC2001_S_out': 3.},
               'model_stock_veh': {'storage:SC2001_S_out': 10.},
               'meter_spill_veh': {'RM_C10484': {'storage:SC2001_S_out': 10.},
                                   'RM_C10480': {'storage:SC2001_S_out': 6.}}}
        moved = mods.spill.spill_inside(row)
        shares = moved['storage:SC2001_S_out']
        self.assertLessEqual(abs(sum(shares.values()) - 3.), 1e-12)
        cfg = NS(network=NS(signals=(), freeway_links=('FW_W', 'FW_E'),
                            sdmpc_cost_ownership={'ramp:RM_C10484': 'FW_E', 'ramp:RM_C10480': 'FW_W'}))
        point = NS(control_area_response={'residence': [row]}, control_area={'ttt_veh_h': 0.75})
        costs = mods.sdmpc.omega_costs(point, cfg)[1]['costs']
        self.assertGreaterEqual(costs[PASSIVE], 0.)
        self.assertEqual(math.fsum(costs.values()), 0.75)
        self.assertEqual((costs['FW_E'], costs['FW_W']), (0.25 * 1.875, 0.25 * 1.125))

    # T-OWN-8
    def test_creation_gate_primal(self):
        for case in ('a', 'b', 'c'):
            mods = modules(rev)
            trace = rev.Trace([.1])
            head_ready, posthead, queue = {'a': (10, 10, 10.), 'b': (10, 0, 10.), 'c': (2, 0, 3.)}[case]
            toy = Toy(mods, head_ready=head_ready, posthead=posthead, queues={'SC1001_W_to_onE': queue})
            toy.state.urban_movement_queue['SC1001_W_to_onE'] = rev.Dual(queue, {0: 1.0}, trace)
            state, ramp = toy.state, toy.ramp
            requests = toy.requests()
            space = state.lane_ramp_runtime.receiving_space(state, ramp)
            before = record(trace)
            virtual = mods.spill.movement_virtual(state, toy.cfg, ramp, requests, space)
            actual = min(requests['SC1001_W_to_onE'], space) if p(requests['SC1001_W_to_onE']) > p(space) \
                else requests['SC1001_W_to_onE']
            mid = record(trace)
            mods.spill.movement_commit(state, ramp, 'SC1001_W_to_onE', virtual, actual)
            after = record(trace)
            e = toy.entry('movement:SC1001_W_to_onE')
            with self.subTest(case=case):
                if case in ('a', 'c'):
                    self.assertIsNone(virtual if case == 'c' else None)
                    self.assertIsNone(e)
                    self.assertFalse(hasattr(toy.ledger, 'meter_spill'))
                    self.assertEqual(before, mid)
                    self.assertEqual(mid, after)                      # no Dual operation, no branch record
                else:
                    k7_room = state.lane_ramp_runtime.total_receiving_space_primal(state, ramp)
                    a0 = min(p(requests['SC1001_W_to_onE']), k7_room)
                    self.assertGreater(p(e), 1e-9)
                    self.assertEqual(p(e), a0 - p(actual))
        # (a) really is a K7-full case and (b) a pre-head-only case
        mods = modules()
        full = Toy(mods, head_ready=10, posthead=10)
        self.assertEqual(full.state.lane_ramp_runtime.receiving_space(full.state, full.ramp), 0.)
        self.assertEqual(full.state.lane_ramp_runtime.total_receiving_space(full.state, full.ramp), 0.)
        pre = Toy(mods, head_ready=10, posthead=0)
        self.assertEqual(pre.state.lane_ramp_runtime.receiving_space(pre.state, pre.ramp), 0.)
        self.assertEqual(pre.state.lane_ramp_runtime.total_receiving_space(pre.state, pre.ramp), 10.)

    # T-OWN-9
    def test_physical_state_unchanged(self):
        def physical(toy):
            ledger = {k: v for k, v in toy.ledger.__dict__.items() if k not in ('meter_spill', '_response')}
            residence = [{k: v for k, v in row.items() if k != 'meter_spill_veh'}
                         for row in toy.ledger._response['residence']]
            others = {k: v for k, v in toy.ledger._response.items() if k != 'residence'}
            return repr((toy.state.ramp_queue, toy.state.urban_movement_queue, toy.buffer.snapshot(),
                         toy.buffer._upstream, toy.buffer._downstream, ledger, residence, others))
        on = Toy(modules(), queues={'SC1001_W_to_onE': 15.})
        off = Toy(modules(), queues={'SC1001_W_to_onE': 15.}, spill=False)
        for block in range(3):                    # M2ALL-like: green 2 s per 10 s cycle, three 15 s blocks
            for _ in range(15):
                on.step(); off.step()
            self.assertEqual(physical(on), physical(off))
        self.assertTrue(on.ledger.meter_spill)
        self.assertEqual(repr(on.ledger.ttt_veh_h), repr(off.ledger.ttt_veh_h))
        c_on, c_off = on.costs()[1], off.costs()[1]
        self.assertEqual(repr(c_on['total_veh_h']), repr(c_off['total_veh_h']))
        self.assertNotEqual(c_on['costs']['FW_E'], c_off['costs']['FW_E'])

    # T-OWN-10
    def test_sc2001_shared_factor_not_spill(self):
        mods = modules()
        rt = lane_runtime(mods, {'RM_C10484': buffer(mods), 'RM_C10480': buffer(mods)})
        ledger = mods.cao.ModelAreaLedger({'storage:SC2001_S_out': {'inside': 30., 'outside': 0.}})
        state = NS(ramp_queue={'RM_C10484': 0., 'RM_C10480': 0.}, lane_ramp_runtime=rt, _control_area_ledger=ledger)
        spec = {'storage': 'SC2001_S_out', 'lanes': 2,
                'branches': {'R_D_E': {'target_kind': 'ramp', 'target': 'RM_C10484', 'lanes': 1},
                             'R_D_W': {'target_kind': 'ramp', 'target': 'RM_C10480', 'lanes': 1},
                             'outside_125': {'target_kind': 'external', 'lanes': 1}}}
        sat, dt_h = 1400., 1. / 3600.
        ready = {'R_D_E': 5., 'R_D_W': 5., 'outside_125': 5.}
        pre = {k: min(ready[k], rt.receiving_space(state, spec['branches'][k]['target'])
                      if spec['branches'][k]['target_kind'] == 'ramp' else 1e9, sat * dt_h) for k in ready}
        factor = min(1., sat * 2 * dt_h / sum(pre.values()))
        self.assertLess(factor, 1.)
        accepted = {k: v * factor for k, v in pre.items()}
        mods.spill.sc2001_branches(state, spec, ready, pre, accepted, sat, dt_h)
        self.assertFalse(hasattr(ledger, 'meter_spill'))

    # T-OWN-11
    def test_lane_resolved_k7_space(self):
        for backend in (None, rev):
            mods = modules(backend)
            old = load(PRB, backend or fwd, k82=True)
            for rows, shares in (([[60., 0., 1]] * 10, (0.5, 0.5)), ([[60., 0., 1]] * 4 + [[61., 0., 2]] * 7, (0.3, 0.7)),
                                 ([], (0., 1.)), ([[60., 0., 2]] * 9, (1., 0.))):
                made = [mod.LaneResolvedRampBoundary(lane_arrival_shares=shares, connector_id='k8', length_m=120.,
                        head_position_m=60., lanes=2, spacing_m=6., travel_speed_kmh=36., time_sec=0.,
                        initial_cohorts=rows) for mod in (mods.prb, old)]
                with self.subTest(rows=len(rows), shares=shares, backend=backend):
                    self.assertEqual(repr(made[0].total_admission_space()), repr(made[1].current_admission_space()))
                    self.assertEqual(repr(made[0].total_admission_space_primal()),
                                     repr(made[1].current_admission_space()))
                    single = [mod.PhysicalRampBoundary(connector_id='k8', length_m=120., head_position_m=60., lanes=1,
                              spacing_m=6., travel_speed_kmh=36., time_sec=0.,
                              initial_cohorts=[r[:2] + [1] for r in rows if r[2] == 1]) for mod in (mods.prb, old)]
                    self.assertEqual(repr(single[0].total_admission_space()), repr(single[1].current_admission_space()))

    # T-OWN-12
    def test_spill_reduces_k7_room(self):
        mods = modules()
        toy = Toy(mods, queues={'SC1001_W_to_onE': 10.})
        for _ in range(15):                           # ends on a red second: the pre-head compartment is full
            toy.step()
        state, ramp, rt = toy.state, toy.ramp, toy.state.lane_ramp_runtime
        e_mov = toy.entry('movement:SC1001_W_to_onE')
        self.assertGreater(e_mov, 0.)
        spec = {'storage': 'SC2001_S_out', 'lanes': 2,
                'branches': {'R_D_E': {'target_kind': 'ramp', 'target': ramp, 'lanes': 1}}}
        sat, dt_h = 1400., 1. / 3600.
        ready = {'R_D_E': 2.}
        space = rt.receiving_space(state, ramp)
        pre = {'R_D_E': min(ready['R_D_E'], space, sat * dt_h)}
        accepted = dict(pre)
        self.assertLess(accepted['R_D_E'], min(ready['R_D_E'], sat * dt_h))
        f7 = max(0., rt.total_receiving_space(state, ramp) - e_mov)          # space_K7 - pending - sum E
        self.assertEqual(mods.spill._room(state, ramp, e_mov), f7)
        mods.spill.sc2001_branches(state, spec, ready, pre, accepted, sat, dt_h)
        a0 = min(min(ready['R_D_E'], sat * dt_h), f7)
        e_sc = toy.entry('storage:SC2001_S_out')
        self.assertIsNotNone(e_sc)
        self.assertEqual(e_sc, min(max(0., a0 - accepted['R_D_E']), max(0., ready['R_D_E'] - accepted['R_D_E'])))
        self.assertLess(f7, rt.total_receiving_space(state, ramp))

    # T-OWN-13
    def test_dual_forward_reverse_and_fd(self):
        def run(backend, g):
            mods = modules(backend)
            toy = Toy(mods, queues={'SC1001_W_to_onE': 15.}, service=g * 1.0)
            for _ in range(45):                           # three 15 s blocks
                toy.step()
            local, part = toy.costs()
            return toy, part
        g0, h = 2.3, 1e-4
        scalar, part_s = run(None, g0)
        out = {}
        for name, backend in (('fwd', fwd), ('rev', rev)):
            trace = fwd.Trace([.1], track_stencils=False) if backend is fwd else rev.Trace([.1])
            toy, part = run(backend, backend.Dual(g0, {0: 1.0}, trace))
            spill = toy.ledger.meter_spill
            self.assertEqual({r: set(v) for r, v in spill.items()},
                             {r: set(v) for r, v in scalar.ledger.meter_spill.items()})
            self.assertEqual({r: {k: p(x) for k, x in v.items()} for r, v in spill.items()},
                             {r: {k: p(x) for k, x in v.items()} for r, v in scalar.ledger.meter_spill.items()})
            self.assertEqual(p(toy.ledger.ttt_veh_h), scalar.ledger.ttt_veh_h)          # state_error = 0
            costs = [part['costs'][o] for o in ('FW_E', PASSIVE)]
            self.assertEqual([p(c) for c in costs], [part_s['costs']['FW_E'], part_s['costs'][PASSIVE]])
            if backend is fwd:
                out[name] = [d(c).get(0, 0.) for c in costs]
            else:
                out[name] = [float(x) for x in trace.jacobian(costs, workers=1)[:, 0]]
        fd = [(run(None, g0 + h)[1]['costs'][o] - run(None, g0 - h)[1]['costs'][o]) / (2 * h) for o in ('FW_E', PASSIVE)]
        for a, b in zip(out['fwd'], out['rev']):
            self.assertLessEqual(abs(a - b), 1e-12)
        for a, b in zip(out['fwd'], fd):
            self.assertLessEqual(abs(a - b), 1e-6)
        self.assertNotEqual(out['fwd'][0], 0.)

    # T-OWN-14
    def test_zero_spill_keeps_derivative(self):
        trace = fwd.Trace([.1], track_stencils=False)
        mods = modules(fwd)
        toy = Toy(mods, queues={'SC1001_W_to_onE': 10.}, service=fwd.Dual(2.3, {0: 1.0}, trace))
        for _ in range(20):
            toy.step()
        self.assertTrue(d(toy.entry('movement:SC1001_W_to_onE')))
        toy.service = 50.
        zero_seen = False
        for _ in range(40):
            toy.step(mode='OFF')
            e = toy.entry('movement:SC1001_W_to_onE')
            self.assertIsNotNone(e)
            zero_seen |= p(e) == 0.
        self.assertTrue(zero_seen)
        self.assertIn('movement:SC1001_W_to_onE', toy.ledger.meter_spill[toy.ramp])
        toy.service = fwd.Dual(2.3, {0: 1.0}, trace)                   # meter binds again: the same entry grows
        toy.state.urban_movement_queue['SC1001_W_to_onE'] = toy.state.urban_movement_queue['SC1001_W_to_onE'] + 30.
        toy.ledger.stocks['movement:SC1001_W_to_onE']['inside'] += 30.
        grew = None
        for _ in range(80):
            toy.step()
            row = toy.log[-1]
            e = toy.entry('movement:SC1001_W_to_onE')
            if p(e) > 0. and row['spill_before']['SC1001_W_to_onE'] is not None:
                old, a0, ready, _ = row['virtual']['SC1001_W_to_onE']
                expect = old + a0 - row['actual']['SC1001_W_to_onE']
                self.assertEqual(p(e), p(expect))
                self.assertEqual(d(e), d(expect))                       # derivative continues through the entry
                grew = e
        self.assertIsNotNone(grew)
        self.assertEqual(list(toy.ledger.meter_spill[toy.ramp]), ['movement:SC1001_W_to_onE'])


if __name__ == '__main__':
    unittest.main()
