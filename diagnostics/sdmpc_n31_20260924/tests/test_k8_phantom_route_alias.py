"""K8-9 tests (K8 amendment 22 section 6.2-3; D-K9-16, D-K9-20): phantom route alias at the ledger failure site only.

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_k8_phantom_route_alias.py -rA

t1 the check tool on this tree rebuilds exactly PHANTOM_ROUTE_ALIAS (exit 0, also with --check).
t2 a table phantom with stock leaves: no raise; the sibling probabilities and crossings give the hand-computed
   stocks, ttd_veh and entered_veh; flow_counts[<phantom>] and flow_counts['phantom_route_alias:<phantom>'] = count.
t3 sibling route missing / probability None / 1.5 / NaN / bool -> the original message, (None, None).
t4 a no_match key outside the table -> the original message, no 'phantom_route_alias:' key.
t5 a table key whose leaving amount is <= 1e-9 -> no raise, same as the old module, no alias key.
t6 a fixed-seed random sequence of transfers and emit_transfer calls (keys outside the table, table keys with numeric
   probabilities, preserve_area, target_inside, physical crossing routes, external inputs, duplicate event ids)
   gives the same ledger as the old module, repr for repr.
t7 ModelAreaLedger.transfer called without alias_route (other callers) equals the old module, raise included.
The old module is `git show 74cd495f:evaluation/controllers/control_area_objective.py` (sha256 checked), executed as
a separate module.  Without git history (a frozen copy) t5, t6 and t7 are skipped; in the repository they must run.
Synthetic objects only: no capture, no rollout, no adapter run, no VISSIM.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import control_area_objective as cao  # noqa: E402

TOOL = ROOT / 'diagnostics/sdmpc_n31_20260924/k9/phantom_route_alias.py'
CAO_REL = 'evaluation/controllers/control_area_objective.py'
BASE = '74cd495f3b08312eb11384f4fcf06109a26c0cba'
OLD_SHA256 = '8ce335e38e4a9c8e9ba9229e4c918d545d22884649167ee4d8132bd8c6c86aa5'
TABLE = {'movement:SC5_S_to_E_SC6': 'movement:SC5_S_SC11_to_E_SC6',
         'movement:SC5_S_to_N_SC102': 'movement:SC5_S_SC11_to_N_SC102',
         'movement:SC5_S_to_W_SC101': 'movement:SC5_S_SC11_to_W_SC101'}
TABLE_SHA256 = '1be612c11f36b744f5084a958233db22b00e3a2072ea1806e8f8d9bc6dda032f'
P_N, P_E, P_W = 'movement:SC5_S_to_N_SC102', 'movement:SC5_S_to_E_SC6', 'movement:SC5_S_to_W_SC101'
OUTSIDE = 'movement:SC7_E_SC16_to_N_SC11'
_OLD = {}


def phantom_route():
    """The runtime route of a phantom (route contract no_match): both probabilities null, the crossing key present."""
    return {'status': 'no_match', 'source_inside': None, 'target_inside': None, 'inside_to_inside': None,
            'outside_to_inside': None, 'outward_crossings_per_vehicle': None, 'inward_crossings_per_vehicle': None,
            'physical_turns': []}


def sibling_routes():
    """The three siblings as in the route contract at 74cd495f (status unique, one physical turn each)."""
    return {
        'movement:SC5_S_SC11_to_N_SC102': {'status': 'unique', 'source_inside': True, 'target_inside': False,
                                           'inside_to_inside': 0.0, 'outside_to_inside': 0.0,
                                           'outward_crossings_per_vehicle': 1, 'inward_crossings_per_vehicle': 0},
        'movement:SC5_S_SC11_to_E_SC6': {'status': 'unique', 'source_inside': True, 'target_inside': True,
                                         'inside_to_inside': 1.0, 'outside_to_inside': 1.0,
                                         'outward_crossings_per_vehicle': 0, 'inward_crossings_per_vehicle': 0},
        'movement:SC5_S_SC11_to_W_SC101': {'status': 'unique', 'source_inside': True, 'target_inside': True,
                                           'inside_to_inside': 1.0, 'outside_to_inside': 1.0,
                                           'outward_crossings_per_vehicle': 0, 'inward_crossings_per_vehicle': 0}}


def config(routes):
    return NS(network=NS(control_area_routes=routes))


def phantom_config(**sibling_override):
    routes = {P_N: phantom_route(), P_E: phantom_route(), P_W: phantom_route(), OUTSIDE: phantom_route()}
    routes.update(sibling_routes())
    for key, value in sibling_override.items():
        routes[key] = value
    return config(routes)


def ledger_state(module, stocks):
    ledger = module.ModelAreaLedger(stocks, capture_response=True)
    ledger.begin_response_step('urban', 900, 902)
    return NS(_control_area_ledger=ledger), ledger


def old_module():
    if 'module' in _OLD:
        return _OLD['module']
    try:
        done = subprocess.run(['git', '-C', str(ROOT), 'show', f'{BASE}:{CAO_REL}'], capture_output=True)
    except OSError:
        done = None
    if done is None or done.returncode != 0:
        raise unittest.SkipTest('git history of 74cd495f is not available here (frozen copy)')
    data = done.stdout
    if hashlib.sha256(data).hexdigest() != OLD_SHA256:
        raise AssertionError('74cd495f control_area_objective.py differs from its declared sha256')
    name = 'k8_9_old_control_area_objective'
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / CAO_REL)
    sys.modules[name] = module
    exec(compile(data.decode('utf-8'), f'74cd495f:{CAO_REL}', 'exec'), module.__dict__)
    _OLD['module'] = module
    return module


def tearDownModule():
    sys.modules.pop('k8_9_old_control_area_objective', None)


def snapshot(ledger):
    return {'stocks': repr(ledger.stocks), 'ttd_veh': repr(ledger.ttd_veh), 'entered_veh': repr(ledger.entered_veh),
            'ttt_veh_h': repr(ledger.ttt_veh_h), 'flow_counts': repr(ledger.flow_counts),
            'event_count': repr(ledger.event_count), 'explicit_events': repr(ledger.explicit_events),
            '_response': repr(getattr(ledger, '_response', None))}


class Tool(unittest.TestCase):
    def test_t1_tool_rebuilds_the_table(self):
        self.assertEqual(cao.PHANTOM_ROUTE_ALIAS, TABLE)
        self.assertEqual(json.dumps(cao.PHANTOM_ROUTE_ALIAS, sort_keys=True), json.dumps(TABLE, sort_keys=True))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'alias.json'
            done = subprocess.run([sys.executable, '-B', str(TOOL), '--root', str(ROOT), '--out', str(out)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            last = done.stdout.strip().splitlines()[-1]
            self.assertEqual(last, f'PHANTOM_ALIAS_OK n=3 table_sha256={TABLE_SHA256}')
            report = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(json.dumps(report['table'], sort_keys=True),
                             json.dumps(cao.PHANTOM_ROUTE_ALIAS, sort_keys=True))
            self.assertTrue(all(report['table_keys_in_enumeration'].values()))
            for key, row in report['phantoms'].items():
                self.assertEqual((row['verdict'], row['S(P)']), ('UNIQUE', ['1220014100']), key)
            checked = subprocess.run([sys.executable, '-B', str(TOOL), '--root', str(ROOT), '--check'],
                                     capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(checked.stdout.strip().splitlines()[-1], last)


class AliasSite(unittest.TestCase):
    def test_t2_phantom_with_stock_uses_the_sibling(self):
        # N_SC102 sibling: inside_to_inside 0, outside_to_inside 0, source_inside True, crossings out 1 / in 0
        state, ledger = ledger_state(cao, {'queue:P': {'inside': 6, 'outside': 2}})
        cao.emit_transfer(state, phantom_config(), 'queue:P', 'storage:SC5_to_SC102', 4, route_key=P_N)
        # draw_in = 4*6/8 = 3, draw_out = 1; target all outside; ttd = 4 * 1 outward; entered = remap entry 1
        self.assertEqual(ledger.stocks, {'queue:P': {'inside': 3.0, 'outside': 1.0},
                                         'storage:SC5_to_SC102': {'inside': 0.0, 'outside': 4.0}})
        self.assertEqual((ledger.ttd_veh, ledger.entered_veh), (4.0, 1.0))
        self.assertEqual(ledger.flow_counts[P_N], 4.0)
        self.assertEqual(ledger.flow_counts['phantom_route_alias:' + P_N], 4.0)
        self.assertEqual(ledger.flow_counts['spatial_remap_entry_veh'], 1.0)
        self.assertEqual(ledger.flow_counts['spatial_remap_exit_veh'], 0.0)
        row = ledger._response['transfers'][-1]
        self.assertEqual((row['route_key'], row['vehicles'], row['ttd_veh'], row['entered_veh']), (P_N, 4.0, 4.0, 1.0))
        # E_SC6 sibling: 1 / 1, crossings 0 / 0, source_inside True
        state, ledger = ledger_state(cao, {'queue:P': {'inside': 6, 'outside': 2}})
        cao.emit_transfer(state, phantom_config(), 'queue:P', 'storage:SC5_to_SC6', 4, route_key=P_E)
        self.assertEqual(ledger.stocks, {'queue:P': {'inside': 3.0, 'outside': 1.0},
                                         'storage:SC5_to_SC6': {'inside': 4.0, 'outside': 0.0}})
        self.assertEqual((ledger.ttd_veh, ledger.entered_veh), (0.0, 1.0))
        self.assertEqual(ledger.flow_counts[P_E], 4.0)
        self.assertEqual(ledger.flow_counts['phantom_route_alias:' + P_E], 4.0)
        # W_SC101 through the ledger directly with the sibling route
        state, ledger = ledger_state(cao, {'queue:P': {'inside': 0, 'outside': 5}})
        ledger.transfer('queue:P', 'storage:SC5_to_SC101', 2, route_key=P_W,
                        alias_route=sibling_routes()['movement:SC5_S_SC11_to_W_SC101'])
        self.assertEqual(ledger.stocks, {'queue:P': {'inside': 0.0, 'outside': 3.0},
                                         'storage:SC5_to_SC101': {'inside': 2.0, 'outside': 0.0}})
        self.assertEqual((ledger.ttd_veh, ledger.entered_veh), (0.0, 2.0))
        self.assertEqual(ledger.flow_counts['phantom_route_alias:' + P_W], 2.0)

    def test_t3_unusable_sibling_keeps_the_original_failure(self):
        sibling = 'movement:SC5_S_SC11_to_N_SC102'
        bad = []
        missing = phantom_config()
        del missing.network.control_area_routes[sibling]
        bad.append(('missing', missing))
        for label, values in (('none', (None, 0.0)), ('one_and_half', (0.0, 1.5)), ('nan', (float('nan'), 0.0)),
                              ('bool', (True, False)), ('negative', (-0.1, 0.0)), ('string', ('0', 0.0))):
            route = dict(sibling_routes()[sibling])
            route['inside_to_inside'], route['outside_to_inside'] = values
            bad.append((label, phantom_config(**{sibling: route})))
        for label, cfg in bad:
            with self.subTest(label):
                state, ledger = ledger_state(cao, {'queue:P': {'inside': 6, 'outside': 2}})
                with self.assertRaises(cao.MembershipError) as caught:
                    cao.emit_transfer(state, cfg, 'queue:P', 'storage:SC5_to_SC102', 4, route_key=P_N)
                self.assertEqual(str(caught.exception),
                                 'unresolved destination of movement:SC5_S_to_N_SC102: (None, None)')
                self.assertNotIn('phantom_route_alias:' + P_N, ledger.flow_counts)
                self.assertEqual(ledger.stocks, {'queue:P': {'inside': 6.0, 'outside': 2.0}})

    def test_t4_phantom_outside_the_table_keeps_the_original_failure(self):
        self.assertNotIn(OUTSIDE, cao.PHANTOM_ROUTE_ALIAS)
        state, ledger = ledger_state(cao, {'queue:Q': {'inside': 1, 'outside': 1}})
        with self.assertRaises(cao.MembershipError) as caught:
            cao.emit_transfer(state, phantom_config(), 'queue:Q', 'storage:x', 1.5, route_key=OUTSIDE)
        self.assertEqual(str(caught.exception), f'unresolved destination of {OUTSIDE}: (None, None)')
        self.assertFalse([k for k in ledger.flow_counts if str(k).startswith('phantom_route_alias:')])


class SuccessPathUnchanged(unittest.TestCase):
    def setUp(self):
        self.old = old_module()

    def run_both(self, stocks, calls):
        results = []
        for module in (self.old, cao):
            state, ledger = ledger_state(module, stocks)
            outcomes = []
            for kind, args, kwargs in calls:
                try:
                    if kind == 'emit':
                        module.emit_transfer(state, *args, **kwargs)
                    elif kind == 'transfer':
                        ledger.transfer(*args, **kwargs)
                    else:
                        ledger.residence(*args, **kwargs)
                    outcomes.append('ok')
                except module.MembershipError as error:
                    outcomes.append('MembershipError: ' + str(error))
            results.append((outcomes, snapshot(ledger)))
        return results

    def test_t5_table_key_with_tiny_leaving_amount(self):
        cfg = phantom_config()
        calls = [('emit', (cfg, 'queue:P', 'storage:SC5_to_SC102', 5e-10), {'route_key': P_N}),
                 ('emit', (cfg, 'queue:P', 'storage:SC5_to_SC6', 1e-9), {'route_key': P_E}),
                 ('emit', (cfg, 'queue:P', 'storage:SC5_to_SC101', 0.0), {'route_key': P_W})]
        (old_out, old_snap), (new_out, new_snap) = self.run_both({'queue:P': {'inside': 6, 'outside': 2}}, calls)
        self.assertEqual(new_out, ['ok', 'ok', 'ok'])
        self.assertEqual(old_out, new_out)
        self.assertEqual(old_snap, new_snap)
        self.assertNotIn('phantom_route_alias', new_snap['flow_counts'])

    def test_t6_random_success_sequence_is_identical(self):
        rng = random.Random(20261014)
        routes = {
            'movement:A_to_B': {'status': 'unique', 'inside_to_inside': 0.7, 'outside_to_inside': 0.2},
            'movement:B_to_C': {'status': 'unique', 'source_inside': True, 'inside_to_inside': 0.0,
                                'outside_to_inside': 0.0, 'outward_crossings_per_vehicle': 1,
                                'inward_crossings_per_vehicle': 0},
            'movement:C_to_A': {'status': 'unique', 'source_inside': False, 'inside_to_inside': 1.0,
                                'outside_to_inside': 1.0, 'outward_crossings_per_vehicle': 0,
                                'inward_crossings_per_vehicle': 1},
            'arrival:D': {'status': 'unique', 'target_inside': True},
            # table keys whose own probabilities are numbers: the alias is never looked up
            P_N: {'status': 'unique', 'inside_to_inside': 0.25, 'outside_to_inside': 0.5},
            P_E: {'status': 'unique', 'source_inside': True, 'inside_to_inside': 1.0, 'outside_to_inside': 0.0,
                  'outward_crossings_per_vehicle': 0, 'inward_crossings_per_vehicle': 2},
            'diag:preserve': {'status': 'DIAGNOSTIC_UNRESOLVED_PRESERVE'},
        }
        routes.update(sibling_routes())
        cfg = config(routes)
        stocks = {'s:A': {'inside': 40, 'outside': 10}, 's:B': {'inside': 5, 'outside': 25},
                  's:C': {'inside': 12, 'outside': 12}, 's:D': {'inside': 0, 'outside': 0}}
        shadow = {k: v['inside'] + v['outside'] for k, v in stocks.items()}
        names = sorted(stocks)
        calls, events = [], []
        for i in range(400):
            source = rng.choice(names)
            target = rng.choice([n for n in names if n != source])
            amount = round(rng.uniform(0.0, 0.3) * shadow[source], 6)
            pick = rng.randrange(9)
            event = None
            if rng.random() < 0.15:
                event = f'ev{i}'
                events.append(event)
            if pick == 0:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'movement:A_to_B', 'event_id': event})
            elif pick == 1:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'movement:B_to_C', 'event_id': event})
            elif pick == 2:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'movement:C_to_A', 'event_id': event})
            elif pick == 3:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'arrival:D', 'event_id': event})
            elif pick == 4:
                call = ('emit', (cfg, source, target, amount), {'route_key': rng.choice([P_N, P_E]),
                                                                  'event_id': event})
            elif pick == 5:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'diag:preserve', 'preserve_area': True,
                                                                  'event_id': event})
            elif pick == 6:
                call = ('emit', (cfg, source, target, amount), {'route_key': 'movement:x',
                                                                  'target_inside': rng.random() < 0.5,
                                                                  'event_id': event})
            elif pick == 7:
                amount = round(rng.uniform(0.0, 3.0), 6)
                call = ('emit', (cfg, 'external:gate', source, amount), {'route_key': 'arrival:D',
                                                                          'source_inside': rng.random() < 0.5})
                shadow[source] += amount
                calls.append(call)
                continue
            else:
                call = ('residence', (tuple(names), rng.uniform(0.0, 0.01)), {'event_id': f'res{i}'})
                calls.append(call)
                continue
            calls.append(call)
            shadow[source] -= amount
            shadow[target] += amount
            if event is not None and rng.random() < 0.5:
                calls.append(call)          # an exact retry with the same event id is idempotent
                calls.append(('emit', (cfg, source, target, 0.0), {'route_key': 'movement:A_to_B'}))
        (old_out, old_snap), (new_out, new_snap) = self.run_both(stocks, calls)
        self.assertEqual(set(new_out), {'ok'})
        self.assertEqual(old_out, new_out)
        for key in old_snap:
            with self.subTest(key):
                self.assertEqual(old_snap[key], new_snap[key])
        self.assertNotIn('phantom_route_alias', new_snap['flow_counts'])
        self.assertGreater(len(events), 10)

    def test_t7_direct_transfer_without_alias_route(self):
        calls = [('transfer', ('q:1', 'q:2', 3), {'inside_to_inside': 0.5, 'outside_to_inside': 0.25,
                                                  'route_key': 'r1', 'event_id': 'e1'}),
                 ('transfer', ('q:1', 'q:2', 3), {'inside_to_inside': 0.5, 'outside_to_inside': 0.25,
                                                  'route_key': 'r1', 'event_id': 'e1'}),
                 ('transfer', ('q:2', 'q:3', 1.25), {'inside_to_inside': 1.0, 'outside_to_inside': 0.0,
                                                     'route_key': 'r2', 'physical_source_inside': False,
                                                     'outward_crossings': 0, 'inward_crossings': 1}),
                 ('transfer', ('external:in', 'q:1', 2), {'source_inside': True, 'inside_to_inside': 1.0,
                                                          'outside_to_inside': 1.0, 'route_key': 'r3'}),
                 ('transfer', ('q:1', 'q:3', 0.5), {'route_key': P_N}),
                 ('transfer', ('q:1', 'q:3', 0.0), {'route_key': P_N}),
                 ('transfer', ('q:3', 'q:1', 1e-10), {'route_key': P_E}),
                 ('residence', (('q:1', 'q:2', 'q:3'), 0.002), {'event_id': 'r'})]
        (old_out, old_snap), (new_out, new_snap) = self.run_both(
            {'q:1': {'inside': 4, 'outside': 4}, 'q:2': {'inside': 1}, 'q:3': {'outside': 2}}, calls)
        self.assertEqual(old_out, new_out)
        self.assertEqual(new_out[4], 'MembershipError: unresolved destination of movement:SC5_S_to_N_SC102: (None, None)')
        self.assertEqual(old_snap, new_snap)
        self.assertNotIn('phantom_route_alias', new_snap['flow_counts'])


if __name__ == '__main__':
    unittest.main()
