"""Decision-local physical-response reuse across NP caps, with explicit binding.

Only NP cap fields are removed from the key. NUF, all actuator fields, all
diagnostics and every future control stay exact. The original response hash
continues to identify its evaluated action; an alias never claims a new rollout.
Candidate-specific quantity feasibility must be recomputed by the caller.
"""
import copy
import hashlib
import pickle


def token(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def physical_key(action):
    from evaluation.controllers import sdmpc_sequence as sequence
    control = copy.deepcopy(action)
    control.N_P_star = 0.
    if sequence.KEY in control.diagnostics:
        sequence.actions(control, 3)
        for row in control.diagnostics[sequence.KEY]['future']:
            row['N_P_star'] = 0.
    return token(control)


def validate_binding(action, item):
    """Check a bound alias without mislabelling its source response identity."""
    proof = item.get('sdmpc_physical_response_reuse')
    if proof is None:
        if item.get('action_token') != token(action):
            raise ValueError('Response/action mismatch')
        return
    source = proof['evaluated_action']
    if (proof.get('schema') != 'sdmpc-np-cap-response-binding/v1'
            or proof['requested_action_token'] != token(action)
            or item.get('action_token') != proof['requested_action_token']
            or proof['evaluated_action_token'] != token(source)
            or physical_key(action) != physical_key(source)
            or proof['physical_key'] != physical_key(action)
            or item['response_token'] != proof['evaluated_response_token']
            or item['frozen_context_token'] != proof['frozen_context_token']
            or item.get('price_or_quantity_terms_included') is not False):
        raise ValueError('Invalid NP-only physical response binding')


class ResponseCache:
    def __init__(self, query, cfg):
        if (not getattr(cfg.network, 'physical_ramp_branches', None)
                or not getattr(cfg.network, 'control_area_enabled', False)
                or not getattr(cfg.network, 'sdmpc_options', {}).get('response_np_cache')):
            raise ValueError('NP response reuse requires explicit physical-ramp SDMPC mode')
        self.query = query
        self.entries = {}
        self.context_token = None
        self.requests = self.misses = self.hits = 0
        self.reuse = []

    def __call__(self, actions):
        actions = tuple(actions)
        keys = [physical_key(a) for a in actions]
        missing = {}
        for key, action in zip(keys, actions):
            if key not in self.entries and key not in missing:
                missing[key] = action
        if missing:
            batch = self.query(tuple(missing.values()))['results']
            if len(batch) != len(missing):
                raise ValueError('Incomplete response cache batch')
            pending = {}
            for (key, action), item in zip(missing.items(), batch):
                validate_binding(action, item)
                if (item.get('price_or_quantity_terms_included') is not False
                        or 'sdmpc_physical_response_reuse' in item):
                    raise ValueError('Physical cache requires original pure response evidence')
                if self.context_token is None:
                    self.context_token = item['frozen_context_token']
                if item['frozen_context_token'] != self.context_token:
                    raise ValueError('Physical cache crossed frozen prediction contexts')
                pending[key] = pickle.dumps((action, item), protocol=5)
            self.entries.update(pending)
        result = []
        for key, action in zip(keys, actions):
            source, item = pickle.loads(self.entries[key])
            validate_binding(source, item)
            requested = token(action)
            if requested != item['action_token']:
                proof = dict(schema='sdmpc-np-cap-response-binding/v1',
                    physical_key=key, evaluated_action=source,
                    evaluated_action_token=item['action_token'],
                    requested_action_token=requested,
                    evaluated_response_token=item['response_token'],
                    frozen_context_token=item['frozen_context_token'],
                    scope='NP-only alias of an evaluated physical trajectory; quantity constraints are checked anew')
                item['action_token'] = requested
                item['sdmpc_physical_response_reuse'] = proof
                validate_binding(action, item)
                self.reuse.append({k: v for k, v in proof.items() if k != 'evaluated_action'})
            result.append(item)
        self.requests += len(actions)
        self.misses += len(missing)
        self.hits += len(actions)-len(missing)
        return result

    def stats(self):
        return dict(requests=self.requests, unique_physical_predictions=self.misses,
                    reused_predictions=self.hits, bindings=self.reuse)
