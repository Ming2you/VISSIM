# O1/O2 plant probe (vsl_v3c3, 2026-10-27 KST). No VISSIM, no COM, no action file written.
# Derived from c_port/vsl/work/v3_plant_probe.py (sha 7307f8a5...). Runs the codex adapter as the VBS command line does
# (runpy __main__), replaces evaluation.controllers.sdmpc.solve by a probe that builds the SAME decision context as
# sdmpc.solve (held reference, operating bounds, fixed-VSL schedule, shared query, coordinates, storage-guard seed),
# then, for each plant-parameter config, (1) patches FW_E plant parameters on the probe's own deep copies,
# (2) builds a NEW in-process shared query (cache off), (3) scores VSL variants of the operating seed, (4) records
# FW_E per-cell rows aggregated into 150 s blocks (and optionally raw rows). Writes one JSON, exits the process.
# Env: O_PROBE_OUT (json path), O_PROBE_SPEC (json):
#   {"owner":"FW_E","zone_head":13,"vsl":[110,100,90] or ["seed",110],"configs":[{"label":..,"phi":1.0,"rho_mult":1.0},..],
#    "keep_rows":["seed"] (variant labels whose raw rows are kept)}
# VSL variant = the operating seed with every <owner>__seg<k> key whose zone head == zone_head set to v in every
# control block (owner min recomputed), other zones/levers unchanged. "seed" = the operating seed itself.
# Patched keys (FW_E only, absolute values from the saved originals each config):
#   phi:  state.lane_freeway_runtime.configs[owner].network.capacity_drop_discharge_phi
#   rho:  ...configs[owner].network.rho_crit (component link scalar),
#         ...configs[owner].network.freeway_segment_params[owner][i]['rho_crit'] (all cells),
#         follower.cfg.network.freeway_segment_params[owner][i]['rho_crit'] (objective copy, lane_plant_runtime.py:568)
import copy, json, math, os, runpy, sys, time, traceback
from contextlib import ExitStack

OUT = os.environ['O_PROBE_OUT']
SPEC = json.loads(os.environ['O_PROBE_SPEC'])
ADAPTER = sys.argv[1]
sys.argv = [ADAPTER] + sys.argv[2:]
T0 = time.perf_counter()
BLOCK_SEC = 150.0


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


def aggregate(rows, lengths, t_start):
    """Per 150 s block and cell: time-mean stock (veh), vehicle-weighted speed (km/h), time-mean flow k*v*lanes (veh/h)."""
    n = len(lengths)
    acc = {}
    for r in rows:
        dt = r['t_after'] - r['t']
        if dt <= 0:
            continue
        b = int((r['t'] - t_start) // BLOCK_SEC)
        a = acc.setdefault(b, {'dt': 0.0, 'nv': [0.0] * n, 'nvv': [0.0] * n, 'q': [0.0] * n})
        a['dt'] += dt
        for i in range(n):
            veh = r['dens'][i] * lengths[i] * r['lanes'][i]
            a['nv'][i] += veh * dt
            a['nvv'][i] += veh * r['spd'][i] * dt
            a['q'][i] += r['dens'][i] * r['spd'][i] * r['lanes'][i] * dt
    out = {}
    for b, a in sorted(acc.items()):
        out[str(b)] = {'dt_sec': a['dt'],
                       'stock_veh': [x / a['dt'] for x in a['nv']],
                       'speed_kmh': [(y / x) if x > 1e-12 else None for x, y in zip(a['nv'], a['nvv'])],
                       'flow_veh_h': [x / a['dt'] for x in a['q']]}
    return out


def probe_solve(controller, state, forecast, historical, mapping, *, options, runtime_sources,
                worker_bootstrap, budget, progress, previous_path):
    from evaluation.controllers import sdmpc as S
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import area_freeway_accounting as AFA
    import numpy as np
    owner = SPEC.get('owner', 'FW_E')
    zone_head = int(SPEC.get('zone_head', 13))
    out = {'schema': 'vsl_v3c3_o_probe/1', 'spec': SPEC, 'started_sec': time.perf_counter() - T0, 'configs': [], 'errors': []}
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
        blocks = int(policy.get('control_blocks', 1) or 1)
        heads = list(net.freeway_vsl_zone_heads[owner])
        out['state_time_sec'] = float(state.time_sec)
        out['policy_fixed_vsl'] = jsonable(policy.get('fixed_vsl'))
        out['config'] = jsonable({'freeway_vsl_zone_heads': getattr(net, 'freeway_vsl_zone_heads', None),
                                  'vsl_set': list(cfg.freeway_follower.vsl_set), 'T_c_sec': cfg.simulation.T_c_sec,
                                  'horizon_steps': cfg.mpc.horizon_steps, 'control_blocks': blocks})
        rt = state.lane_freeway_runtime
        comp = rt.configs[owner]
        cnet = comp.network
        geom_lengths = [float(x) for x in AFA.cell_lengths_km(comp, owner, len(state.freeway_density[owner]))]
        out['geom'] = dict(lengths_km=geom_lengths, lanes0=[float(x) for x in state.freeway_effective_lanes[owner]],
                           lane_group_roads=sorted(rt.lanes), ramps={k: (v.get('road'), v.get('to_cell')) for k, v in rt.ramps.items()},
                           offramps={k: (v.get('road'), v.get('from_cell')) for k, v in rt.offramps.items()},
                           dt_sec=float(comp.simulation.T_f_sec))
        orig = dict(phi=float(getattr(cnet, 'capacity_drop_discharge_phi', 1.0) or 1.0), rho_link=float(cnet.rho_crit),
                    rho_rows=[float(r.get('rho_crit', cnet.rho_crit)) for r in cnet.freeway_segment_params[owner]],
                    rho_rows_main=[float(r.get('rho_crit', float('nan'))) for r in net.freeway_segment_params[owner]],
                    rho_rows_have_key=[('rho_crit' in r) for r in cnet.freeway_segment_params[owner]])
        out['original_params'] = orig
        out['component_config'] = jsonable({k: getattr(cnet, k, None) for k in (
            'freeway_vsl_fd_response', 'vsl_fd_two_branch', 'capacity_drop_discharge_phi', 'metanet_delta_merge',
            'rho_crit', 'rho_max', 'v_free', 'metanet_a_m', 'component_vsl_transport', 'terminal_zero_gradient')})
        out['initial_FW_E'] = dict(dens=[float(x) for x in state.freeway_density[owner]],
                                   spd=[float(x) for x in state.freeway_speed[owner]])
        # ---- the decision context (same as sdmpc.solve), once ----
        with joint.shared_query_runtime_scope(), ExitStack():
            adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
            callbacks, context, fingerprint = joint._joint_runtime_callbacks(follower, state, forecast,
                historical, reference, mapping, runtime_sources, reference=reference, total_budget=None,
                directional={}, tolerance=options['nuf_tolerance_veh_h'], budget=budget, price_probe=False)
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
            seed_blocks = sequence.actions(operating_seed, 3) if blocks == 3 else [operating_seed]
            out['seed_plan_vsl'] = [dict((k, float(v)) for k, v in c.vsl.items() if k.startswith(owner)) for c in seed_blocks]
            out['setup_sec'] = time.perf_counter() - T0

            def zone_keys(c):
                ks = []
                for k in c.vsl:
                    if k.startswith(owner + '__seg'):
                        cell = int(k.split('__seg')[1])
                        if max(h for h in heads if h <= cell) == zone_head:
                            ks.append(k)
                return ks

            def vsl_variant(value):
                ctrls = [c.copy() for c in (sequence.actions(operating_seed, 3) if blocks == 3 else [operating_seed])]
                for c in ctrls:
                    c.vsl = dict(c.vsl)
                    ks = zone_keys(c)
                    if not ks:
                        raise ValueError('zone head has no expanded VSL key')
                    for k in ks:
                        c.vsl[k] = float(value)
                    c.vsl[owner] = min(float(c.vsl[k]) for k in c.vsl if k.startswith(owner + '__seg'))
                return sequence.pack(ctrls) if blocks == 3 else ctrls[0]

            out['zone_keys'] = zone_keys(seed_blocks[0])
            # ---- capture hooks ----
            CAP = {'label': None, 'rows': [], 'vsl': {}}
            from evaluation.controllers import lane_freeway_runtime as LFR
            orig_adv = LFR.LaneFreewayRuntime.advance

            def adv(self, st, control, demand, **kw):
                t_before = float(st.time_sec)
                r = orig_adv(self, st, control, demand, **kw)
                if CAP['label'] is not None and owner in st.freeway_density:
                    CAP['rows'].append(dict(
                        t=t_before, t_after=float(st.time_sec),
                        dens=[float(x) for x in st.freeway_density[owner]],
                        spd=[float(x) for x in st.freeway_speed[owner]],
                        lanes=[float(x) for x in st.freeway_effective_lanes[owner]],
                        origin_q=float((getattr(st, 'mainline_origin_queue', {}) or {}).get(owner, float('nan'))),
                        ramp_rel={k: float(v) for k, v in (kw.get('ramp_releases') or {}).items()},
                        off_cap={k: float(v) for k, v in (kw.get('off_capacities') or {}).items()}))
                return r
            mn = AFA._mn
            orig_seg = mn.segment_vsl

            def seg(control, road, i, c, *a, **kw):
                v = orig_seg(control, road, i, c, *a, **kw)
                if CAP['label'] is not None and road == owner:
                    CAP['vsl'].setdefault(str(int(i)), set()).add(round(float(v), 3))
                return v
            LFR.LaneFreewayRuntime.advance = adv
            mn.segment_vsl = seg
            try:
                for conf in SPEC['configs']:
                    crec = {'label': conf['label'], 'phi': conf['phi'], 'rho_mult': conf['rho_mult'], 'variants': []}
                    t_c = time.perf_counter()
                    try:
                        m = float(conf['rho_mult'])
                        cnet.capacity_drop_discharge_phi = float(conf['phi'])
                        cnet.rho_crit = orig['rho_link'] * m
                        for i, row in enumerate(cnet.freeway_segment_params[owner]):
                            row['rho_crit'] = orig['rho_rows'][i] * m
                        for i, row in enumerate(net.freeway_segment_params[owner]):
                            if math.isfinite(orig['rho_rows_main'][i]):
                                row['rho_crit'] = orig['rho_rows_main'][i] * m
                        crec['applied'] = dict(phi=float(cnet.capacity_drop_discharge_phi), rho_link=float(cnet.rho_crit),
                                               rho_rows_min=min(r['rho_crit'] for r in cnet.freeway_segment_params[owner]),
                                               rho_rows_max=max(r['rho_crit'] for r in cnet.freeway_segment_params[owner]))
                        query = joint.make_decision_shared_query(follower, state, reference, forecast,
                            horizon_steps=cfg.mpc.horizon_steps, source_fingerprint=source_token,
                            cache_enabled=False, check_budget=budget.check, parallel_workers=0, worker_bootstrap=None,
                            deadline_monotonic=None, unlimited_time=budget.unlimited_time)
                        try:
                            for v in SPEC['vsl']:
                                label = 'seed' if v == 'seed' else 'v%d' % int(v)
                                rec = {'label': label}
                                t1 = time.perf_counter()
                                try:
                                    action = operating_seed if v == 'seed' else vsl_variant(v)
                                    rec['token'] = S.token(action)
                                    rec['plan_vsl_zone'] = [[float(c.vsl[k]) for k in zone_keys(c)] for c in
                                                            (sequence.actions(action, 3) if blocks == 3 else [action])]
                                    CAP['label'], CAP['rows'], CAP['vsl'] = label, [], {}
                                    item = query((action,))['results'][0]
                                    CAP['label'] = None
                                    part = item.get('sdmpc_omega_partition') or {}
                                    rows = sorted(CAP['rows'], key=lambda r: r['t'])
                                    # state.time_sec is set by the caller before each substep (t_after == t in the hook):
                                    # a step's end is the next step's start; the last ends at T + horizon (c_port v3_analyze c973fe58 rule)
                                    horizon_end = float(state.time_sec) + float(cfg.mpc.horizon_steps) * float(cfg.simulation.T_c_sec)
                                    for a_, b_ in zip(rows, rows[1:]):
                                        a_['t_after'] = b_['t']
                                    if rows:
                                        rows[-1]['t_after'] = horizon_end
                                    rc_link = float(cnet.rho_crit)
                                    exceed = [0.0] * len(geom_lengths)
                                    for r in rows:
                                        for i, d in enumerate(r['dens']):
                                            if d > rc_link:
                                                exceed[i] += r['t_after'] - r['t']
                                    rec.update(objective_veh_h=float(item['objective_veh_h']),
                                               costs={k: float(v2) for k, v2 in (part.get('costs') or {}).items()},
                                               blocks=aggregate(rows, geom_lengths, float(state.time_sec)),
                                               n_steps=len(rows), exceed_rho_link_sec=exceed, horizon_end=horizon_end,
                                               origin_q_end=rows[-1]['origin_q'] if rows else None,
                                               ramp_rel_mean={k: sum(r['ramp_rel'].get(k, 0.0) for r in rows) / max(len(rows), 1)
                                                              for k in (rows[0]['ramp_rel'] if rows else {})},
                                               vsl_by_cell={k: sorted(x) for k, x in CAP['vsl'].items()},
                                               wall_sec=time.perf_counter() - t1)
                                    if label in (SPEC.get('keep_rows') or []):
                                        rec['rows'] = [dict(t=r['t'], t_after=r['t_after'], dens=[round(x, 4) for x in r['dens']],
                                                            spd=[round(x, 3) for x in r['spd']]) for r in rows]
                                except Exception as e:
                                    CAP['label'] = None
                                    rec['error'] = repr(e)
                                    rec['traceback'] = traceback.format_exc()[-3000:]
                                crec['variants'].append(rec)
                        finally:
                            query.close()
                    except Exception as e:
                        crec['error'] = repr(e)
                        crec['traceback'] = traceback.format_exc()[-3000:]
                    crec['wall_sec'] = time.perf_counter() - t_c
                    out['configs'].append(crec)
                    write(out)
            finally:
                LFR.LaneFreewayRuntime.advance = orig_adv
                mn.segment_vsl = orig_seg
                cnet.capacity_drop_discharge_phi = orig['phi']
                cnet.rho_crit = orig['rho_link']
                for i, row in enumerate(cnet.freeway_segment_params[owner]):
                    row['rho_crit'] = orig['rho_rows'][i]
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
write({'schema': 'vsl_v3c3_o_probe/1', 'errors': ['adapter returned without calling sdmpc.solve'], 'total_sec': time.perf_counter() - T0})
os._exit(4)
