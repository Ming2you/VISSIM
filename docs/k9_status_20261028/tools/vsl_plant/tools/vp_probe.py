"""vsl_plant plant probe inside the deployed adapter process (PRE_VP.md sections 3-5).  No VISSIM, no COM, no action
file is written.  Scratch tool, never committed.

    python -B vp_probe.py <adapter.py> <the adapter's own argument list (k92_replay.py form)>
    env: VP_SPEC (spec JSON path), VP_OUT (output JSON path), VP_DEC (source decisions folder, read only),
         VP_HOOK_DIR (passive worker hook output folder; vp_hooks/sitecustomize.py)

It runs the adapter exactly as the VBS command line does (runpy __main__, sys.path[0] = the adapter folder, the
workspace root in front, as `python -B adapter.py`) and replaces evaluation.controllers.sdmpc.solve by probe_solve.
probe_solve repeats sdmpc.solve (FRZ_K92 sdmpc.py:536-592) up to the creation of the continuous surrogate Query
(`surrogate_reuse` is on in the V-A tuning), i.e. the same load_prices check, held reference, runtime callbacks,
decision shared query, sequence coordinates and prepare_request(follower, state, forecast, reference, reference,
coord, worker_bootstrap).  Every plant evaluation then goes through sdmpc_tangent_surrogate.Query.evaluate, whose
runner is sdmpc_tangent._evaluate_single (one isolated worker process per prediction) = the deployed worker path.
The probe wraps the runner only to record which worker request (sha256) belongs to which plan.

Plans (all three-block sdmpc-sequence/v1 plans):
  REC   = the recorded selected plan of decision T, rebuilt as the next decision would read it:
          held(action_T) as block 0 + the two recorded future blocks (sdmpc_prediction_sequence) -> sequence.pack.
          held(x) = control_from_json -> physical_ramp_branches.held_actual_reference -> expand_shared_vsl_action
          (the adapter's own segment_vsl_func) -> sequence.first_action -> area_meter_finalization.
          prepare_held_actual_reference  (vissim_stackelberg_adapter.py:13158-13180, sdmpc.py:556-568).
  REPACK = sequence.pack(sequence.actions(REC, 3)) (identity; checks that the arm path itself changes nothing).
  ARM v = REC with every FW_E__seg<k> key of zone head 10 (cells 10-14) set to v in all three blocks and the FW_E
          link key = min of the FW_E segment keys; nothing else changes.
  EXEC  = pack([held(action_T), held(action_{T+150}), held(action_{T+300})]) = the block-0 commands VISSIM actually
          ran in [T, T+450).
Checks written to the output (the caller applies the stop rules):
  R1  REC, AD mode (as recorded: the selected plan was scored by an AD rollout) -> objective within 1e-9 veh*h of
      action_T metadata.joint_leader_selection.selected_objective and every omega_partition cost within 1e-9 veh*h
      (PRE_VP_R3, user decision D-K9-108, data-after amendment r3; r2 = PRE_VP_FIXED section 3.4 required the
      objective bit-equal.  R1_objective_bit_equal is still written, report only).
  R2  REC, scalar mode -> recorded gap R2 - R1 (reported).
  R3  REPACK scalar == REC scalar (bit).  REPACK normally has the REC token, so Query.evaluate serves it from the
      same physical-key cache entry (one worker): R3 then checks the identity repack, not a second rollout.
  null ablation (P mode) scalar == EXEC scalar (bit; its own Query and worker, different request bytes).
Ablations (P mode; each on its own unpickled copy of the request template, own Query, EXEC plan, scalar):
  C1_vfree, C2_rhocrit, C3_merge, C4_lanedrop, C5_capdrop, C6_compliance, C7_initial, C8_antic18 (anticipation
  coefficient nu of the cell rows given, normally cell 18 = the cell before the 4 -> 3 lane drop), C9_lanedrop_both
  (C4 and C8 together) (PRE_VP_FIXED section 5.4).
"""
import copy
import json
import math
import os
import pickle
import runpy
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

OUT = Path(os.environ['VP_OUT'])
SPEC = json.loads(Path(os.environ['VP_SPEC']).read_text(encoding='utf-8'))
DEC = Path(os.environ['VP_DEC'])
ADAPTER = str(Path(sys.argv[1]).resolve())
sys.argv = [ADAPTER] + sys.argv[2:]
ROOT = str(Path(ADAPTER).parents[2])
sys.path[0] = str(Path(ADAPTER).parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
T0 = time.perf_counter()
OWNER = SPEC.get('owner', 'FW_E')
HEAD = int(SPEC.get('zone_head', 10))
CAP = {}
RUNS = []
RUNS_LOCK = threading.Lock()
PROGRESS = OUT.with_suffix('.progress.txt')


def say(msg):
    with open(PROGRESS, 'a', encoding='utf-8') as f:
        f.write('%.1f %s\n' % (time.perf_counter() - T0, msg))


def write(obj):
    with RUNS_LOCK:
        snap = dict(obj)
        if 'runs' in snap:
            snap['runs'] = [dict(r) for r in RUNS]
    tmp = OUT.with_name(OUT.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(snap, f)
    os.replace(tmp, OUT)


def jsonable(x, depth=0):
    if depth > 6:
        return str(x)[:200]
    if isinstance(x, dict):
        return {str(k): jsonable(v, depth + 1) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [jsonable(v, depth + 1) for v in x]
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return x
    try:
        return float(x)
    except Exception:
        return str(x)[:200]


import evaluation.controllers.area_follower_objective as _joint  # noqa: E402

_orig_expand = _joint.expand_shared_vsl_action


def _capture_expand(action, cfg, *, segment_vsl_func):
    CAP.setdefault('segment_vsl_func', segment_vsl_func)
    return _orig_expand(action, cfg, segment_vsl_func=segment_vsl_func)


_joint.expand_shared_vsl_action = _capture_expand


def probe_solve(controller, state, forecast, historical, mapping, *, options, runtime_sources,
                worker_bootstrap, budget, progress, previous_path):
    from evaluation.controllers import sdmpc as S
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import physical_ramp_branches
    from evaluation.controllers import sdmpc_tangent
    from evaluation.controllers.sdmpc_tangent_surrogate import Query, token as stoken
    from src.models.state import ControlAction
    out = {'schema': 'vp-probe/1', 'spec': SPEC, 'errors': [], 'checks': {}, 'plans': {}, 'evaluations': {},
           'runs': [], 'started_sec': time.perf_counter() - T0}
    try:
        # ---------------- sdmpc.solve, verbatim up to the surrogate Query (FRZ_K92 sdmpc.py:538-592) ----------------
        follower, state, forecast, historical = copy.deepcopy((controller.nash_solver, state, forecast, historical))
        cfg, policy = follower.cfg, dict(follower.cfg.network.sdmpc_options)
        central_mode = bool(policy.get('central_multiplier'))
        cap_mode = bool(policy.get('budget_caps'))
        if cap_mode:
            options = dict(options, nuf_tolerance_veh_h=policy['pfo_cap_options']['nuf_tolerance_veh_h'])
        if central_mode:
            from evaluation.controllers import sdmpc_central as central
        if sequence.KEY in historical.diagnostics:
            historical = sequence.first_action(historical)
        if cfg.mpc.horizon_steps * cfg.simulation.T_c_sec != 450:
            raise ValueError('First SDMPC migration requires the agreed 450s horizon')
        state._sdmpc_interval_sec = cfg.simulation.T_c_sec
        prices, price_receipt = S.load_prices(previous_path, state, policy)
        if central_mode:
            initial_central_dual = central.initialize_duals(prices, caps=cap_mode)
            if price_receipt['committed']:
                saved = json.loads(Path(previous_path).read_text(encoding='utf-8-sig'))['metadata']['sdmpc_state']
                initial_central_dual = __import__('numpy').asarray(saved['next_central_duals_scaled'], dtype=float)
        del state._sdmpc_interval_sec
        source_token = S.token(runtime_sources)
        reference = meters.prepare_held_actual_reference(historical, cfg)
        out['policy_sha256'] = S.token(policy)
        out['price_receipt_committed'] = bool(price_receipt.get('committed'))
        with joint.shared_query_runtime_scope(), ExitStack():
            adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
            callbacks, context, fingerprint = joint._joint_runtime_callbacks(follower, state, forecast,
                historical, reference, mapping, runtime_sources, reference=reference, total_budget=None,
                directional={}, tolerance=options['nuf_tolerance_veh_h'], budget=budget, price_probe=False)
            query = joint.make_decision_shared_query(follower, state, reference, forecast,
                horizon_steps=cfg.mpc.horizon_steps, source_fingerprint=source_token,
                cache_enabled=True, check_budget=budget.check,
                parallel_workers=options['response_parallel_workers'], worker_bootstrap=worker_bootstrap,
                deadline_monotonic=None if budget.unlimited_time else budget.started + budget.seconds - budget.reserve_sec,
                unlimited_time=budget.unlimited_time)
            budget.response_query = query
            coordinate_type = sequence.SequenceCoordinates if policy.get('control_blocks') == 3 else S.Coordinates
            coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)
            if not policy.get('surrogate_reuse'):
                raise ValueError('vp_probe expects the deployed surrogate_reuse path')
            query.close()
            template = sdmpc_tangent.prepare_request(follower, state, forecast, reference, reference, coord,
                                                     worker_bootstrap)
            tpl_bytes = pickle.dumps(template, protocol=5)
            out['setup_sec'] = time.perf_counter() - T0
            say('setup done')

            # ---------------- plans ----------------
            T = int(round(float(state.time_sec)))
            if T != int(SPEC['state']['T']):
                raise ValueError('state time %s differs from spec T %s' % (T, SPEC['state']['T']))
            seg_fn = CAP.get('segment_vsl_func')
            if seg_fn is None:
                raise ValueError('segment_vsl_func was not captured from the adapter')

            def action_path(t):
                return DEC / ('action_%06d.json' % t)

            def held(t):
                prev = adapter.control_from_json(action_path(t), cfg, ControlAction)
                h = physical_ramp_branches.held_actual_reference(prev, cfg)
                h, _ = _orig_expand(h, cfg, segment_vsl_func=seg_fn)
                if sequence.KEY in h.diagnostics:
                    h = sequence.first_action(h)
                return meters.prepare_held_actual_reference(h, cfg)

            raw_T = json.loads(action_path(T).read_text(encoding='utf-8-sig'))
            sel = raw_T['metadata']['joint_leader_selection']
            rec_obj = sel['selected_objective']
            rec_costs = sel['omega_partition']['costs']
            plan_token_rec = sel['control_sequence']['plan_action_token']
            direct = adapter.control_from_json(action_path(T), cfg, ControlAction)
            if sequence.KEY not in direct.diagnostics:
                raise ValueError('recorded action has no three-block plan')
            future = sequence.actions(direct, 3)[1:]
            h0 = held(T)
            REC = sequence.pack([h0] + [c.copy() for c in future])
            heads = list(cfg.network.freeway_vsl_zone_heads[OWNER])

            def zone_keys(c):
                ks = []
                for k in c.vsl:
                    if k.startswith(OWNER + '__seg'):
                        cell = int(k.split('__seg')[1])
                        if max(h for h in heads if h <= cell) == HEAD:
                            ks.append(k)
                return ks

            def with_vsl(plan, value):
                blocks = [c.copy() for c in sequence.actions(plan, 3)]
                for c in blocks:
                    c.vsl = dict(c.vsl)
                    ks = zone_keys(c)
                    if not ks:
                        raise ValueError('zone head has no VSL key')
                    for k in ks:
                        c.vsl[k] = float(value)
                    c.vsl[OWNER] = min(float(c.vsl[k]) for k in c.vsl if k.startswith(OWNER + '__seg'))
                return sequence.pack(blocks)

            def vsl_view(plan):
                return [{'zone_head_%d' % HEAD: sorted({float(c.vsl[k]) for k in zone_keys(c)}),
                         'other_FW_E_below_110': sorted(k for k in c.vsl if k.startswith(OWNER + '__seg')
                                                        and k not in zone_keys(c) and float(c.vsl[k]) < 110.0),
                         'FW_E': float(c.vsl.get(OWNER, float('nan')))} for c in sequence.actions(plan, 3)]

            plans = {'REC': REC, 'REPACK': sequence.pack(sequence.actions(REC, 3))}
            mode = SPEC['mode']
            if mode in ('A', 'S'):
                for v in SPEC['arms']:
                    plans['ARM%d' % int(v)] = with_vsl(REC, v)
            plans['EXEC'] = sequence.pack([h0.copy(), held(T + 150), held(T + 300)])
            if mode == 'S' and SPEC.get('smoke_candidates'):
                plans['CAND_direct'] = direct
            for name, p in plans.items():
                out['plans'][name] = {'token': stoken(p), 'vsl': vsl_view(p)}
            out['recorded'] = {'selected_objective': rec_obj, 'omega_costs': rec_costs, 'plan_action_token': plan_token_rec,
                               'held_objective': sel.get('held_objective'),
                               'action_json_sha256': __import__('hashlib').sha256(action_path(T).read_bytes()).hexdigest()}
            out['checks']['R0_rec_token_equals_recorded'] = out['plans']['REC']['token'] == plan_token_rec
            write(out)

            def make_runner(batch):
                def runner(request):
                    r = sdmpc_tangent._evaluate_single(request)
                    with RUNS_LOCK:
                        RUNS.append({'batch': batch, 'action_token': stoken(request['action']),
                                     'mode': request.get('surrogate_evaluation'),
                                     'request_sha256': r.get('request_sha256'),
                                     'wall_sec': r.get('wall_sec_including_spawn')})
                    return r
                return runner

            def nocheck(*a, **k):
                return None

            def emit(stage, **kw):
                say('%s %s' % (stage, json.dumps(jsonable(kw))[:200]))

            def item_rec(item):
                part = item.get('sdmpc_omega_partition') or {}
                proof = item.get('sdmpc_physical_response_reuse') or {}
                return {'objective_veh_h': item['objective_veh_h'], 'costs': dict(part.get('costs') or {}),
                        'action_token': item.get('action_token'), 'response_token': item.get('response_token'),
                        'evaluated_action_token': proof.get('evaluated_action_token', item.get('action_token')),
                        'prediction_model': item.get('prediction_model'),
                        'np_actual': ((item.get('quantities') or {}).get('np') or {}).get('actual')
                        if isinstance(item.get('quantities'), dict) else None}

            def evaluate(label_plans, derivatives, batch):
                q = Query(template, nocheck, emit, runner=make_runner(batch))
                t1 = time.perf_counter()
                items = q.evaluate([p for _, p in label_plans], derivatives=derivatives)
                for (lab, _), it in zip(label_plans, items):
                    rec = item_rec(it)
                    rec.update(mode='ad' if derivatives else 'scalar', wall_sec=time.perf_counter() - t1, batch=batch)
                    out['evaluations'][lab] = rec
                q.close()
                write(out)

            # R1: recorded plan in AD mode
            say('R1 start')
            evaluate([('R1_REC_ad', REC)], True, 'R1')
            r1 = out['evaluations']['R1_REC_ad']
            out['checks']['R1_objective_bit_equal'] = r1['objective_veh_h'] == rec_obj
            same_keys = set(r1['costs']) == set(rec_costs)
            cdiff = max(abs(r1['costs'][k] - rec_costs[k]) for k in rec_costs) if same_keys else None
            out['checks']['R1_costs_same_keys'] = same_keys
            out['checks']['R1_costs_max_abs_diff'] = cdiff
            out['checks']['R1_costs_within_1e-9'] = same_keys and cdiff <= 1e-9
            out['checks']['R1_objective_diff'] = r1['objective_veh_h'] - rec_obj
            # r3 (D-K9-108): the objective uses the same tolerance as the costs; bit equality stays a report field.
            odiff = out['checks']['R1_objective_diff']
            out['checks']['R1_objective_within_1e-9'] = math.isfinite(odiff) and abs(odiff) <= 1e-9
            write(out)
            if mode == 'S' and SPEC.get('smoke_candidates'):
                evaluate([('CAND_direct_ad', plans['CAND_direct'])], True, 'CAND_ad')
            if not (out['checks']['R1_objective_within_1e-9'] and out['checks']['R1_costs_within_1e-9']) and mode != 'S':
                out['stop'] = 'S-R1: recorded plan does not reproduce the recorded objective within 1e-9 (or a cost by > 1e-9)'
                write(out)
                return finish(out, 5)
            # scalar batch
            batch = [('R2_REC_scalar', REC), ('R3_REPACK_scalar', plans['REPACK']), ('EXEC_scalar', plans['EXEC'])]
            if mode in ('A', 'S'):
                batch += [('ARM%d_scalar' % int(v), plans['ARM%d' % int(v)]) for v in SPEC['arms']]
            if mode == 'S' and SPEC.get('smoke_candidates'):
                batch += [('CAND_direct_scalar', plans['CAND_direct'])]
            say('scalar batch start n=%d' % len(batch))
            evaluate(batch, False, 'SCALAR')
            ev = out['evaluations']
            out['checks']['R2_minus_R1'] = ev['R2_REC_scalar']['objective_veh_h'] - r1['objective_veh_h']
            out['checks']['R3_repack_bit_equal'] = (ev['R3_REPACK_scalar']['objective_veh_h']
                                                    == ev['R2_REC_scalar']['objective_veh_h']
                                                    and ev['R3_REPACK_scalar']['costs'] == ev['R2_REC_scalar']['costs'])
            write(out)
            # ablations (P mode, and S mode for the pipeline test)
            if mode in ('P', 'S'):
                out['ablations'] = {}
                names = ['null'] + list(SPEC['ablations'])

                def one(name):
                    t = pickle.loads(tpl_bytes)
                    applied = apply_ablation(t, name, SPEC['ablations'].get(name, {}), OWNER)
                    lab = 'ABL_%s' % name
                    q = Query(t, nocheck, emit, runner=make_runner(lab))
                    t1 = time.perf_counter()
                    it = q.evaluate([plans['EXEC']], derivatives=False)[0]
                    rec = item_rec(it)
                    rec.update(mode='scalar', wall_sec=time.perf_counter() - t1, applied=applied, batch=lab)
                    q.close()
                    return lab, rec
                with ThreadPoolExecutor(max_workers=int(SPEC.get('max_parallel', 4))) as pool:
                    for lab, rec in pool.map(one, names):
                        out['evaluations'][lab] = rec
                        out['ablations'][lab] = rec['applied']
                        write(out)
                out['checks']['null_bit_equal'] = (ev['ABL_null']['objective_veh_h'] == ev['EXEC_scalar']['objective_veh_h']
                                                   and ev['ABL_null']['costs'] == ev['EXEC_scalar']['costs'])
            return finish(out, 0)
    except Exception as e:
        out['errors'].append(repr(e))
        out['traceback'] = traceback.format_exc()[-6000:]
        return finish(out, 3)


def apply_ablation(t, name, cfgv, owner):
    """Patch one unpickled request template (parent side, before the worker sees it).  Returns what was set.
    The V-A FW_E plant is the aggregate 31-cell METANET step (area_freeway_accounting._freeway_substep_events) run
    with the component config state.lane_freeway_runtime.configs['FW_E']; every patch goes there (follower cell rows
    only when they describe the same cells, i.e. the same row count).  No code object is changed."""
    follower, state, _reference, _forecast = t['owned']
    rt = state.lane_freeway_runtime
    cnet = rt.configs[owner].network
    fnet = follower.cfg.network
    if rt.lanes.get(owner) is not None:
        raise ValueError('vp_probe ablations are written for the aggregate FW_E step; a lane-group plant is present')
    applied = {'name': name}
    if name == 'null':
        return applied
    rows_c = cnet.freeway_segment_params[owner]
    rows_f = (getattr(fnet, 'freeway_segment_params', {}) or {}).get(owner)
    # The follower rows are patched only when they describe the same cells (same row count, not the same objects);
    # in V-A the follower FW_E rows are also 31 (smoke v4 record component_rows_n = follower_rows_n = 31; the r1
    # comment "21 parent segments" was wrong, LOG 16:53), so both are patched.
    applied['component_rows_n'] = len(rows_c)
    applied['follower_rows_n'] = len(rows_f) if isinstance(rows_f, (list, tuple)) else None
    if not (isinstance(rows_f, (list, tuple)) and len(rows_f) == len(rows_c)):
        rows_f = None
    applied['follower_rows_patched'] = rows_f is not None
    if name == 'C1_vfree':
        cells = {}
        for key, val in sorted(cfgv['cells'].items(), key=lambda kv: int(kv[0])):
            i = int(key)
            row = rows_c[i]
            old = float(row.get('v_free', cnet.v_free))
            if 'delta' in val:
                new = old + float(val['delta'])
            else:
                rc = float(row.get('rho_crit', cnet.rho_crit))
                a = float(row.get('metanet_a_m', cnet.metanet_a_m))
                factor = math.exp(-(1.0 / a) * (float(val['k_med']) / rc) ** a)
                new = float(val['s_med']) / factor
            row['v_free'] = new
            if rows_f is not None and isinstance(rows_f[i], dict) and rows_f[i] is not row:
                rows_f[i]['v_free'] = new
            cells[str(i)] = {'old': old, 'new': new}
        applied['cells'] = cells
    elif name == 'C2_rhocrit':
        m = float(cfgv['mult'])
        cells = {}
        for i in cfgv['cells']:
            row = rows_c[int(i)]
            old = float(row.get('rho_crit', cnet.rho_crit))
            row['rho_crit'] = old * m
            rf = rows_f[int(i)] if rows_f is not None else None
            if isinstance(rf, dict) and rf is not row and 'rho_crit' in rf:
                rf['rho_crit'] = float(rf['rho_crit']) * m
            cells[str(i)] = {'old': old, 'new': old * m}
        applied['cells'] = cells
    elif name in ('C3_merge', 'C4_lanedrop'):
        _zero_scalar(cnet, fnet, owner, 'metanet_delta_merge' if name == 'C3_merge' else 'freeway_lane_drop_phi',
                     applied)
    elif name == 'C8_antic18':
        applied['cells'] = _zero_nu_rows(cnet, rows_c, rows_f, cfgv['cells'])
    elif name == 'C9_lanedrop_both':
        _zero_scalar(cnet, fnet, owner, 'freeway_lane_drop_phi', applied)
        applied['cells'] = _zero_nu_rows(cnet, rows_c, rows_f, cfgv['cells'])
    elif name == 'C5_capdrop':
        applied['old_discharge_phi'] = getattr(cnet, 'capacity_drop_discharge_phi', None)
        applied['old_anticipation'] = getattr(cnet, 'capacity_drop_anticipation', None)
        cnet.capacity_drop_discharge_phi = 1.0
        cnet.capacity_drop_anticipation = False
        applied['new_discharge_phi'] = 1.0
        applied['new_anticipation'] = False
    elif name == 'C6_compliance':
        for attr in ('freeway_vsl_fd_response', 'component_vsl_transport', 'component_vsl_initial_commands'):
            val = getattr(cnet, attr, None)
            applied['old_present_' + attr] = isinstance(val, dict) and owner in val
            if isinstance(val, dict) and owner in val:
                val = dict(val)
                val.pop(owner)
                setattr(cnet, attr, val)
        ex = getattr(state, '_component_vsl_exposure', None)
        applied['old_present_exposure_state'] = isinstance(ex, dict) and owner in ex
        if isinstance(ex, dict) and owner in ex:
            ex.pop(owner)
    elif name == 'C7_initial':
        cells = {}
        for key, val in sorted(cfgv['cells'].items(), key=lambda kv: int(kv[0])):
            i = int(key)
            old = float(state.freeway_speed[owner][i])
            new = old + float(val['delta']) if isinstance(val, dict) and 'delta' in val else float(val)
            state.freeway_speed[owner][i] = new
            cells[str(i)] = {'old': old, 'new': new}
        applied['cells'] = cells
    else:
        raise ValueError('unknown ablation ' + name)
    return applied


def _zero_scalar(cnet, fnet, owner, key, applied):
    """C3 / C4 (and C9): one FW_E scalar coefficient to 0 in the component config and in any by-direction table."""
    applied['old'] = getattr(cnet, key, None)
    setattr(cnet, key, 0.0)
    for label, net_ in (('component', cnet), ('follower', fnet)):
        bd = (getattr(net_, 'metanet_parameters_by_direction', {}) or {}).get(owner)
        if isinstance(bd, dict) and key in bd:
            applied.setdefault('by_direction_old', {})[label] = bd[key]
            bd[key] = 0.0
    applied['new'] = 0.0


def _zero_nu_rows(cnet, rows_c, rows_f, cell_list):
    """C8 (and C9): the anticipation coefficient nu of the listed cell rows to 0.  The adapter's patched
    select_anticipation_nu reads the row value (FRZ_K92 vissim_stackelberg_adapter.py:9560-9567); the congested
    nu_cong row is read only when capacity_drop_anticipation is on, which it is not in V-A (PRE_VP_FIXED 1.1)."""
    cells = {}
    for i in cell_list:
        row = rows_c[int(i)]
        old = float(row.get('metanet_nu_km2_h', cnet.metanet_nu_km2_h))
        row['metanet_nu_km2_h'] = 0.0
        rf = rows_f[int(i)] if rows_f is not None else None
        if isinstance(rf, dict) and rf is not row and 'metanet_nu_km2_h' in rf:
            rf['metanet_nu_km2_h'] = 0.0
        cells[str(int(i))] = {'old': old, 'new': 0.0}
    return cells


def finish(out, code):
    out['total_sec'] = time.perf_counter() - T0
    out['exit_code'] = code
    write(out)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


import evaluation.controllers.sdmpc as _S  # noqa: E402

_S.solve = probe_solve
runpy.run_path(ADAPTER, run_name='__main__')
write({'schema': 'vp-probe/1', 'errors': ['adapter returned without calling sdmpc.solve'],
       'total_sec': time.perf_counter() - T0})
os._exit(4)
