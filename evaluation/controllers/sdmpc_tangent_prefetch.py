"""Overlap a frozen initial Jacobian with the required held-action query.

The independent response is still evaluated under its exact action token.
The precomputed derivative can be consumed only by the identical full request.
This context joins its owned task on every exit, including failed hold queries.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import pickle
import time


class InitialDerivative:
    def __init__(self, request, evaluate):
        self.original=pickle.dumps(request,protocol=5)
        self.digest=hashlib.sha256(self.original).hexdigest()
        frozen=pickle.loads(self.original)
        workers=frozen['owned'][0].cfg.network.sdmpc_options['derivative_workers']
        if type(workers) is not int or not 3<=workers<=8:
            raise ValueError('Initial overlap needs 3..8 numerical workers')
        # One ordinary held-action prediction may still be active at sweep time.
        frozen['reverse_worker_limit']=workers-1
        self.payload=pickle.dumps(frozen,protocol=5)
        self.evaluate=evaluate
        self.consumed=False
        self.executor=None
        self.receipt=None

    def __enter__(self):
        self.started=time.perf_counter()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='sdmpc-initial-derivative')
        try:
            self.future=self.executor.submit(self._run)
        except BaseException:
            self.executor.shutdown(wait=True,cancel_futures=True)
            raise
        return self

    def _run(self):
        return self.evaluate(pickle.loads(self.payload))

    def consume(self, request):
        if self.consumed:
            raise ValueError('Initial derivative was already consumed')
        current=hashlib.sha256(pickle.dumps(request,protocol=5)).hexdigest()
        if current!=self.digest:
            raise ValueError('Prefetched derivative full request changed')
        wait_started=time.perf_counter()
        result=self.future.result()
        self.consumed=True
        self.receipt=dict(request_sha256=self.digest,full_request_exact=True,
            elapsed_since_start_sec=time.perf_counter()-self.started,
            waiting_after_hold_sec=time.perf_counter()-wait_started,
            reverse_workers=result.get('reverse_sweeps',{}).get('workers'),
            ordinary_hold_queries_skipped=0)
        result['initial_prediction_overlap']=self.receipt
        return result

    def __exit__(self, exc_type, exc_value, traceback):
        self.executor.shutdown(wait=True,cancel_futures=True)
        if exc_type is None and not self.consumed:
            self.future.result()
            raise ValueError('Prefetched derivative was not consumed')
        return False


class TrialDerivatives:
    """At most two speculative anchors alongside their original predictions.

    A batch owns at most eight numerical execution slots: each derivative has
    two primal processes followed by a limited reverse sweep; ordinary model
    predictions reserve one slot each throughout. Unselected work is joined,
    checked and reported, never counted as a selected/validated control action.
    """

    def __init__(self, requests, evaluate):
        if not 1 <= len(requests) <= 2:
            raise ValueError('Trial overlap supports one or two candidate anchors')
        self.evaluate = evaluate
        self.count = len(requests)
        self.reverse_workers = (8-self.count)//self.count
        self.digests, self.action_tokens, self.payloads = [], [], []
        for request in requests:
            original = pickle.dumps(request, protocol=5)
            frozen = pickle.loads(original)
            policy = frozen['owned'][0].cfg.network.sdmpc_options
            if (type(policy.get('derivative_workers')) is not int
                    or policy['derivative_workers'] != 8
                    or not policy.get('trial_derivative_overlap')):
                raise ValueError('Trial overlap requires explicit mode and eight workers')
            self.digests.append(hashlib.sha256(original).hexdigest())
            self.action_tokens.append(hashlib.sha256(pickle.dumps(request['action'], protocol=5)).hexdigest())
            frozen['reverse_worker_limit'] = self.reverse_workers
            self.payloads.append(pickle.dumps(frozen, protocol=5))
        if len(set(self.action_tokens)) != self.count:
            raise ValueError('Duplicate speculative action')
        self.consumed = set()
        self.futures = []
        self.closed = False
        self.receipt = dict(started_derivatives=self.count, consumed_derivatives=0,
            unused_derivatives=0, ordinary_prediction_slots=self.count,
            reverse_workers_per_derivative=self.reverse_workers,
            max_numerical_workers=self.count+self.count*max(2, self.reverse_workers),
            all_joined=False, unused_qualified=False, tasks=[])

    def __enter__(self):
        self.started = time.perf_counter()
        self.executor = ThreadPoolExecutor(max_workers=self.count,
            thread_name_prefix='sdmpc-trial-derivative')
        try:
            for payload in self.payloads:
                self.futures.append(self.executor.submit(self._run, payload))
        except BaseException:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.closed = True
            raise
        return self

    def _run(self, payload):
        return self.evaluate(pickle.loads(payload))

    def contains_action(self, action):
        digest = hashlib.sha256(pickle.dumps(action, protocol=5)).hexdigest()
        return digest in self.action_tokens

    def consume(self, request):
        digest = hashlib.sha256(pickle.dumps(request, protocol=5)).hexdigest()
        if digest not in self.digests:
            raise ValueError('Speculative derivative full request changed')
        index = self.digests.index(digest)
        if self.closed or index in self.consumed:
            raise ValueError('Speculative derivative was already consumed or closed')
        wait_started = time.perf_counter()
        result = self.futures[index].result()
        self.consumed.add(index)
        result['trial_prediction_overlap'] = dict(request_sha256=digest,
            full_request_exact=True, elapsed_since_start_sec=time.perf_counter()-self.started,
            waiting_after_trials_sec=time.perf_counter()-wait_started,
            reverse_workers=result.get('reverse_sweeps', {}).get('workers'),
            ordinary_trial_queries_skipped=0)
        return result

    def close(self, primary_error=False):
        if self.closed:
            return
        # Normal completion must also observe errors from not-yet-started,
        # unselected work. Cancellation is reserved for an existing failure.
        self.executor.shutdown(wait=True, cancel_futures=primary_error)
        self.closed = True
        self.receipt['all_joined'] = all(future.done() for future in self.futures)
        self.receipt['elapsed_sec'] = time.perf_counter()-self.started
        errors, rows = [], []
        for index, future in enumerate(self.futures):
            row = dict(request_sha256=self.digests[index], consumed=index in self.consumed)
            try:
                result = future.result()
                qualified = (result.get('complete_primal_state_match') is True
                    and not result.get('fallback_reasons') and 'error' not in result
                    and result.get('reverse_sweeps', {}).get('workers') == self.reverse_workers)
                if not qualified:
                    raise ValueError('Unqualified speculative derivative')
                row.update(qualified=True, wall_sec=result.get('wall_sec_including_spawn'))
            except BaseException as error:
                errors.append(error)
                row.update(qualified=False, error=repr(error))
            rows.append(row)
        self.receipt.update(tasks=rows, consumed_derivatives=len(self.consumed),
            unused_derivatives=self.count-len(self.consumed), unused_qualified=not errors)
        if errors and not primary_error:
            raise errors[0]

    def __exit__(self, exc_type, exc_value, traceback):
        self.close(primary_error=exc_type is not None)
        return False
