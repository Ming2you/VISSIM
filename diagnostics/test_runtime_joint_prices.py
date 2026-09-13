"""Runtime common price basis using synthetic linear physical responses."""
import copy
import hashlib
import math
import pickle
from types import SimpleNamespace as NS
import unittest

from diagnostics.test_joint_price_field import fixture
from evaluation.controllers import area_runtime, joint_owner_game as game


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def live(signal):
    return ('p1', 'p2') if signal == 'SC17' else ('p1', 'p2', 'p3', 'p4')


def cycle(signal):
    return 120. if signal == 'SC1' else 150.


class RuntimeJointPricesTests(unittest.TestCase):
    def setUp(self):
        self.follower, self.reference, edges, self.truth = fixture()
        net = self.follower.cfg.network
        net.signal_live_phases, net.signal_cycle_length = live, cycle
        net.control_area_beta_seconds = 300.
        net.ramp_capacity_veh_h = dict.fromkeys(net.ramps, 100.)  # Reference is all-open.
        self.owners = tuple(net.signals)+tuple(net.freeway_links)
        addresses = []
        for owner in self.owners:
            if owner in net.signals:
                addresses.extend(game.Address('green_times', owner+'_'+p, owner,
                    'strategy' if p in live(owner) else 'fixed_dead') for p in ('p1','p2','p3','p4'))
                addresses.append(game.Address('offsets', owner, owner, 'strategy'))
            else:
                for i, head in enumerate(net.freeway_vsl_zone_head_of_cell[owner]):
                    role = 'fixed_recovery' if head == 4 else 'strategy' if i == head else 'derived'
                    addresses.append(game.Address('vsl', owner+f'__seg{i}', owner, role))
                addresses.append(game.Address('vsl', owner, owner, 'derived'))
                addresses.extend(game.Address('ramp_metering', r, owner, 'strategy')
                    for r in self.follower._local_freeway_models[owner].owned_ramps)
        self.ownership = game.Ownership(self.owners, tuple(addresses), ())
        self.domains = {}
        for owner, rows in edges.items():
            actions = [copy.deepcopy(self.reference)]
            for row in rows:
                action = copy.deepcopy(self.reference)
                coordinate = row['coordinate']
                for key, delta in coordinate['direction'].items():
                    field = next(a.field for a in addresses if a.owner == owner and a.key == key)
                    if field == 'ramp_metering':
                        delta = -abs(delta)
                    getattr(action, field)[key] += delta
                if owner in net.signals:
                    action.offsets[owner] %= cycle(owner)
                else:
                    action.vsl[owner] = min(action.vsl[f'{owner}__seg{i}'] for i in range(6))
                actions.append(action)
            self.domains[owner] = tuple(actions)
        self.context = {'common_anchor': 'actual-previous', 'source': 'synthetic-v1'}
        self.callbacks = {'ownership': self.ownership,
            'neighbors': lambda owner, action, context: game.Neighborhood(self.domains[owner], True, 'synthetic written fixed box'),
            'command_evidence': self.evidence}
        self.calls = []

    def evidence(self, action, context):
        return {'owner_physical_sha256': {owner: digest({a.key: getattr(action,a.field)[a.key]
            for a in self.ownership.addresses if a.owner == owner}) for owner in self.owners}}

    def responses(self, actions):
        output = []
        for action in actions:
            self.calls.append(copy.deepcopy(action))
            local = dict.fromkeys(self.owners, 10.)
            total_external = 0.
            for owner in self.owners:
                changed = False
                for key, price in self.truth[owner].items():
                    field = next(a.field for a in self.ownership.addresses if a.owner == owner and a.key == key)
                    delta = getattr(action,field)[key]-getattr(self.reference,field)[key]
                    if field == 'offsets':
                        delta = ((delta+cycle(owner)/2) % cycle(owner))-cycle(owner)/2
                    changed |= delta != 0.
                    total_external += price*delta
                if changed:
                    local[owner] += 4.
            output.append({'action_token': digest(action), 'response_token': digest(('response',action)),
                'frozen_context_token': 'fixed-model-inputs', 'conditional_model_feasibility_witness': True,
                'objective_veh_h': 100.+sum(v-10. for v in local.values())+total_external,
                'local_base_costs': local})
        return {'results': output, 'endpoint_calls': len(actions)}

    def evaluate(self, **changes):
        options = dict(callbacks=self.callbacks, context=self.context, context_fingerprint=digest,
            horizon_steps=3, directional_nuf_targets_veh_h=None, nuf_tolerance_veh_h=0.,
            source_fingerprint='synthetic-v1', response_query=self.responses, nuf_price_policy='independent')
        options.update(changes)
        return area_runtime.evaluate_joint_prices(self.follower, NS(time_sec=900.), self.reference,
            [NS(demand=1.)]*3, **options)

    def test_all_open_independent_meters_use_one_sided_probes_without_false_zero_prices(self):
        result = self.evaluate()
        field = result['field']
        self.assertEqual(field['nuf_price_policy'], 'independent')
        for owner in ('FW_E','FW_W'):
            self.assertEqual(result['probe_selection'][owner]['dimension'], 5)
            for ramp in self.follower._local_freeway_models[owner].owned_ramps:
                observed = field['holder_values']['metering_marginal_price'][ramp]
                self.assertAlmostEqual(observed, self.truth[owner][ramp], places=12)
                self.assertTrue(any(a.ramp_metering[ramp] < 100. for a in self.calls))
        self.assertTrue(all(0. <= v <= 100. for a in self.calls for v in a.ramp_metering.values()))
        self.assertTrue(all(row['rank'] == row['dimension'] for row in result['probe_selection'].values()))

    def test_missing_independent_coordinate_is_not_declared_zero_gradient(self):
        self.domains['FW_E'] = self.domains['FW_E'][:-1]
        with self.assertRaisesRegex(ValueError, 'do not span'):
            self.evaluate()
        self.assertFalse(self.calls)

    def test_deadline_stops_before_price_endpoint_batch(self):
        def check(stage):
            if stage == 'price_endpoints':
                raise TimeoutError('decision time exhausted')
        with self.assertRaisesRegex(TimeoutError, 'decision time exhausted'):
            self.evaluate(check_budget=check)
        self.assertFalse(self.calls)

    def test_short_response_batch_is_failure(self):
        def truncated(actions):
            return {'results': self.responses(actions)['results'][:-1]}
        with self.assertRaisesRegex(ValueError, 'Incomplete price response batch'):
            self.evaluate(response_query=truncated)


if __name__ == '__main__':
    unittest.main()
