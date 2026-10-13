"""Opt-in continuous prediction reuse. Never claims exact actuator dynamics.

An AD trajectory supplies both the candidate response and its next Jacobian.
Scalar candidates use the identical continuous actuator model. No independent
scalar AD witness runs in this mode; that omission is explicit in receipts.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import math
import pickle
import time

from evaluation.controllers.sdmpc_dual import Dual

MODEL = 'continuous-signal-and-cycle-mean-meter/v1'


def token(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def plain(value):
    if isinstance(value, Dual):
        return plain(float(value.value))
    if isinstance(value, dict):
        return {key: plain(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(plain(child) for child in value)
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Nonfinite surrogate response')
        return value
    raise TypeError('Unsupported surrogate summary field: '+type(value).__name__)


def prediction(point, initial, action, local, partition, quantities, context_token):
    """Export only already-computed primal summaries; never a second rollout."""
    response = point.control_area_response
    allocations = response['resource_allocations']
    streamed = response.get('streamed_model_checks')
    if streamed is not None and (streamed.get('original_checks_performed') is not True
            or streamed.get('successful_records_retained') is not False
            or allocations or response['state_bounds']):
        raise ValueError('Invalid streamed model-check summary')
    result = plain(dict(objective_veh_h=point.objective,
        local_base_costs={owner: row['cost'] for owner, row in local.items()},
        local_costs=local, quantities=quantities, control_area=point.control_area,
        action_token=token(action), frozen_context_token=context_token,
        price_or_quantity_terms_included=False, shared_capacity_certificate=False,
        model_constraint_coverage=response.get('model_constraint_coverage'),
        conditional_model_feasibility_witness=response.get('conditional_model_feasibility_witness', False),
        native_prehead_reference_overdraw_veh=(
            getattr(point.states[-1], 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)
            - getattr(initial, 'native_input_prehead_state', {}).get('existing_wn_budget_overdraw_veh', 0.)),
        native_prehead_limit_scope='Existing prehead mismatch; no native feasibility certificate',
        resource_summary=(streamed['allocation_summary'] if streamed is not None else
            dict(count=len(allocations), kinds=dict(Counter(row['kind'] for row in allocations)),
                max_exceedance_veh=max((plain(row['exceedance_veh']) for row in allocations), default=0.))),
        sdmpc_omega_partition=partition, prediction_model=MODEL,
        execution_model_evaluated=False, native_applied=False,
        response_token_scope='Digest of continuous candidate summary, not exact execution-model ledger'))
    if streamed is not None:
        result['streamed_model_checks']=plain(streamed)
    result['response_token'] = token(result)
    return result


def validate_prediction(item, action, context_token):
    if (item.get('prediction_model') != MODEL or item.get('execution_model_evaluated') is not False
            or item.get('action_token') != token(action)
            or item.get('frozen_context_token') != context_token):
        raise ValueError('Surrogate response context/model mismatch')
    raw = dict(item); observed = raw.pop('response_token', None)
    if token(raw) != observed:
        raise ValueError('Surrogate response digest mismatch')
    warm = raw.pop('warm_budget_binding', None)
    if warm is not None:
        source, init = warm['source_action'], warm['initialization']
        raw['action_token'] = token(source)
        if (warm.get('schema') != 'sdmpc-pfo-budget-binding/v2'
                or init.get('schema') != 'decision-pfo-budget-initialization/v2'
                or init['reference_action_token'] != token(source)
                or init['reference_response_token'] != token(raw)
                or init['frozen_context_token'] != context_token):
            raise ValueError('Invalid PFO budget source proof')
        np_margin, nuf_margin = init['np_cap_margin_veh'], init['nuf_cap_margin_veh_h']
        if any(type(m) is not float or not math.isfinite(m) or m < 0 for m in (np_margin, nuf_margin)):
            raise ValueError('Invalid PFO budget margin')
        expected = copy.deepcopy(source)
        q = raw['quantities']
        achieved_np = math.fsum(q['owners'][s]['net_inflow_veh'] for s in sorted(q['owners']))
        achieved_nuf = math.fsum(q['predicted_ramp_merge']['rate_veh_h_by_ramp'].values())
        expected.N_P_star, expected.N_UF_star = achieved_np+np_margin, achieved_nuf+nuf_margin
        if (achieved_np != init['achieved_np_veh'] or achieved_nuf != init['achieved_nuf_veh_h']
                or token(expected) != token(action) or expected.N_P_star != init['np_cap_veh']
                or expected.N_UF_star != init['nuf_cap_veh_h']):
            raise ValueError('PFO budget binding changed physical inputs, achieved quantities or margins')
    binding = raw.pop('initial_target_binding', None)
    if binding is not None:
        source = binding['source_action']
        init = binding['initialization']
        raw['action_token'] = token(source)
        if (binding.get('schema') != 'sdmpc-initial-target-binding/v1'
                or init['reference_action_token'] != token(source)
                or init['reference_response_token'] != token(raw)
                or init['frozen_context_token'] != context_token
                or init['previous_target_veh_h'] != source.N_UF_star):
            raise ValueError('Invalid initial target source proof')
        expected = copy.deepcopy(source)
        expected.N_UF_star = math.fsum(init['accepted_rate_veh_h_by_ramp'].values())
        if token(expected) != token(action) or expected.N_UF_star != init['target_veh_h']:
            raise ValueError('Initial binding changed more than the derived merge target')


class Query:
    """NP-only cache plus an opt-in, proved initial merge-target binding."""
    def __init__(self, template, check_budget, emit, runner=None):
        from evaluation.controllers.sdmpc_tangent import _evaluate_single
        self.template = pickle.dumps(template, protocol=5)
        self.context_token = token((template['owned'], template['runtime'], template['bootstrap'], template['horizon']))
        self.runner = runner or _evaluate_single
        self.check_budget, self.emit = check_budget, emit
        self.entries = {}
        self.requests = self.hits = self.scalar = self.ad = 0
        self.derivative_hits = 0
        self.failed_batches = self.failed_predictions_unknown = 0
        self.closed = False
        self.rows = []
        self.initial_binding = None
        self.warm_binding = None

    def bind_warm_budget(self, source, target, options):
        """Reuse the selected PFO trajectory only after proving both budgets.

        Ordinary cache identity still includes NUF. This one initialization
        cannot rebind an arbitrary search target or another physical control.
        """
        from evaluation.controllers import sdmpc_budget
        from evaluation.controllers.sdmpc_response_cache import physical_key
        request = pickle.loads(self.template)
        follower, state, _, _ = request['owned']
        policy = follower.cfg.network.sdmpc_options
        if (self.closed or self.warm_binding is not None or self.initial_binding is not None
                or not policy.get('pfo_each_interval') or not policy.get('budget_caps')
                or getattr(state, 'lane_freeway_runtime', None) is None):
            raise ValueError('PFO binding requires this interval\'s enabled lane predictor')
        stored, item, receipt = self.entries[physical_key(source)]
        if token(stored) != token(source) or receipt is None:
            raise ValueError('PFO binding requires its exact scored derivative')
        validate_prediction(item, source, self.context_token)
        expected, initialization = sdmpc_budget.initialize(follower,state,source,item,options)
        if token(expected) != token(target):
            raise ValueError('PFO target differs from its achieved-plus-margin budgets')
        binding = dict(schema='sdmpc-pfo-budget-binding/v2',source_action=copy.deepcopy(source),
            initialization=initialization,scope='Only constraint budgets (PFO-achieved + configured margin) change; physical trajectory unchanged')
        derived = copy.deepcopy(item); derived.pop('response_token')
        derived.update(action_token=token(target),warm_budget_binding=binding)
        derived['response_token'] = token(derived)
        validate_prediction(derived,target,self.context_token)
        self.entries[physical_key(target)] = (copy.deepcopy(target),derived,receipt)
        self.warm_binding = binding

    def bind_initial_target(self, source, target):
        """Consume the entry AD once; do not relax ordinary NUF cache identity.

        In the lane continuous predictor, box_walk=False and actual meter greens
        drive traffic. NUF is only the quantity-constraint target. Preserve the
        original response digest and record a separately hashed derived summary.
        """
        from evaluation.controllers import area_follower_objective as joint
        from evaluation.controllers.sdmpc_response_cache import physical_key
        from evaluation.controllers.sdmpc_sequence import KEY
        request = pickle.loads(self.template)
        follower, state, reference, _ = request['owned']
        policy = follower.cfg.network.sdmpc_options
        if (self.closed or self.initial_binding is not None or len(self.rows) != 1
                or not policy.get('initial_shared_prediction') or not policy.get('surrogate_reuse')
                or getattr(state, 'lane_freeway_runtime', None) is None
                or not getattr(follower.cfg.network, 'physical_ramp_branches', None)
                or token(source) != token(reference) or KEY in source.diagnostics):
            raise ValueError('Initial target reuse requires the first lane-model reference AD')
        stored, item, receipt = self.entries[physical_key(source)]
        if receipt is None or token(stored) != token(source):
            raise ValueError('Initial target reuse requires the exact reference derivative')
        validate_prediction(item, source, self.context_token)
        expected, initialization = joint.initialize_decision_nuf(follower, state, source, item)
        if token(expected) != token(target):
            raise ValueError('Initial target differs from actual-command merge forecast')
        binding = dict(schema='sdmpc-initial-target-binding/v1',
            source_action=copy.deepcopy(source), initialization=initialization,
            scope='NUF-only initial constraint target; physical inputs and AD trajectory unchanged')
        derived = copy.deepcopy(item)
        derived.pop('response_token')
        derived.update(action_token=token(target), initial_target_binding=binding)
        derived['response_token'] = token(derived)
        validate_prediction(derived, target, self.context_token)
        self.entries[physical_key(target)] = (copy.deepcopy(target), derived, receipt)
        self.initial_binding = copy.deepcopy(binding)

    def evaluate(self, actions, *, derivatives=False):
        from evaluation.controllers.sdmpc_response_cache import physical_key
        if self.closed:
            raise ValueError('Closed surrogate query')
        actions = tuple(actions)
        missing = {}
        for action in actions:
            key = physical_key(action)
            stored = self.entries.get(key)
            if stored is None or (derivatives and stored[2] is None):
                missing.setdefault(key, action)
        count = len(missing)
        slots = min(8, count) if count else 0
        reverse_workers = max(1, 8//slots) if slots else 8
        def execute(pair):
            key, action = pair
            self.check_budget('sdmpc_surrogate_prediction')
            request = pickle.loads(self.template)
            request['action'] = copy.deepcopy(action)
            request['surrogate_evaluation'] = 'ad' if derivatives else 'scalar'
            request['surrogate_context_sha256'] = self.context_token
            if derivatives and reverse_workers < 8:
                request['reverse_worker_limit'] = reverse_workers
            result = self.runner(request)
            item = result['surrogate_prediction']
            validate_prediction(item, action, self.context_token)
            if result.get('primal_audit_performed') is not False:
                raise ValueError('Unexpected surrogate audit receipt')
            expected = (0, 1) if derivatives else (1, 0)
            if (result.get('scalar_rollouts'), result.get('tangent_rollouts')) != expected:
                raise ValueError('Surrogate rollout accounting mismatch')
            if derivatives and (result.get('fallback_reasons') or len(result.get('ad_axes', ())) != len(request['axes'])):
                raise ValueError('Incomplete surrogate Jacobian')
            return key, (copy.deepcopy(action), item, result if derivatives else None), result
        if missing:
            self.emit('sdmpc_surrogate_batch_start', predictions=count, derivative_predictions=derivatives,
                      prediction_workers=slots, reverse_workers_per_prediction=reverse_workers)
            started = time.perf_counter()
            try:
                with ThreadPoolExecutor(max_workers=slots) as pool:
                    completed = list(pool.map(execute, missing.items()))
            except BaseException:
                self.failed_batches += 1
                self.failed_predictions_unknown += count
                raise
            # Publish only a complete successful batch. Errors are never cached.
            for key, entry, receipt in completed:
                self.entries[key] = entry
                self.scalar += receipt['scalar_rollouts']; self.ad += receipt['tangent_rollouts']
                self.rows.append(dict(action_token=token(entry[0]), derivatives=derivatives,
                    scalar_rollouts=receipt['scalar_rollouts'], tangent_rollouts=receipt['tangent_rollouts'],
                    wall_sec=receipt['wall_sec_including_spawn'], consumed_derivative=False))
            self.emit('sdmpc_surrogate_batch_done', predictions=count, seconds=time.perf_counter()-started)
        self.requests += len(actions); self.hits += len(actions)-count
        return [self._response(action) for action in actions]

    def _response(self, action):
        from evaluation.controllers.sdmpc_response_cache import physical_key, validate_binding
        source, item, _ = self.entries[physical_key(action)]
        item = copy.deepcopy(item)
        validate_prediction(item, source, self.context_token)
        if token(source) != token(action):
            proof = dict(schema='sdmpc-np-cap-response-binding/v1', physical_key=physical_key(action),
                evaluated_action=copy.deepcopy(source), evaluated_action_token=token(source),
                requested_action_token=token(action), evaluated_response_token=item['response_token'],
                frozen_context_token=self.context_token,
                scope='NP-only reuse of a continuous-model trajectory; constraints rechecked for this cap')
            item['action_token'] = token(action); item['sdmpc_physical_response_reuse'] = proof
            validate_binding(action, item)
        return item

    def derivative(self, action):
        from evaluation.controllers.sdmpc_response_cache import physical_key
        key = physical_key(action)
        if key not in self.entries or self.entries[key][2] is None:
            self.evaluate([action], derivatives=True)
        source, _, receipt = self.entries[key]
        ad_source_token = receipt['surrogate_prediction']['action_token']
        self.derivative_hits += 1
        for row in self.rows:
            if row['action_token'] == ad_source_token and row['derivatives']:
                row['consumed_derivative'] = True
        # The central state Jacobian is a ~5169 x 231 list of lists; deep-copying it took
        # ~0.45 s per call, six calls a decision. Every consumer only reads it:
        # sdmpc_central.recover extends a local list and immediately copies it into a
        # fresh ndarray (np.asarray(rows)), and the metadata writers serialize it. So it is
        # shared with the cached receipt instead of copied; everything else still is.
        central = receipt.get('central_physical')
        shared = central.get('jacobian') if isinstance(central, dict) else None
        result = copy.deepcopy(receipt, {id(shared): shared} if isinstance(shared, list) else None)
        result['candidate_prediction_reused'] = dict(source_action_token=ad_source_token,
            requested_action_token=token(action), physical_inputs_exact=True, prediction_model=MODEL)
        if ad_source_token != token(source):
            if self.warm_binding is not None:
                result['candidate_prediction_reused']['warm_budget_binding'] = copy.deepcopy(self.warm_binding)
            else:
                result['candidate_prediction_reused']['initial_target_binding'] = copy.deepcopy(self.initial_binding)
        return result

    def close(self):
        self.closed = True

    def stats(self):
        return dict(schema='sdmpc-continuous-response-reuse/v1', prediction_model=MODEL,
            requests=self.requests, cache_hits=self.hits, scalar_rollouts=self.scalar,
            tangent_rollouts=self.ad, total_rollouts=self.scalar+self.ad,
            endpoint_calls=self.scalar+self.ad, derivative_cache_uses=self.derivative_hits,
            unused_ad_predictions=sum(row['derivatives'] and not row['consumed_derivative'] for row in self.rows),
            independent_ad_witness_rollouts=0, exact_execution_rollouts=0, rows=self.rows,
            initial_target_binding=copy.deepcopy(self.initial_binding),
            initial_scalar_rollouts_removed=int(self.initial_binding is not None),
            **({'warm_budget_binding':copy.deepcopy(self.warm_binding),
                'pfo_to_sdmpc_extra_rollouts':0} if self.warm_binding is not None else {}),
            failed_batches=self.failed_batches, failed_predictions_with_unknown_rollout_count=self.failed_predictions_unknown,
            owned_workers_alive=[], closed=self.closed,
            scope='Approximate-model predictions only; physical command checks remain separate')
