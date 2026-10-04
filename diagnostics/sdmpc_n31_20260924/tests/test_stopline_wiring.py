"""K8-6 SA wiring tests: RS/LOR/UFA hooks, make_config arm flags, key-absent structure and bit identity.

No adapter run, capture, rollout, harness job or VISSIM. The UFA rows run the real urban_substep_accounted and
LaneOfframpRuntime.drain on the vendor default ExperimentConfig with the SC1001 W pieces grafted in (one-second
urban steps, two real DelayedPorts, a ModelAreaLedger). The key-absent rows compare that run with the base
commit's UFA and LOR (the parent of the first K8-6 commit, read with git show: K8-0e on the K8 branch, whose runtime
is ec063ff = K8-4; fef1e76 = K8-1 before the rebase)
and must be bit-identical; the key-present rows check the SA invariants inside the real loop and that the toy
drive (stopline_toy.drive) is the real hook order.
"""
from __future__ import annotations

import ast
import json
import math
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
N31D = HERE.parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE, N31D):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stopline_toy as T  # noqa: E402
from src.models.state import ExperimentConfig, SimulationConfig, TrafficState, ControlAction  # noqa: E402
from src.models.demand import DemandStep  # noqa: E402
from src.models import urban_queue_model as uqm  # noqa: E402
from evaluation.controllers import stopline_approach as SA  # noqa: E402
from evaluation.controllers import urban_flow_accounting as ufa  # noqa: E402
from evaluation.controllers import area_runtime  # noqa: E402
from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime  # noqa: E402
from evaluation.controllers.control_area_objective import ModelAreaLedger, emit_transfer  # noqa: E402
from evaluation.controllers.lane_urban_runtime import _debit_stock  # noqa: E402



def base_revision():
    """The commit K8-6 sits on (key absent must equal it): K8_SA_BASE_REV, else the parent of the oldest
    'WIP K8-6:'/'K8-6:' commit on HEAD (ec063ff = K8-4 runtime after the rebase onto the K8 head; on the K8 branch the
    K8-0e harness commit, diagnostics only, so its UFA/LOR/RS are those of ec063ff)."""
    rev = __import__('os').environ.get('K8_SA_BASE_REV')
    if rev:
        return rev
    done = subprocess.run(['git', '-C', str(ROOT), 'log', '--format=%H %s', 'HEAD'], capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    own = [line.split(' ', 1)[0] for line in done.stdout.splitlines()
           if line.split(' ', 1)[-1].startswith(('WIP K8-6:', 'K8-6:'))]
    return (own[-1] + '^') if own else 'HEAD'


BASE_REV = base_revision()
UFA_REL = 'evaluation/controllers/urban_flow_accounting.py'
LOR_REL = 'evaluation/controllers/lane_offramp_runtime.py'
RS_REL = 'evaluation/controllers/runtime_setup.py'
E, S, N, IN = T.E, T.S, T.N, T.IN
T0 = 600
# Observed connector vehicles [position_m, speed_kmh, lane] (canonical_harness.DelayedPort cohorts).
COHORTS = {'10491': [[231.4, 30.0, 1]] * 4 + [[150.0, 30.0, 1]] * 3,
           '10481': [[454.3, 30.0, 1]] * 6 + [[300.0, 30.0, 2]] * 4}
LANDING = {'10491': 0.12, '10481': 0.2}       # veh per second landed on each port (LOR.land stand-in)
GATE_VEH_H = 420.0                             # city demand on the in_SC1001_W gate
READY = [(1, E, 6.0, 'init:city'), (1, S, 2.0, 'init:port'), (2, E, 5.0, 'init:unknown'), (3, N, 3.0, 'init:city')]
MOVING = [(1, E, 1.5, 7, 'init:port'), (2, E, 1.0, 12, 'init:city'), (3, N, 0.8, 9, 'init:port')]
DEST = {E: 'E', S: 'S', N: 'N'}


# ---------------------------------------------------------------- the graft

def git_show(rel, rev=BASE_REV):
    done = subprocess.run(['git', '-C', str(ROOT), 'show', f'{rev}:{rel}'], capture_output=True)
    if done.returncode:
        raise unittest.SkipTest('git show %s:%s unavailable' % (rev, rel))
    return done.stdout


def base_module(rel, name):
    """The base commit's module source, executed as a separate module (same imports, same globals)."""
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / rel)
    exec(compile(git_show(rel), str(ROOT / rel) + '@' + BASE_REV, 'exec'), module.__dict__)
    return module


def graft(*, sa=False, arm='observed_full', evidence=None, lor_class=LaneOfframpRuntime, t0=T0,
          seed=True, gate=True, idle=False):
    """Vendor default network + SC1001 W members, the eight SC1001 off-ramp movements, the two ports and stores.

    idle=True empties the default network's own queues so that every perimeter count belongs to SC1001.
    """
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    cfg = ExperimentConfig(simulation=SimulationConfig(T_u=1.0, T_f=1.0))
    net = cfg.network
    sink = net.boundary_out_links[0]               # the three receivers drain as sinks (mass leaves via sink:)
    toy = {name: {k: v for k, v in row.items() if v is not None}       # UFA reads str(spec['ramp'])
           for name, row in T.movements().items()}
    for name in (E, S, N):
        net.urban_movements[name] = dict(toy[name], destination=sink, beta=T.OFF_BETA[DEST[name]])
    for name, row in toy.items():
        if name.startswith('SC1001_off'):
            net.urban_movements[name] = dict(row, destination=sink)
    net.off_ramp_to_movement['OR_D_W'] = [m for m in toy if m.startswith('SC1001_offW')]
    net.off_ramp_to_movement['OR_D_E'] = [m for m in toy if m.startswith('SC1001_offE')]
    for key in (IN, 'SC1001_to_SC1002', 'SC1001_to_SC1003', 'SC1001_to_SC2002', 'SC1001_W_out',
                'OR_D_W_storage', 'OR_D_E_storage'):
        net.urban_link_storage_veh[key] = T.CAPS[key]
    if gate:
        net.boundary_in_links = list(net.boundary_in_links) + [IN]
    control = ControlAction.uncontrolled(cfg)
    control.green_times.update(T.GREENS)
    control.offsets['SC1001'] = 0.0
    state = TrafficState.initial(cfg)
    uqm.ensure_urban_state(state, cfg)
    for member in (E, S, N):              # initial() seeds every gate queue; the W index starts from seed_stocks
        state.urban_movement_queue[member] = 0.0
    if idle:
        for movement in state.urban_movement_queue:
            state.urban_movement_queue[movement] = 0.0
    state.time_sec = float(t0)
    rows = T.offramp_rows()
    ports = {off: DelayedPort(row['storage_capacity_veh'], row['length_m'], 60.0, COHORTS[off], t0,
                              interval_service=True) for off, row in rows.items()}
    state.lane_offramp_runtime = lor_class(ports, rows, None, {'10491': True, '10481': True, '129': True,
                                                               '127': True})
    for off, row in rows.items():
        state.urban_link_storage[row['storage']] = row['storage_capacity_veh'] - ports[off].stock
    routes = {}
    for movement, spec in uqm.movement_specs(cfg).items():
        routes['movement:' + movement] = {'target_inside': bool(spec.get('receiving_link') in state.urban_link_storage)}
        routes['arrival:' + movement] = {'target_inside': True}
    for origin in net.boundary_in_links:
        routes['input:gate:' + origin] = {'target_inside': True}
    for ramp in net.ramps:
        routes['input:ramp:' + ramp] = {'target_inside': True}
    routes.update(T.routes_table())
    net.control_area_routes = routes
    if sa:
        spec = SA.build_view(cfg, T.section(arm), evidence or T.evidence(), 'f' * 64)
        net.stopline_approach = spec
        SA._bind_ports(state, cfg, spec)
        for off in SA.PORTS:
            rows[off]['approach'] = SA.APPROACH
        state.stopline_approach_state = SA._new_state(spec)
        state.stopline_approach_state['speed_kmh'] = 30.0
    if seed:
        seed_stocks(state, cfg, t0)
    state._control_area_ledger = ModelAreaLedger(
        {k: {'inside': v, 'outside': 0.0} for k, v in area_runtime.model_inventory(state, cfg).items()})
    return cfg, state, control


def seed_stocks(state, cfg, t0):
    """Ready queues and moving in_SC1001_W reservations; with SA also their lane packets and tags."""
    st = getattr(state, 'stopline_approach_state', None)
    for lane, member, amount, source in READY:
        state.urban_movement_queue[member] += amount
        if st is not None:
            SA._insert(st, lane, t0, source, member, amount)
            st['stock'][lane] += amount
    for lane, member, amount, ahead, source in MOVING:
        due = t0 + ahead
        uqm._schedule(state.urban_arrival_buffer, IN, due, amount)
        uqm._schedule(state.urban_storage_release_buffer, IN, due, amount)
        state.urban_link_storage[IN] -= amount
        if st is not None:
            SA._insert(st, lane, due, source, member, amount)
            st['stock'][lane] += amount
            tags = st['tags'].setdefault(due, {})
            tags[(lane, member, source)] = tags.get((lane, member, source), 0.0) + amount


def land(state, cfg, t):
    """LOR.land stand-in for the two ports (connector accept, store debit, landing transfer)."""
    lor = state.lane_offramp_runtime
    for off, amount in LANDING.items():
        key = lor.descriptions[off]['storage']
        lor.ports[off].accept(t + 1, amount)
        state.urban_link_storage[key] = _debit_stock(state.urban_link_storage[key], amount)
        emit_transfer(state, cfg, None, 'storage:' + key, amount, source_inside=True, target_inside=True)


def run(cfg, state, control, module, steps, *, t0=T0, gate=True, each=None):
    demand = DemandStep({}, {IN: GATE_VEH_H} if gate else {}, {})
    ledger = state._control_area_ledger
    out = []
    for t in range(t0, t0 + steps):
        ledger.begin_response_step('urban', t, t + 1)
        cost, diag = module.urban_substep_accounted(state, control, demand, cfg, urban_step_index=t,
                                                    ramp_release_veh_h={})
        ledger.begin_response_step('landing', t, t + 1)
        land(state, cfg, t)
        ledger.assert_stocks(area_runtime.model_inventory(state, cfg))
        out.append((cost, diag))
        if each is not None:
            each(t, cost, diag)
    return out


def snapshot(state):
    skip = {'_control_area_ledger', 'lane_offramp_runtime'}
    out = {k: repr(v) for k, v in sorted(vars(state).items()) if k not in skip}
    lor = state.lane_offramp_runtime
    out['lor'] = repr(({off: sorted(vars(p).items()) for off, p in lor.ports.items()}, lor.descriptions,
                       lor.last_drain))
    led = state._control_area_ledger
    out['ledger'] = repr((led.stocks, sorted(led.flow_counts.items()), led.ttt_veh_h, led.ttd_veh, led.entered_veh))
    return out


# ------------------------------------------------- T2 key absent: bit identity

class KeyAbsentBitIdentityTests(unittest.TestCase):
    """G-EB-1 at unit level: no key -> the wired UFA/LOR run equals the base commit's, step by step."""

    @classmethod
    def setUpClass(cls):
        cls.base_ufa = base_module(UFA_REL, 'k8sa_base_urban_flow_accounting')
        cls.base_lor = base_module(LOR_REL, 'k8sa_base_lane_offramp_runtime')

    def test_wired_modules_equal_the_base_without_the_key(self):
        base = graft(lor_class=self.base_lor.LaneOfframpRuntime)
        current = graft()
        self.assertEqual(snapshot(base[1]), snapshot(current[1]))
        steps = 150
        left, right = [], []
        run(*base, self.base_ufa, steps, each=lambda t, c, d: left.append((repr((c, d)), snapshot(base[1]))))
        run(*current, ufa, steps, each=lambda t, c, d: right.append((repr((c, d)), snapshot(current[1]))))
        for t, (a, b) in enumerate(zip(left, right)):
            if a != b:
                diff = sorted(k for k in a[1] if a[1][k] != b[1].get(k))
                self.fail(f'step {T0 + t}: key-absent run differs from {BASE_REV} in {diff or "diagnostics"}')
        self.assertFalse(any(k.startswith('stopline_') for k in right[-1][0]))
        # The scenario is not idle: ports released, W members departed, the gate landed.
        flows = dict(current[1]._control_area_ledger.flow_counts)
        self.assertGreater(flows.get('movement:SC1001_offW_to_E_SC1002', 0.0), 0.0)
        self.assertGreater(flows.get('movement:SC1001_offE_to_N_SC2002', 0.0), 0.0)
        self.assertGreater(flows.get('movement:' + E, 0.0), 0.0)
        self.assertGreater(flows.get('arrival:' + N, 0.0), 0.0)
        self.assertFalse(hasattr(current[0].network, 'stopline_approach'))
        self.assertFalse(hasattr(current[1], 'stopline_approach_state'))
        self.assertNotIn('approach', current[1].lane_offramp_runtime.descriptions['10491'])


class KeyAbsentStructureTests(unittest.TestCase):
    """The hooks sit only behind the key: SA is never imported and every SA name is guarded."""

    def test_modules_do_not_import_sa(self):
        code = ('import sys; sys.path[:0]=[%r, %r]\n'
                'from evaluation.controllers import runtime_setup, lane_offramp_runtime, urban_flow_accounting\n'
                'print("SA_LOADED" if "evaluation.controllers.stopline_approach" in sys.modules else "SA_ABSENT")'
                % (str(ROOT), str(ROOT / 'vendor/NumSim-mine')))
        done = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, cwd=ROOT,
                              encoding='utf-8', errors='replace',
                              env={**__import__('os').environ, 'PYTHONHASHSEED': '0'})
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        self.assertEqual(done.stdout.strip().splitlines()[-1], 'SA_ABSENT')

    @staticmethod
    def guarded_names(tree, wanted, guard):
        """Names in `wanted` that occur outside every If whose test satisfies guard."""
        bad = []

        def walk(node, inside):
            if isinstance(node, ast.If) and guard(node.test):
                for child in node.body:
                    walk(child, True)
                for child in node.orelse:
                    walk(child, inside)
                walk(node.test, inside)
                return
            if isinstance(node, (ast.Name, ast.alias)):
                name = node.id if isinstance(node, ast.Name) else (node.asname or node.name)
                if name in wanted and not inside:
                    bad.append((getattr(node, 'lineno', None), name))
            if isinstance(node, ast.ImportFrom) and node.module and 'stopline_approach' in node.module and not inside:
                bad.append((node.lineno, node.module))
            for child in ast.iter_child_nodes(node):
                walk(child, inside)

        walk(tree, False)
        return bad

    def test_ufa_hooks_are_behind_the_view(self):
        tree = ast.parse((ROOT / UFA_REL).read_text(encoding='utf-8'))
        mentions = lambda test: 'sa' in {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
        self.assertEqual(self.guarded_names(tree, {'_sa', 'stopline_approach'}, mentions), [])
        src = (ROOT / UFA_REL).read_text(encoding='utf-8')
        self.assertEqual(src.count("getattr(net, 'stopline_approach', None)"), 1)
        self.assertNotIn('import stopline_approach\n', src.split('def urban_substep_accounted')[0])
        self.assertEqual(src.count('_sa.'), 6)   # #6 split, #7 enqueue, #8 intended, #9 resolve, #10 depart, #10b end

    def test_lor_hooks_are_behind_the_row_field(self):
        tree = ast.parse((ROOT / LOR_REL).read_text(encoding='utf-8'))
        row_field = lambda test: "approach" in ast.unparse(test) and 'row.get' in ast.unparse(test)
        self.assertEqual(self.guarded_names(tree, {'stopline_approach'}, row_field), [])
        self.assertEqual((ROOT / LOR_REL).read_text(encoding='utf-8').count("row.get('approach')"), 2)

    def test_rs_hooks_are_behind_the_tuning_key(self):
        tree = ast.parse((ROOT / RS_REL).read_bytes().decode('utf-8'))
        key = lambda test: "'stopline_approach'" in ast.unparse(test) and 'is not None' in ast.unparse(test)
        self.assertEqual(self.guarded_names(tree, {'stopline_approach'}, key), [])
        source = (ROOT / RS_REL).read_bytes().decode('utf-8')
        configure = source.index('stopline_approach.configure(')
        self.assertLess(source.index('local_signal_service.configure(cfg, tuning)'), configure)  # after LSS/HSR (#2)
        self.assertLess(configure, source.index('physical_ramp_branches.configure('))
        initialize = source.index('stopline_approach.initialize(')
        self.assertLess(source.index('lane_plant_runtime.initialize('), initialize)              # RS:253 (#3)
        self.assertLess(initialize, source.index('area_runtime.configure(a, cfg, tuning'))       # before RS:254

    def test_hook_order_is_the_amended_second_order(self):
        """Amendment 2.3: arrival split (3) < gate landing (4) < off-ramp drain (6) < intended < resolve
        < depart before the ledger transfer (7) < end_step; LOR: allocate < port.release < land_release."""
        body = (ROOT / UFA_REL).read_text(encoding='utf-8').split('def urban_substep_accounted(')[1]
        body = body.split('\ndef ')[0]
        marks = ['_sa.split_arrival(', '_sa.enqueue_city(', '_drain_offramp_storage_accounted(state', '_sa.intended(',
                 '_sa.resolve(', '_sa.depart(', '_sa.end_step(']
        positions = [body.index(mark) for mark in marks]
        self.assertEqual(positions, sorted(positions))
        depart = body.index('_sa.depart(')
        self.assertGreater(body.find("state.urban_movement_queue[movement] = max(0.0, before - actual)", depart), depart)
        self.assertLess(body.rindex("actual = min(before, departed)"), depart)
        lor = (ROOT / LOR_REL).read_text(encoding='utf-8')
        marks = ['stopline_approach.allocate(', 'port.release(', 'stopline_approach.land_release(']
        positions = [lor.index(mark) for mark in marks]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(lor.index("state.urban_link_storage[key]+=n"), lor.index('stopline_approach.land_release('))

    def test_runtime_files_differ_from_the_base_only_by_hooks(self):
        """Every base line reappears (re-indented) except the declared counted-inflow replacement (#10, 5.6-8)."""
        replaced = {UFA_REL: {'urban_gate_inflow_veh += actual': 'urban_gate_inflow_veh += counted'}}
        for rel in (UFA_REL, LOR_REL, RS_REL):
            with self.subTest(rel):
                old = git_show(rel).decode('utf-8').splitlines()
                new = (ROOT / rel).read_bytes().decode('utf-8').splitlines()
                stripped = {line.strip() for line in new}
                lost = {line.strip() for line in old if line.strip() and line.strip() not in stripped}
                self.assertEqual(lost, set(replaced.get(rel, {})))
                for line in replaced.get(rel, {}).values():
                    self.assertIn(line, stripped)


# -------------------------------------------- key present: the real wired loop

class WiredLoopTests(unittest.TestCase):
    def run_wired(self, steps=240, arm='observed_full', evidence=None):
        cfg, state, control = graft(sa=True, arm=arm, evidence=evidence, idle=True)
        reads = []
        original = uqm._movement_capacity_flow

        def spy(control_, cfg_, movement, spec):
            reads.append(movement)
            return original(control_, cfg_, movement, spec)

        rows = []
        with mock.patch.object(uqm, '_movement_capacity_flow', spy):
            run(cfg, state, control, ufa, steps, each=lambda t, c, d: rows.append(d))
        return cfg, state, rows, reads

    def test_invariants_accounting_and_capacity_table(self):
        cfg, state, rows, reads = self.run_wired()
        st = state.stopline_approach_state
        self.assertEqual(st['last_step'], T0 + 239)
        self.assertEqual(st['plan'], {})
        expected = ['stopline_' + k for k in SA.STEP_KEYS]
        for diag in rows:
            self.assertEqual([k for k in diag if k.startswith('stopline_')], expected)
        self.assertLessEqual(len(expected), 20)
        c = st['counters']
        for key in ('port_release_veh_10491', 'port_release_veh_10481', 'served_port_OR_D_W_veh',
                    'served_port_OR_D_E_veh', 'served_city_veh', 'served_init_city_veh', 'served_init_port_veh',
                    'np_boundary_in_veh', 'internal_crossing_veh'):
            self.assertGreater(c[key], 0.0, key)
        self.assertAlmostEqual(c['np_off_ramp_veh'], c['port_release_veh_10491'] + c['port_release_veh_10481'],
                               places=12)
        # N_P (amendment 5.6): the gate inflow is exactly the city-side crossings; ports count once at release.
        gate = math.fsum(d['urban_gate_inflow_veh'] for d in rows)
        inbound = math.fsum(d['inbound_service_veh'] for d in rows)
        released = math.fsum(d['offramp_departures_veh'] for d in rows)
        self.assertAlmostEqual(gate, c['np_boundary_in_veh'], delta=1e-9)
        self.assertAlmostEqual(inbound, released + c['np_boundary_in_veh'], delta=1e-9)
        self.assertAlmostEqual(released, c['np_off_ramp_veh'], delta=1e-9)
        flows = state._control_area_ledger.flow_counts
        for member in (E, S, N):
            self.assertGreater(flows['stopline_internal:' + member], 0.0)
            self.assertGreater(flows['movement:' + member], 0.0)
        for tag in ('offW', 'offE'):
            for dest in ('E_SC1002', 'S_SC1003', 'N_SC2002'):
                self.assertGreater(flows['movement:SC1001_%s_to_%s' % (tag, dest)], 0.0)
            self.assertNotIn('movement:SC1001_%s_to_W_RAMP' % tag, flows)
        # B6: neither the W members nor the two approach ports read the capacity table.
        self.assertFalse(set(reads) & ({E, S, N} | set(cfg.network.stopline_approach['offramp_movements'])))
        self.assertTrue(reads)      # the rest of the network still does
        for name in cfg.network.stopline_approach['offramp_movements']:
            self.assertEqual(state.urban_movement_queue[name], 0.0)

    def test_geometric_arm_runs(self):
        cfg, state, rows, _reads = self.run_wired(steps=60, arm='geometric')
        self.assertEqual(cfg.network.stopline_approach['lanes'][1]['S'], T.HEADS[1] / 6.0)
        self.assertEqual(state.stopline_approach_state['last_step'], T0 + 59)

    def test_committed_evidence_drives_the_loop(self):
        document = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/stopline/'
                               'sc1001eb_evidence_v3c3_20261004.json').read_text(encoding='utf-8'))
        cfg, state, rows, _reads = self.run_wired(steps=60, evidence=document)
        spec = cfg.network.stopline_approach
        self.assertEqual((spec['lanes'][1]['S'], spec['lanes'][2]['S']), (81.0, 63.0))
        self.assertEqual(state.stopline_approach_state['last_step'], T0 + 59)

    def test_noncontiguous_step_is_refused(self):
        cfg, state, control = graft(sa=True)
        run(cfg, state, control, ufa, 3)
        with self.assertRaises(SA.StoplineInvariantError):
            run(cfg, state, control, ufa, 1, t0=T0 + 4)


class ToyOrderTests(unittest.TestCase):
    """The toy drive used by the module tests and the tangent probe is the real UFA/LOR hook order."""

    def test_toy_drive_equals_the_wired_loop(self):
        cfg, state, control = graft(sa=True, gate=False)
        tcfg = T.config()
        for name, row in tcfg.network.urban_movements.items():     # the graft's in_SC1001_W beta (no ramps)
            if row.get('origin') == IN:
                row['beta'] = T.OFF_BETA[DEST[name]] if name in DEST else 0.0
        tcfg, tst = T.bare(T0, cohorts=COHORTS, speed_kmh=30.0, cfg=tcfg)
        seed_stocks(tst, tcfg, T0)
        ctl = T.control()

        def compare(t):
            a, b = state.stopline_approach_state, tst.stopline_approach_state
            for key in ('lanes', 'stock', 'carry', 'tags', 'counters', 'next_seq', 'city_over', 'last_step'):
                self.assertEqual(a[key], b[key], f'{key} at {t}')
            for member in (E, S, N):
                self.assertEqual(state.urban_movement_queue[member], tst.urban_movement_queue[member])
            self.assertEqual(state.urban_link_storage[IN], tst.urban_link_storage[IN])
            self.assertEqual(state.urban_arrival_buffer.get(IN), tst.urban_arrival_buffer.get(IN))

        def toy_step(t, _cost, _diag):
            T.drive(tst, tcfg, ctl, t, landing=LANDING)
            compare(t)

        run(cfg, state, control, ufa, 200, gate=False, each=toy_step)
        self.assertGreater(state.stopline_approach_state['counters']['port_release_veh_10481'], 0.0)


class LorRowTests(unittest.TestCase):
    def test_approach_rows_bypass_the_movement_branch(self):
        """Hook #4/#5: the approach row requests SA.allocate's limit and lands through SA.land_release."""
        cfg, state, control = graft(sa=True, gate=False)
        state._control_area_ledger.begin_response_step('urban', T0, T0 + 1)
        lor = state.lane_offramp_runtime
        with mock.patch.object(SA, 'land_release', wraps=SA.land_release) as landed, \
                mock.patch.object(SA, 'allocate', wraps=SA.allocate) as allocated:
            SA.split_arrival(state, cfg, T0, 0.0, uqm.approach_routing(cfg)[IN])
            out = lor.drain(state, control, cfg, T0, uqm.approach_routing(cfg))
        self.assertEqual([c.args[3] for c in allocated.call_args_list], ['10491', '10481'])
        self.assertEqual(sorted(c.args[3] for c in landed.call_args_list), ['10481', '10491'])
        plan = state.stopline_approach_state['plan']['ports']
        for off, group in (('10491', 'OR_D_W'), ('10481', 'OR_D_E')):
            self.assertLessEqual(out[group], plan[off]['limit'] + 1e-12)
            self.assertEqual(plan[off]['released'], out[group])
        lor.assert_mirrors(state, cfg)


# ------------------------------------------------------- T2 make_config flags

class ConfigFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import make_config_n31 as m
        cls.m = m
        if not (ROOT / m.BASE).is_file():
            raise unittest.SkipTest('WP-E base config not in this tree')
        cls.base = m.build()

    def test_default_output_is_byte_identical(self):
        self.assertEqual(self.m.dumps(self.base), self.m.OUT.read_bytes())

    def test_arms_add_exactly_the_key(self):
        base = json.loads(self.m.dumps(self.base))
        for arm in self.m.STOPLINE_STORAGES:
            with self.subTest(arm):
                doc = self.m.apply_stopline_approach(self.base, self.m.STOPLINE_EVIDENCE, arm)
                section = doc['urban']['stopline_approach']
                SA.check_section(section)
                self.assertEqual(list(section), list(SA.TUNING_FIELDS))
                self.assertEqual(section['storage'], arm)
                self.assertEqual(section['evidence']['path'], self.m.STOPLINE_EVIDENCE)
                document, digest = SA.load_evidence(section['evidence'])
                self.assertEqual(digest, section['evidence']['sha256'])
                stripped = json.loads(self.m.dumps(doc))
                stripped['urban'].pop('stopline_approach')
                self.assertEqual(stripped, base)
                self.assertEqual(self.m.stopline_out(arm).name, 'config_n31_v2_stopline_%s.json' % arm)
        self.assertEqual(self.m.dumps(self.base), self.m.OUT.read_bytes())       # the base doc is not mutated

    def test_flag_contract(self):
        with self.assertRaises(ValueError):
            self.m.stopline_section(self.m.STOPLINE_EVIDENCE, 'sfull')
        with self.assertRaises(ValueError):
            doc = self.m.apply_stopline_approach(self.base, self.m.STOPLINE_EVIDENCE, 'geometric')
            self.m.apply_stopline_approach(doc, self.m.STOPLINE_EVIDENCE, 'geometric')
        for argv in (['--stopline-approach', self.m.STOPLINE_EVIDENCE],
                     ['--stopline-storage', 'geometric'],
                     ['--stopline-approach', self.m.STOPLINE_EVIDENCE, '--stopline-storage', 'geometric',
                      '--urban-batch1']):
            with self.subTest(argv), mock.patch.object(sys, 'argv', ['make_config_n31.py', *argv]), \
                    self.assertRaises(SystemExit):
                self.m.main()

    def test_configure_accepts_the_generated_section(self):
        doc = self.m.apply_stopline_approach(self.base, self.m.STOPLINE_EVIDENCE, 'observed_full')
        cfg = T.config()
        meta = SA.configure(cfg, doc, {})
        self.assertEqual(meta['stopline_approach_storage_arm'], 'observed_full')
        self.assertEqual(meta['stopline_approach_storage_veh'], {'1': 81.0, '2': 63.0, '3': T.HEADS[3] / 6.0})


if __name__ == '__main__':
    unittest.main()
