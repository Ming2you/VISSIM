# V3 plant probe wrapper (VSL_OFFLINE, data-after declaration). No VISSIM, no COM.
# Runs the codex adapter exactly as the VBS command line does (runpy as __main__), but replaces
# evaluation.controllers.sdmpc.solve with a probe that (1) builds the SAME decision context as
# sdmpc.solve (sdmpc.py:791-874: held reference, operating bounds, shared query, coordinates,
# storage-guard operating seed) with an in-process query (parallel_workers=0), (2) scores the
# operating seed and a few VSL variants of it with the plant (no optimisation, no derivatives),
# (3) records FW_E per-cell density/speed/flow per plant step and the per-cell VSL the plant used,
# then writes one JSON and exits the process (no action file is written).
# Usage: python -B v3_plant_probe.py <adapter.py> <adapter args...>
#   env VSL_PROBE_OUT = output json path; VSL_PROBE_SPEC = json list of variants
#   variant = {"label": str, "keys": ["FW_E__seg13"], "blocks": [0,1,2], "value": 100.0}
import copy, json, math, os, runpy, sys, time, traceback
from contextlib import ExitStack

OUT = os.environ['VSL_PROBE_OUT']
SPEC = json.loads(os.environ['VSL_PROBE_SPEC'])
ADAPTER = sys.argv[1]
sys.argv = [ADAPTER] + sys.argv[2:]
T0 = time.perf_counter()


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
        return float(x) if isinstance(x, float) else x
    try:
        return float(x)
    except Exception:
        return str(x)[:200]


def write(obj):
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f)
    os.replace(tmp, OUT)


def probe_solve(controller, state, forecast, historical, mapping, *, options, runtime_sources,
                worker_bootstrap, budget, progress, previous_path):
    from evaluation.controllers import sdmpc as S
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import physical_lane_groups as PLG
    from evaluation.controllers import area_freeway_accounting as AFA
    import numpy as np
    out = {'schema': 'vsl_offline_v3/1', 'started_sec': time.perf_counter() - T0, 'variants': [], 'errors': []}
    try:
        follower, state, forecast, historical = copy.deepcopy((controller.nash_solver, state, forecast, historical))
        cfg, policy = follower.cfg, dict(follower.cfg.network.sdmpc_options)
        cap_mode = bool(policy.get('budget_caps'))
        if cap_mode:
            options = dict(options, nuf_tolerance_veh_h=policy['pfo_cap_options']['nuf_tolerance_veh_h'])
        if sequence.KEY in historical.diagnostics:
            historical = sequence.first_action(historical)
        source_token = S.token(runtime_sources)
        reference = meters.prepare_held_actual_reference(historical, cfg)
        from evaluation.controllers.physical_ramp_branches import configure_operating_bounds
        configure_operating_bounds(state, cfg, reference)
        if policy.get('fixed_vsl') is not None:
            from evaluation.controllers.control_hold import fixed_vsl_reference
            reference = fixed_vsl_reference(reference, policy['fixed_vsl'], cfg.network.freeway_vsl_zone_heads,
                                            state.time_sec, cfg.simulation.T_c_sec, policy.get('control_blocks', 1))
        net = cfg.network
        out['state_time_sec'] = float(state.time_sec)
        out['config'] = jsonable({
            'freeway_vsl_zone_heads': getattr(net, 'freeway_vsl_zone_heads', None),
            'freeway_vsl_zone_head_of_cell': getattr(net, 'freeway_vsl_zone_head_of_cell', None),
            'freeway_vsl_zone_free': getattr(net, 'freeway_vsl_zone_free', None),
            'freeway_vsl_fd_response': getattr(net, 'freeway_vsl_fd_response', None),
            'vsl_fd_two_branch': getattr(net, 'vsl_fd_two_branch', None),
            'capacity_drop_discharge_phi': getattr(net, 'capacity_drop_discharge_phi', None),
            'metanet_delta_merge': getattr(net, 'metanet_delta_merge', None),
            'alpha_vsl': getattr(net, 'alpha_vsl', None), 'v_free': getattr(net, 'v_free', None),
            'rho_crit': getattr(net, 'rho_crit', None), 'rho_max': getattr(net, 'rho_max', None),
            'metanet_a_m': getattr(net, 'metanet_a_m', None), 'metanet_tau_h': getattr(net, 'metanet_tau_h', None),
            'freeway_hadiuzzaman_FW_E': (getattr(net, 'freeway_hadiuzzaman', {}) or {}).get('FW_E') is not None,
            'freeway_port_response': getattr(net, 'freeway_port_response', None),
            'component_vsl_transport': getattr(net, 'component_vsl_transport', None) or getattr(net, 'freeway_component_vsl_transport', None),
            'vsl_set': list(cfg.freeway_follower.vsl_set),
            'T_f_sec': cfg.simulation.T_f_sec, 'T_c_sec': cfg.simulation.T_c_sec, 'horizon_steps': cfg.mpc.horizon_steps,
            'policy_fd_vsl_kmh': policy.get('fd_vsl_kmh'), 'control_blocks': policy.get('control_blocks'),
        })
        seg_rows = (getattr(net, 'freeway_segment_params', {}) or {}).get('FW_E')
        out['segment_params_FW_E'] = jsonable(seg_rows)
        with joint.shared_query_runtime_scope(), ExitStack():
            adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
            callbacks, context, fingerprint = joint._joint_runtime_callbacks(follower, state, forecast,
                historical, reference, mapping, runtime_sources, reference=reference, total_budget=None,
                directional={}, tolerance=options['nuf_tolerance_veh_h'], budget=budget, price_probe=False)
            query = joint.make_decision_shared_query(follower, state, reference, forecast,
                horizon_steps=cfg.mpc.horizon_steps, source_fingerprint=source_token,
                cache_enabled=True, check_budget=budget.check, parallel_workers=0, worker_bootstrap=None,
                deadline_monotonic=None, unlimited_time=budget.unlimited_time)
            coordinate_type = sequence.SequenceCoordinates if policy.get('control_blocks') == 3 else S.Coordinates
            coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)
            if getattr(cfg.network, 'urban_storage_guard', None):
                from evaluation.controllers.urban_storage_guard import operating_seed as protected_seed
                operating_seed = protected_seed(coord, reference, policy)
            else:
                operating_seed = reference
                if not coord.valid(coord.encode(reference)):
                    seed_z = coord.encode(reference)
                    for j, axis in enumerate(coord.axes):
                        if axis['kind'] == 'meter':
                            seed_z[j] = np.clip(seed_z[j], coord.lower[j], coord.upper[j])
                    operating_seed = coord.decode(seed_z, reference)
                    coord.validate(operating_seed)
            z0 = coord.encode(operating_seed)
            out['seed_vsl_axes'] = [dict(key=a['key'], block=a['block'], ref=a['reference_value'],
                                         value=a['reference_value'] + z0[j] * a['scale'], allowed=a.get('allowed'))
                                    for j, a in enumerate(coord.axes) if a['kind'] == 'vsl']
            out['setup_sec'] = time.perf_counter() - T0
            # ---- capture hooks (installed only now, after the adapter's own segment hooks) ----
            CAP = {'label': None, 'rows': [], 'vsl': {}, 'geom': None, 'component_config': None}
            from evaluation.controllers import lane_freeway_runtime as LFR
            orig_adv = LFR.LaneFreewayRuntime.advance

            def adv(self, st, control, demand, **kw):
                t_before = float(st.time_sec)
                r = orig_adv(self, st, control, demand, **kw)
                if CAP['label'] is not None and 'FW_E' in st.freeway_density:
                    dens = [float(x) for x in st.freeway_density['FW_E']]
                    lanes = [float(x) for x in st.freeway_effective_lanes['FW_E']]
                    if CAP['geom'] is None:
                        c = self.configs.get('FW_E')
                        lengths = [float(x) for x in AFA.cell_lengths_km(c, 'FW_E', len(dens))] if c is not None else None
                        CAP['geom'] = dict(lengths_km=lengths, lanes=lanes, dt_sec=float(c.simulation.T_f_sec) if c is not None else None,
                                           ramps={k: (v.get('road'), v.get('to_cell')) for k, v in self.ramps.items()},
                                           offramps={k: (v.get('road'), v.get('from_cell')) for k, v in self.offramps.items()},
                                           lane_group_roads=sorted(self.lanes))
                        if c is not None:
                            n2 = c.network
                            CAP['component_config'] = jsonable({k: getattr(n2, k, None) for k in (
                                'freeway_vsl_fd_response', 'vsl_fd_two_branch', 'capacity_drop_discharge_phi', 'metanet_delta_merge',
                                'alpha_vsl', 'v_free', 'rho_crit', 'rho_max', 'metanet_a_m', 'metanet_tau_h', 'metanet_kappa_veh_km_lane',
                                'lane_drop_phi', 'freeway_hadiuzzaman', 'freeway_port_response', 'freeway_state_response',
                                'freeway_component_vsl_transport', 'component_vsl_transport', 'freeway_vsl_exposure',
                                'physical_vsl_sign_binding', 'observed_vsl_history', 'freeway_physical_cell_fd',
                                'freeway_delta_merge_cells')})
                    flow = getattr(st, 'freeway_flow', {}).get('FW_E') if isinstance(getattr(st, 'freeway_flow', None), dict) else None
                    CAP['rows'].append(dict(
                        t=t_before, t_after=float(st.time_sec),
                        dens=[round(x, 4) for x in dens],
                        spd=[round(float(x), 3) for x in st.freeway_speed['FW_E']],
                        flow=[round(float(x), 2) for x in flow] if flow is not None else None,
                        lanes=lanes if len(CAP['rows']) == 0 else None,
                        origin_q=float((getattr(st, 'mainline_origin_queue', {}) or {}).get('FW_E', float('nan'))),
                        ramp_rel={k: round(float(v), 2) for k, v in (kw.get('ramp_releases') or {}).items()},
                        off_cap={k: round(float(v), 2) for k, v in (kw.get('off_capacities') or {}).items()}))
                return r
            mn = AFA._mn
            orig_seg = mn.segment_vsl

            def seg(control, road, i, c, *a, **kw):
                v = orig_seg(control, road, i, c, *a, **kw)
                if CAP['label'] is not None and road == 'FW_E':
                    CAP['vsl'].setdefault(str(int(i)), set()).add(round(float(v), 3))
                return v
            LFR.LaneFreewayRuntime.advance = adv
            mn.segment_vsl = seg
            try:
                seed_variants = [{'label': 'seed', 'seed': True}] + SPEC
                for spec in seed_variants:
                    t1 = time.perf_counter()
                    rec = {'label': spec['label'], 'spec': spec}
                    try:
                        if spec.get('seed'):
                            action = operating_seed
                        else:
                            z = z0.copy()
                            for j, a in enumerate(coord.axes):
                                if a['kind'] == 'vsl' and a['key'] in spec['keys'] and a['block'] in spec['blocks']:
                                    z[j] = (float(spec['value']) - a['reference_value']) / a['scale']
                            action = coord.decode(z, operating_seed)
                        rec['token'] = S.token(action)
                        rec['plan_vsl'] = [dict((k, v) for k, v in c.vsl.items() if k.startswith('FW_E__seg') or k in ('FW_E', 'FW_W'))
                                           for c in sequence.actions(action, 3)] if policy.get('control_blocks') == 3 else [dict(action.vsl)]
                        CAP['label'], CAP['rows'], CAP['vsl'] = spec['label'], [], {}
                        item = query((action,))['results'][0]
                        CAP['label'] = None
                        part = item.get('sdmpc_omega_partition') or {}
                        rec.update(objective_veh_h=float(item['objective_veh_h']),
                                   costs={k: float(v) for k, v in (part.get('costs') or {}).items()},
                                   control_area_ttt=jsonable((item.get('control_area') or {}).get('ttt_veh_h')),
                                   rows=CAP['rows'], vsl_by_cell={k: sorted(v) for k, v in CAP['vsl'].items()},
                                   wall_sec=time.perf_counter() - t1)
                    except Exception as e:
                        CAP['label'] = None
                        rec['error'] = repr(e)
                        rec['traceback'] = traceback.format_exc()[-3000:]
                    out['variants'].append(rec)
                    out['geom'] = CAP['geom']
                    out['component_config'] = CAP['component_config']
                    write(out)
            finally:
                LFR.LaneFreewayRuntime.advance = orig_adv
                mn.segment_vsl = orig_seg
            out['query_stats'] = jsonable({k: v for k, v in query.stats().items() if not isinstance(v, (dict, list))})
            query.close()
    except Exception as e:
        out['errors'].append(repr(e))
        out['traceback'] = traceback.format_exc()[-4000:]
    out['total_sec'] = time.perf_counter() - T0
    write(out)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0 if not out['errors'] else 3)


import evaluation.controllers.sdmpc as _S
_S.solve = probe_solve
runpy.run_path(ADAPTER, run_name='__main__')
# If the adapter returns without calling solve, record that.
write({'schema': 'vsl_offline_v3/1', 'errors': ['adapter returned without calling sdmpc.solve'], 'total_sec': time.perf_counter() - T0})
os._exit(4)
