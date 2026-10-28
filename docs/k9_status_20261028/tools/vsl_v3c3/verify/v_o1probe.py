# v_o1probe.py — VERIFY_VSL (2026-10-27 KST). Fresh O1 re-check (does not import or copy o_probe.py).
# Different route from the authors' probe: the REAL sdmpc.solve runs unmodified up to the point where it holds its own
# decision query and operating seed; we only intercept (a) joint.make_decision_shared_query to record its arguments
# (and force in-process, cache off, as the authors did), (b) the first consumer of the operating seed
# (sdmpc_pfo.solve in cap mode, joint.initialize_decision_nuf otherwise). There we build, per phi config, a NEW query
# on a deep copy of the solve's own state with FW_E capacity_drop_discharge_phi patched, and score the operating seed
# with VSL zone-13 keys set to 110 and 90 in all three blocks. Then write JSON and exit (no action file).
# Env: V_O1_OUT (json path). argv[1] = adapter path, rest = adapter args.
import copy, json, os, runpy, sys, time, traceback

OUT = os.environ['V_O1_OUT']
PHIS = [('base', 1.0), ('phi0.95', 0.95), ('phi0.90', 0.90), ('phi0.85', 0.85), ('base_again', 1.0)]
VSLS = [110, 90]
ADAPTER = sys.argv[1]
sys.argv = [ADAPTER] + sys.argv[2:]
T0 = time.perf_counter()
CAP = {}
REC = {'schema': 'verify_vsl_o1probe/1', 'route': 'intercept real sdmpc.solve', 'configs': [], 'errors': []}


def dump():
    with open(OUT + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(REC, f, indent=1)
    os.replace(OUT + '.tmp', OUT)


def run_probe(operating_seed, where):
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import area_freeway_accounting as AFA
    try:
        REC['intercepted_at'] = where
        REC['setup_sec'] = time.perf_counter() - T0
        a, kw = CAP['args'], dict(CAP['kwargs'])
        follower, state, reference, forecast = a[0], a[1], a[2], a[3]
        cfg = follower.cfg
        heads = list(cfg.network.freeway_vsl_zone_heads['FW_E'])
        nxt = [h for h in heads if h > 13]
        hi = min(nxt) if nxt else 10 ** 6
        REC['state_time_sec'] = float(state.time_sec)
        REC['zone_heads_FW_E'] = heads
        REC['control_blocks'] = int(cfg.network.sdmpc_options.get('control_blocks', 1) or 1)
        REC['real_query_kwargs'] = {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(type(v))) for k, v in CAP['orig_kwargs'].items()}
        seen = {}
        orig_seg = AFA._mn.segment_vsl

        def seg_hook(control, road, i, c, *x, **y):
            v = orig_seg(control, road, i, c, *x, **y)
            if road == 'FW_E' and CAP.get('label'):
                seen.setdefault(CAP['label'], {}).setdefault(int(i), set()).add(round(float(v), 3))
            return v
        AFA._mn.segment_vsl = seg_hook
        blocks = sequence.actions(operating_seed, 3) if REC['control_blocks'] == 3 else [operating_seed]
        REC['seed_FW_E_vsl'] = [{k: float(v) for k, v in c.vsl.items() if k.startswith('FW_E')} for c in blocks]

        def variant(v):
            out = []
            for c in (sequence.actions(operating_seed, 3) if REC['control_blocks'] == 3 else [operating_seed]):
                c = c.copy()
                c.vsl = dict(c.vsl)
                keys = [k for k in c.vsl if k.startswith('FW_E__seg') and 13 <= int(k.split('__seg')[1]) < hi]
                for k in keys:
                    c.vsl[k] = float(v)
                segs = [float(c.vsl[k]) for k in c.vsl if k.startswith('FW_E__seg')]
                c.vsl['FW_E'] = min(segs)
                out.append(c)
            REC.setdefault('variant_keys', keys)
            return sequence.pack(out) if REC['control_blocks'] == 3 else out[0]

        for label, phi in PHIS:
            crec = {'label': label, 'phi': phi, 'J': {}}
            st = copy.deepcopy(state)
            comp_net = st.lane_freeway_runtime.configs['FW_E'].network
            crec['phi_before_patch'] = float(getattr(comp_net, 'capacity_drop_discharge_phi', 1.0) or 1.0)
            comp_net.capacity_drop_discharge_phi = phi
            crec['phi_after_patch'] = float(comp_net.capacity_drop_discharge_phi)
            crec['orig_state_phi_untouched'] = float(getattr(state.lane_freeway_runtime.configs['FW_E'].network,
                                                             'capacity_drop_discharge_phi', 1.0) or 1.0)
            q = CAP['orig_make'](follower, st, reference, forecast, **dict(kw, cache_enabled=False, parallel_workers=0,
                                                                           worker_bootstrap=None, deadline_monotonic=None))
            try:
                for v in VSLS:
                    t1 = time.perf_counter()
                    act = variant(v)
                    CAP['label'] = '%s_v%d' % (label, v)
                    item = q((act,))['results'][0]
                    CAP['label'] = None
                    crec['J']['v%d' % v] = float(item['objective_veh_h'])
                    crec.setdefault('wall', {})['v%d' % v] = time.perf_counter() - t1
            finally:
                q.close()
            crec['dJ_v90'] = crec['J']['v90'] - crec['J']['v110']
            REC['configs'].append(crec)
            dump()
        AFA._mn.segment_vsl = orig_seg
        REC['vsl_cells_seen'] = {lab: {str(i): sorted(s) for i, s in sorted(d.items()) if min(s) < 110.0 or i in (17, 18, 25, 26)}
                                 for lab, d in seen.items()}
    except Exception as e:
        REC['errors'].append(repr(e))
        REC['traceback'] = traceback.format_exc()[-4000:]
    REC['total_sec'] = time.perf_counter() - T0
    dump()
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0 if not REC['errors'] else 3)


import evaluation.controllers.sdmpc as _S
_orig_solve = _S.solve


def solve_wrapper(*a, **kw):
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers import sdmpc_pfo
    orig_make = joint.make_decision_shared_query

    def make_wrap(*ma, **mkw):
        if 'args' not in CAP:
            CAP['args'], CAP['orig_kwargs'], CAP['orig_make'] = ma, dict(mkw), orig_make
            CAP['kwargs'] = dict(mkw)
        return orig_make(*ma, **dict(mkw, cache_enabled=False, parallel_workers=0, worker_bootstrap=None))
    joint.make_decision_shared_query = make_wrap
    sdmpc_pfo.solve = lambda reference, *x, **y: run_probe(reference, 'sdmpc_pfo.solve')
    joint.initialize_decision_nuf = lambda follower, state, reference, item: run_probe(reference, 'initialize_decision_nuf')
    return _orig_solve(*a, **kw)


_S.solve = solve_wrapper
runpy.run_path(ADAPTER, run_name='__main__')
REC['errors'].append('adapter returned without reaching the intercept')
dump()
os._exit(4)
