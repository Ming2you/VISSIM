"""K8 fresh-process prediction on a captured SDMPC request template (termcost tc_worker pattern, H = 3 blocks).

    python -B worker.py <job.pickle> <result.pickle>

job = {template, action: 'REFERENCE' | {'meters': {ramp: green}}, mode: 'scalar' | 'ad' | 'ad_full', patches: [..]}
mode ad_full (K8-0b): non-surrogate reverse AD (scalar witness + tangent + full state_error, sdmpc_tangent_worker
  default path); the two diagnostic-only options central_multiplier / prediction_hotpath are switched off in this
  process only (they require the surrogate worker; model arithmetic unchanged; amend1/s1 S1_OWNER §5 recipe).
patches (scratch, compiled from the method's own source text in the code root with one-line edits, run through the same
tangent AST transform when the module was transformed; nothing on disk is edited):
  own_off (K8-0c) S1-OWN updates switched off in this process only (gate (h): I-5 check, not a runtime key): the
      six site entry points of evaluation.controllers.meter_spill become no-ops, so no meter_spill entry is ever
      created; S1 itself, the ledger and the Omega partition code are those of the code root
  s1  PhysicalRampBoundary.current_admission_space / finish_interval: admission space limited to the pre-head
      compartment  min(total free, head_pos*lanes/spacing - (upstream travelling + head ready))  (head_pos 0: unchanged)
  s3  zero-mass transfer keeps an active derivative: `if served/admitted/amount:` -> has_transfer(x), and
      ModelAreaLedger.transfer no early return for a zero-primal Dual
Summary: block-end stocks (ramps, ramp buffers, ramp-feeding movement queues, ledger), Omega costs, objective.
K8-0c records (reads only): summary.blocks[k].meter_spill = the candidate ledger's S1-OWN spill E[ramp][feeder]
  (primal; {} when the ledger has no entry), summary.omega_calls = per sdmpc.omega_costs call the partition's
  meter_spill_veh_h (None when absent), owner costs, total and ledger TTT; result['axes'] / result['costs_order'] =
  the request's decision axes (owner, kind, key, block, scale) and owner order.
K8-0b passive records: result['kind_service'] = per call of area_leader_objective.shared_urban_quantities, the
  owner signals' accepted_event_count and net_inflow_veh primal (reads only; the call itself is unchanged);
  result['trace'] = the worker's trace metadata (event counts, discrete/tie axes).
Code root: env K8G_ROOT (set by jobs.py through k8common.base_env), else this worktree (k8_gates/../../..).
"""
import copy
import hashlib
import inspect
import os
import pickle
import sys
import textwrap
import time
import traceback
from pathlib import Path

if len(sys.argv) < 3 or sys.argv[1] in ('-h', '--help'):
    print(__doc__)
    raise SystemExit(0 if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help') else 2)
R = Path(os.environ.get('K8G_ROOT') or Path(__file__).resolve().parents[3]).resolve()
sys.path[0] = str(R / 'evaluation' / 'controllers')
sys.path[:0] = [str(R), str(R / 'vendor/NumSim-mine')]
import importlib.abc  # noqa: E402

SUMMARY = {}
PATCHED = []


def _f(x):
    return float(getattr(x, 'value', x))


class Post(importlib.abc.MetaPathFinder):
    def __init__(self, callbacks):
        self.callbacks = dict(callbacks)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.callbacks:
            return None
        idx = sys.meta_path.index(self)
        for f in sys.meta_path[idx + 1:]:
            fs = getattr(f, 'find_spec', None)
            spec = fs(fullname, path, target) if fs else None
            if spec is not None:
                break
        else:
            return None
        orig = spec.loader.exec_module
        cb = self.callbacks[fullname]

        def exec_module(module):
            orig(module)
            cb(module)
        spec.loader.exec_module = exec_module
        return spec


def replace_method(module, cls, name, edits):
    fn = getattr(cls, name) if cls is not None else getattr(module, name)
    src = inspect.getsource(fn)
    for old, new in edits:
        if src.count(old) != 1:
            raise RuntimeError(f'patch anchor not unique in {name}: {old!r}')
        src = src.replace(old, new)
    src = textwrap.dedent(src)
    tree = __import__('ast').parse(src)
    if '_tangent_min' in module.__dict__:
        from evaluation.controllers.sdmpc_tangent_runtime import Transform
        tree = Transform().visit(tree)
    code = compile(__import__('ast').fix_missing_locations(tree), f'<k8:{name}>', 'exec')
    ns = module.__dict__
    exec(code, ns)
    new = ns.pop(fn.__name__) if cls is not None else ns[fn.__name__]
    if cls is not None:
        setattr(cls, name, new)
    PATCHED.append(f'{getattr(cls, "__name__", module.__name__)}.{name}')


HAS = ("(lambda _v: bool(getattr(_v, 'value', _v)) or bool(getattr(_v, 'node', 0)) "
       "or bool(getattr(_v, 'tangent', None)))")


def patch_prb(module, patches):
    cls = module.PhysicalRampBoundary
    edits = {}
    if 's1' in patches:
        def _k8_admission_space_veh(self):
            stocks = self._stocks()
            total_free = max(0.0, self.capacity_veh - stocks['connector_veh'])
            if self.head_position_m == 0:
                return total_free
            prehead_capacity = self.head_position_m * self.lanes / self.spacing_m
            prehead_stock = stocks['upstream_travelling_veh'] + stocks['head_ready_veh']
            return min(total_free, max(0.0, prehead_capacity - prehead_stock))
        if '_tangent_min' in module.__dict__:
            src = textwrap.dedent(inspect.getsource(_k8_admission_space_veh))
            from evaluation.controllers.sdmpc_tangent_runtime import Transform
            import ast
            tree = Transform().visit(ast.parse(src))
            exec(compile(ast.fix_missing_locations(tree), '<k8:admission>', 'exec'), module.__dict__)
            cls._admission_space_veh = module.__dict__.pop('_k8_admission_space_veh')
        else:
            cls._admission_space_veh = _k8_admission_space_veh
        edits.setdefault('finish_interval', []).append(
            ('free = max(0.0, self.capacity_veh-self._stocks()["connector_veh"])', 'free = self._admission_space_veh()'))
        edits.setdefault('current_admission_space', []).append(
            ("return max(0., self.capacity_veh-self._stocks()['connector_veh'])", 'return self._admission_space_veh()'))
    if 's3' in patches:
        edits.setdefault('apply_head_service', []).append(('        if served:\n', f'        if {HAS}(served):\n'))
        edits.setdefault('finish_interval', []).append(('        if admitted:\n', f'        if {HAS}(admitted):\n'))
        edits.setdefault('admit_current', []).append(('        if amount:\n', f'        if {HAS}(amount):\n'))
    for name, e in edits.items():
        replace_method(module, cls, name, e)


def patch_afa(module, patches):
    if 's3f' in patches:
        replace_method(module, None, '_freeway_substep_events', [
            ('receiving_for_mainline = [max(0.0, receiving[i] - max(0.0, ramp_in_by_link[link][i])) for i in range(len(rho_for_flow))]',
             'receiving_for_mainline = [max(0.0, receiving[i] - ramp_in_by_link[link][i]) for i in range(len(rho_for_flow))]'),
            ('            if delta_m > 0.0 and ramp_in_by_link[link][i] > 0.0:\n',
             f'            if delta_m > 0.0 and {HAS}(ramp_in_by_link[link][i]):\n')])


def patch_cao(module, patches):
    if 's3' in patches:
        replace_method(module, module.ModelAreaLedger, 'transfer', [
            ('        if count == 0:\n',
             "        if count == 0 and not getattr(count, 'node', 0) and not getattr(count, 'tangent', None):\n")])


def ramp_buffer_row(b):
    lanes = getattr(b, '_lane_buffers', None) or [b]
    up = sum(_f(n) for x in lanes for _, n in x._upstream)
    head = sum(_f(x._head_ready) for x in lanes)
    down = sum(_f(n) for x in lanes for _, n in x._downstream)
    ready = sum(_f(x._merge_ready) for x in lanes)
    pre_cap = (b.head_position_m * b.lanes / b.spacing_m) if b.head_position_m else None
    over = sum(max(0.0, (sum(_f(n) for _, n in x._upstream) + _f(x._head_ready)) - x.head_position_m * x.lanes / x.spacing_m)
               for x in lanes) if b.head_position_m else 0.0
    return dict(up=up, head=head, down=down, ready=ready, total=up + head + down + ready, capacity=float(b.capacity_veh),
                prehead_capacity=pre_cap, prehead_over=over)


def summarize_state(s, cfg):
    from evaluation.controllers.control_area_objective import get_ledger
    net = cfg.network
    L = get_ledger(s)
    feeding = {}
    for m, spec in (net.urban_movements or {}).items():
        r = str(spec.get('ramp', '') or '')
        if r:
            feeding[r] = feeding.get(r, 0.0) + _f(s.urban_movement_queue.get(m, 0.0))
    rr = getattr(s, 'lane_ramp_runtime', None)
    return dict(time_sec=_f(s.time_sec), ledger_ttt=_f(L.ttt_veh_h) if L else None,
                ramp_queue={k: _f(v) for k, v in s.ramp_queue.items()},
                ramp_buffers={k: ramp_buffer_row(b) for k, b in (rr.buffers.items() if rr else [])},
                ramp_feeding_movement_queue=feeding,
                movement_queue_total=sum(_f(v) for v in s.urban_movement_queue.values()),
                movement_queue={k: _f(v) for k, v in s.urban_movement_queue.items()},
                storage_available={k: _f(v) for k, v in s.urban_link_storage.items()},
                storage_available_total=sum(_f(v) for v in s.urban_link_storage.values()),
                origin_queue={k: _f(v) for k, v in s.mainline_origin_queue.items()},
                arrival_buffer_total=sum(_f(n) for d in s.urban_arrival_buffer.values() for n in d.values()),
                meter_spill={r: {f: _f(v) for f, v in by.items()}
                             for r, by in ((getattr(L, 'meter_spill', None) or {}).items() if L else [])})


KIND_SERVICE = []


def patch_alo(module):
    original = module.shared_urban_quantities

    def shared_urban_quantities(*args, **kwargs):
        out = original(*args, **kwargs)
        try:
            KIND_SERVICE.append({sig: {'accepted_event_count': row.get('accepted_event_count'),
                                       'net_inflow_veh': _f(row.get('net_inflow_veh', 0.0))}
                                 for sig, row in (out.get('owners') or {}).items()})
        except Exception as exc:  # passive record only
            KIND_SERVICE.append({'record_error': repr(exc)[:200]})
        return out
    module.shared_urban_quantities = shared_urban_quantities


def patch_sdmpc(module):
    original = module.omega_costs

    def omega_costs(point, cfg):
        out = original(point, cfg)
        try:
            part = out[1]
            SUMMARY.setdefault('omega_calls', []).append(dict(
                meter_spill_veh_h=part.get('meter_spill_veh_h'),
                costs={k: _f(v) for k, v in part['costs'].items()}, total=_f(part['total_veh_h']),
                ledger_ttt=_f(point.control_area['ttt_veh_h'])))
        except Exception as exc:  # passive record only
            SUMMARY.setdefault('omega_calls', []).append({'record_error': repr(exc)[:200]})
        if 'blocks' not in SUMMARY:
            SUMMARY['blocks'] = [summarize_state(s, cfg) for s in point.states]
            SUMMARY['objective'] = _f(point.objective)
        return out
    module.omega_costs = omega_costs


OWN_SITES = ('movement_virtual', 'movement_commit', 'shared_branch', 'sc2001_branches', 'legsplit_request',
             'legsplit_accepted')


def patch_meter_spill(module, patches):
    """own_off (K8-0c, gate (h)): the S1-OWN site entry points become no-ops in this process."""
    if 'own_off' not in patches:
        return
    for name in OWN_SITES:
        if not callable(getattr(module, name, None)):
            raise RuntimeError('own_off: meter_spill has no site entry point ' + name)
        setattr(module, name, lambda *args, **kwargs: None)
    PATCHED.append('meter_spill.' + ','.join(OWN_SITES) + ':noop')


def main():
    job_path, result_path = sys.argv[1:3]
    started = time.perf_counter()
    result = {'job': job_path}
    try:
        from evaluation.controllers.sdmpc_tangent_runtime import install
        job = pickle.loads(Path(job_path).read_bytes())
        patches = set(job.get('patches', ()))
        finder = install(R, 'reverse-v1')
        sys.meta_path.insert(0, Post({
            'evaluation.controllers.physical_ramp_boundary': lambda m: patch_prb(m, patches),
            'evaluation.controllers.control_area_objective': lambda m: patch_cao(m, patches),
            'evaluation.controllers.area_freeway_accounting': lambda m: patch_afa(m, patches),
            'evaluation.controllers.area_leader_objective': patch_alo,
            'evaluation.controllers.meter_spill': lambda m: patch_meter_spill(m, patches),
            'evaluation.controllers.sdmpc': patch_sdmpc}))
        from evaluation.controllers import sdmpc_tangent_worker as standard
        request = pickle.loads(Path(job['template']).read_bytes())
        follower, state, reference, forecast = request['owned']
        action = job['action']
        if action == 'REFERENCE':
            action = reference.copy()
        else:
            spec = action
            action = reference.copy()
            from evaluation.controllers.sdmpc_continuous import meter_rate
            rows = follower.cfg.network.physical_ramp_branches['ramps']
            for ramp, g in (spec.get('meters') or {}).items():
                action.diagnostics['rw_meter_green_' + ramp] = float(g)
                action.ramp_metering[ramp] = meter_rate(float(g), rows[ramp])
        request['action'] = copy.deepcopy(action)
        if job.get('mode') == 'ad_full':
            opts = follower.cfg.network.sdmpc_options
            opts['central_multiplier'] = False
            opts['prediction_hotpath'] = False
        else:
            request['surrogate_evaluation'] = job.get('mode', 'scalar')
            from evaluation.controllers.sdmpc_tangent_surrogate import token
            request['surrogate_context_sha256'] = token((request['owned'], request['runtime'], request['bootstrap'],
                                                         request['horizon']))
        out = standard.run(request, finder, result)
        result['out_keys'] = sorted(out.keys())
        result['costs'] = [_f(x) for x in out.get('costs', [])]
        sp = out.get('surrogate_prediction') or {}
        result['objective_veh_h'] = sp.get('objective_veh_h')
        for k in ('cost_jacobian', 'resource_jacobian', 'ad_axes', 'fallback_reasons', 'resources',
                  'max_primal_state_error', 'complete_primal_state_match', 'scalar_rollouts', 'tangent_rollouts',
                  'trace', 'transformed_source_sha256', 'scalar_sec', 'tangent_sec', 'reverse_sec'):
            if k in out:
                result[k] = out[k]
        result['surrogate_keys'] = sorted(sp.keys()) if isinstance(sp, dict) else None
        if isinstance(sp, dict):
            for k in ('gradient', 'objective_gradient', 'cost_gradients', 'costs', 'resources', 'jacobian'):
                if k in sp:
                    result['sp_' + k] = sp[k]
        result['summary'] = dict(SUMMARY)
        result['axes'] = [dict(owner=a['owner'], kind=a['kind'], key=a['key'], block=a.get('block', 0),
                               scale=a.get('scale')) for a in request['axes']]
        result['costs_order'] = list(request['costs_order'])
    except Exception:
        result['error'] = traceback.format_exc()
    result['patched'] = PATCHED
    result['kind_service'] = KIND_SERVICE
    result['wall_sec'] = time.perf_counter() - started
    Path(result_path).write_bytes(pickle.dumps(result, protocol=5))
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
