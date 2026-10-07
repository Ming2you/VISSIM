# K8-6 SA gate hook site (diagnostics only).  Loaded only through PYTHONPATH=<k8_gates>/sa/sa_hooks, which
# sa_capture.py `full` and sa_jobs.py --hooks set for the hooked runs of G-EB-11(d) and G-EB-13.
#
# (1) Chain: env K8_SA_CHAIN_SITE = path of another sitecustomize.py, executed first in its own module namespace:
#       k8_gates/site/sitecustomize.py   (K8-0 long-path shim + passive S1/S3 counters), or
#       k8_gates/s3site/sitecustomize.py (K8-0b S3 31-site LINE hook).  With env K8_S3_TABLE_JSON the s3site's site
#       table is taken from that JSON (sa_anchors.py re-anchoring onto the K8-6 tree): the three-line selection block
#       of the s3site source is replaced in memory (exact text, must occur once; otherwise this site refuses), so the
#       S3 hook machinery itself is unchanged (amendment 2 N-A9 "the same S3 31-site hook").
# (2) K8_HOOK_DIR set and K8_SA_HOOK=1: PASSIVE monitors (sys.monitoring, Python 3.12; attribute reads only, never an
#     arithmetic, comparison or method call on a Dual):
#     (a) SA fold sites (OPT1_V2_SPEC_AMENDMENT_1 §5.9 rule 3 + amendment 2 N-A4), the four named functions of
#         evaluation.controllers.stopline_approach:
#           _fold_service_residual(st, lane, member, residual)   carry[l][m] before/after
#           _fold_city_share(st, lane, member, amount)            carry[l][m] before/after
#           _merge_tiny_transfer(st, kept, tiny)                  kept / return value
#           _skip_tiny_port_share(st, lane, member, amount)       report site (N-A4): no retention check
#         For a reverse-AD tape value the event keeps (trace, node_in, node_before, node_after); at the start of
#         Trace.jacobian one read-only forward sweep with a fixed random direction (rng 20261004, as the s3site)
#         gives t = J r and the bound s = |J| |r| per node: an event is "exact nonzero" when |t_in| > 1e-13 s_in;
#         it is "dropped" when additionally |t_after - t_before - t_in| > 1e-13 (s_after + s_before + s_in)
#         (the folded tangent did not arrive in carry / the merged value).  Judged in G-EB-11(d): dropped = 0 at
#         the three rule-3 sites; site 4 is reported (events, sum |t_in|).
#     (b) G-EB-13 capacity reads of the three W members:
#           calls of src.models.urban_queue_model._movement_capacity_flow with movement in the W members, by caller
#           module:function:line;
#           LINE events of every source line (modules under K8G_ROOT) holding 'cap_flow_of[' or
#           'movement_capacity_by_movement_veh_h': a W member found in the locals m / movement / _m / member /
#           reference / mv / key / name -> counted by module:function:line:token; whole-table copies (dict(...))
#           and lines with no resolvable member are counted apart ('table', 'unresolved').
#     Output <K8_HOOK_DIR>/sahook_<pid>.json at exit and every 20 s.
import os
import sys

_CHAIN = os.environ.get('K8_SA_CHAIN_SITE')
_TABLE = os.environ.get('K8_S3_TABLE_JSON')
_OUT = os.environ.get('K8_HOOK_DIR')
_ON = os.environ.get('K8_SA_HOOK') == '1'
S3_SELECT = ("ANCHORS = os.environ.get('K8_S3_ANCHORS', 'k81')\n"
             "if ANCHORS not in ('k81', 'k82'):\n"
             "    raise SystemExit('K8_S3_ANCHORS must be k81 or k82')\n"
             "SITES = SITES_K82 if ANCHORS == 'k82' else SITES_K81\n")


def _chain():
    import types
    path = os.path.abspath(_CHAIN)
    with open(path, 'r', encoding='utf-8') as h:
        text = h.read()
    if _TABLE:
        if text.count(S3_SELECT) != 1:
            raise RuntimeError('chained site has no unique s3 table selection block: ' + path)
        text = text.replace(S3_SELECT, "import json as _k8sa_json\n"
                            "ANCHORS = 'json:' + os.path.basename(%r)\n"
                            "SITES = [tuple(_r) for _r in _k8sa_json.load(open(%r, encoding='utf-8'))['rows']]\n"
                            % (_TABLE, _TABLE))
    module = types.ModuleType('k8_chained_site')
    module.__file__ = path
    sys.modules['k8_chained_site'] = module
    exec(compile(text, path, 'exec'), module.__dict__)


if _CHAIN:
    try:
        _chain()
    except Exception as _exc:  # never break the process; leave a trace in the hook dir
        if _OUT:
            try:
                os.makedirs(_OUT, exist_ok=True)
                with open(os.path.join(_OUT, 'sa_chain_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
                    _h.write(repr(_exc))
            except Exception:
                pass

W_MEMBERS = tuple(os.environ.get('K8_SA_W_MEMBERS', 'SC1001_W_to_E_SC1002,SC1001_W_to_S_SC1003,'
                                                    'SC1001_W_to_N_SC2002').split(','))
FOLD_SITES = {'_fold_service_residual': ('residual', 'carry', True), '_fold_city_share': ('amount', 'carry', True),
              '_merge_tiny_transfer': ('tiny', 'kept', True), '_skip_tiny_port_share': ('amount', None, False),
              '_skip_tiny_city_moving_share': ('amount', None, False)}   # K8b-3 P-2 site 5 (amendment 16 2.0-9)
CAP_TOKENS = ('cap_flow_of[', 'movement_capacity_by_movement_veh_h')
KEY_NAMES = ('m', 'movement', '_m', 'member', 'reference', 'mv', 'key', 'name')


def _setup():
    import atexit
    import importlib.abc
    import json
    import threading
    import time
    from collections import defaultdict

    mon = sys.monitoring
    ev = mon.events
    tool = None
    for candidate in (2, 1, 5, 3, 4):
        try:
            mon.use_tool_id(candidate, 'k8_sa_passive')
            tool = candidate
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('no free sys.monitoring tool id')
    DISABLE = mon.DISABLE
    lock = threading.RLock()
    role = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else 'python'
    root = os.path.normcase(os.path.abspath(os.environ.get('K8G_ROOT', '.')))
    C = defaultdict(float)
    FOLD = defaultdict(lambda: defaultdict(float))
    CAP = defaultdict(lambda: defaultdict(float))
    EXTRA = {'errors': [], 'patched': [], 'sweeps': [], 'tool': tool, 'members': list(W_MEMBERS)}
    PENDING = {}          # id(trace) -> (trace, [(site, n_in, n_before, n_after)])
    OPEN = {}             # id(frame) -> (site, n_in, n_before, trace, cls)
    state = {'last': time.time()}

    def dump(final=False):
        try:
            os.makedirs(_OUT, exist_ok=True)
            with lock:
                rec = {'schema': 'k8-sa-hook/v1', 'pid': os.getpid(), 'ppid': os.getppid(), 'role': role,
                       'argv': [str(a)[-120:] for a in sys.argv[:5]], 'final': final, 'wall': time.time(),
                       'counters': dict(C), 'fold': {k: dict(v) for k, v in FOLD.items()},
                       'cap_reads': {k: dict(v) for k, v in CAP.items()},
                       'pending_unevaluated': sum(len(v[1]) for v in PENDING.values()), 'extra': EXTRA}
            tmp = os.path.join(_OUT, 'sahook_%d.json.tmp' % os.getpid())
            with open(tmp, 'w', encoding='utf-8') as h:
                json.dump(rec, h)
            os.replace(tmp, os.path.join(_OUT, 'sahook_%d.json' % os.getpid()))
        except Exception:
            pass

    def maybe_dump():
        now = time.time()
        if now - state['last'] > 20.0:
            state['last'] = now
            dump()

    def final():
        with lock:
            for _key, (_trace, events) in list(PENDING.items()):
                for e in events:
                    FOLD[e[0]]['ev_unevaluated'] += 1
            PENDING.clear()
        dump(True)

    atexit.register(final)

    def note(exc):
        C['hook_errors'] += 1
        if len(EXTRA['errors']) < 10:
            EXTRA['errors'].append(repr(exc)[:300])

    def classify(x):
        """('float'|'rdual'|'rdual0'|'fdual'|'other', primal, node, trace, tangent_abs)."""
        if x is None:
            return 'other', None, 0, None, 0.0
        if isinstance(x, (int, float)) and not hasattr(x, 'value'):
            return 'float', float(x), 0, None, 0.0
        try:
            p = float(getattr(x, 'value'))
        except Exception:
            return 'other', None, 0, None, 0.0
        try:
            node = object.__getattribute__(x, 'node')
        except AttributeError:
            node = None
        if node is not None:
            return ('rdual' if node else 'rdual0'), p, int(node), getattr(x, 'trace', None), 0.0
        tan = getattr(x, 'tangent', None)
        if isinstance(tan, dict):
            return 'fdual', p, 0, None, sum(abs(float(v)) for v in tan.values())
        return 'rdual0', p, 0, None, 0.0

    # ------------------------------------------------------------------ (a) SA fold sites
    def fold_value(site, loc, which):
        name, ref, _check = FOLD_SITES[site]
        if which == 'in':
            return loc.get(name)
        if ref == 'carry':
            st, lane, member = loc.get('st'), loc.get('lane'), loc.get('member')
            try:
                return st['carry'][lane][member]
            except Exception:
                return None
        if ref == 'kept':
            return loc.get('kept')
        return None

    def fold_start(site, frame):
        loc = frame.f_locals
        x = fold_value(site, loc, 'in')
        cls, p, node, trace, tabs = classify(x)
        B = FOLD[site]
        B['calls'] += 1
        B['values_' + cls] += 1
        if p is not None and p != 0.0:
            B['primal_nonzero'] += 1
            B['primal_abs_sum'] += abs(p)
        if cls == 'fdual':
            B['fdual_tangent_abs_sum'] += tabs
        before = fold_value(site, loc, 'before') if FOLD_SITES[site][2] else None
        bcls, _bp, bnode, _bt, btabs = classify(before)
        OPEN[id(frame)] = (site, cls, node, bnode, trace, tabs, btabs)

    def fold_return(site, frame, retval):
        row = OPEN.pop(id(frame), None)
        if row is None:
            return
        _site, cls, n_in, n_before, trace, tabs, btabs = row
        B = FOLD[site]
        if not FOLD_SITES[site][2]:
            if cls == 'rdual' and trace is not None:
                ent = PENDING.setdefault(id(trace), (trace, []))
                ent[1].append((site, n_in, 0, 0))
            return
        after = retval if FOLD_SITES[site][1] == 'kept' else fold_value(site, frame.f_locals, 'after')
        acls, _ap, n_after, _at, atabs = classify(after)
        if cls == 'rdual' and trace is not None:
            ent = PENDING.setdefault(id(trace), (trace, []))
            ent[1].append((site, n_in, n_before, n_after))
        elif cls == 'fdual':
            # forward mode (tests only): tangent sums are directly readable
            if tabs > 0.0:
                B['ev_exact_nonzero'] += 1
                if atabs + 1e-15 < max(0.0, tabs - btabs) - 1e-12:
                    B['dropped'] += 1
                    B['dropped_abs_tangent_sum'] += tabs

    kernel = {}

    def get_kernel():
        if 'f' not in kernel:
            import numba
            import numpy as np

            def sweep(p1, p2, w1, w2, sn, sa, sw, r, n):
                t = np.zeros(n)
                s = np.zeros(n)
                for k in range(len(sn)):
                    v = sw[k] * r[sa[k]]
                    t[sn[k]] += v
                    s[sn[k]] += abs(v)
                for i in range(1, n):
                    a = p1[i]
                    b = p2[i]
                    if a != 0:
                        t[i] += w1[i] * t[a]
                        s[i] += abs(w1[i]) * s[a]
                    if b != 0:
                        t[i] += w2[i] * t[b]
                        s[i] += abs(w2[i]) * s[b]
                return t, s
            kernel['f'] = numba.njit(cache=False)(sweep)
            kernel['np'] = np
        return kernel['f'], kernel['np']

    def jacobian_start(frame):
        trace = frame.f_locals.get('self')
        if trace is None:
            return
        with lock:
            ent = PENDING.pop(id(trace), None)
        if not ent:
            return
        f, np = get_kernel()
        n = len(trace.p1)
        r = np.random.default_rng(20261004).standard_normal(len(trace.steps))
        views = [np.frombuffer(trace.p1, dtype=np.int64), np.frombuffer(trace.p2, dtype=np.int64),
                 np.frombuffer(trace.w1, dtype=np.float64), np.frombuffer(trace.w2, dtype=np.float64),
                 np.frombuffer(trace.seed_nodes, dtype=np.int64), np.frombuffer(trace.seed_axes, dtype=np.int64),
                 np.frombuffer(trace.seed_weights, dtype=np.float64)]
        try:
            t, s = f(*views, r, n)
        finally:
            del views
        with lock:
            for site, n_in, n_b, n_a in ent[1]:
                B = FOLD[site]
                tin, sin = float(t[n_in]), float(s[n_in])
                if not (tin != 0.0 and abs(tin) > 1e-13 * sin):
                    B['ev_exact_zero'] += 1
                    continue
                B['ev_exact_nonzero'] += 1
                B['abs_dir_tangent_sum'] += abs(tin)
                if not FOLD_SITES[site][2]:
                    continue
                ta = float(t[n_a]) if n_a else 0.0
                tb = float(t[n_b]) if n_b else 0.0
                sa_ = float(s[n_a]) if n_a else 0.0
                sb_ = float(s[n_b]) if n_b else 0.0
                if abs(ta - tb - tin) > 1e-13 * (sa_ + sb_ + sin):
                    B['dropped'] += 1
                    B['dropped_abs_tangent_sum'] += abs(tin)
                else:
                    B['kept'] += 1
            EXTRA['sweeps'].append({'nodes': n - 1, 'events': len(ent[1])})
        dump()

    # ------------------------------------------------------------------ (b) capacity reads
    def caller_key(frame):
        code = frame.f_code
        mod = os.path.splitext(os.path.basename(code.co_filename))[0]
        return f'{mod}:{getattr(code, "co_qualname", code.co_name)}:{frame.f_lineno}'

    def chain_key(frame, depth=5):
        """'mod:func:line < mod:func:line < ...' from the given frame outwards (classification in sa_hookcount)."""
        parts = []
        while frame is not None and len(parts) < depth:
            parts.append(caller_key(frame))
            frame = frame.f_back
        return ' < '.join(parts)

    def capflow_start(frame):
        m = frame.f_locals.get('movement')
        if isinstance(m, str) and m in W_MEMBERS:
            back = frame.f_back
            CAP['_movement_capacity_flow'][(chain_key(back) if back is not None else '?') + ' | ' + m] += 1

    line_sites = {}       # code -> {line: (token, kind)}

    def handle_line(code, line, frame):
        site = line_sites[code][line]
        token, kind = site
        key = f'{os.path.splitext(os.path.basename(code.co_filename))[0]}:' \
              f'{getattr(code, "co_qualname", code.co_name)}:{line}:{token}'
        if kind == 'table':
            CAP['table'][key] += 1
            return
        loc = frame.f_locals
        hit = [n for n in KEY_NAMES if isinstance(loc.get(n), str) and loc.get(n) in W_MEMBERS]
        if hit:
            back = frame.f_back
            CAP['member'][key + ':' + hit[0] + ' | ' + (chain_key(back, 4) if back is not None else '?')] += 1
        else:
            CAP['unresolved_lines'][key] += 1

    def all_codes(code):
        yield code
        for k in code.co_consts:
            if hasattr(k, 'co_lines'):
                yield from all_codes(k)

    def module_codes(module):
        seen, out = set(), []

        def add(obj):
            fn = getattr(obj, '__func__', obj)
            code = getattr(fn, '__code__', None)
            if code is None or id(code) in seen:
                return
            seen.add(id(code))
            out.extend(all_codes(code))
        for value in list(vars(module).values()):
            if isinstance(value, type) and getattr(value, '__module__', None) == module.__name__:
                for v in list(vars(value).values()):
                    add(v)
            elif callable(value) and getattr(value, '__module__', None) == module.__name__:
                add(value)
        return out

    start_handlers, return_handlers = {}, {}

    def patch_module(module):
        name = module.__name__
        if name.endswith('stopline_approach'):
            for site in FOLD_SITES:
                fn = getattr(module, site, None)
                if fn is None:
                    EXTRA['errors'].append('fold site missing ' + site)
                    continue
                code = fn.__code__
                start_handlers[code] = (lambda fr, _s=site: fold_start(_s, fr))
                return_handlers[code] = (lambda fr, rv, _s=site: fold_return(_s, fr, rv))
                mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_START | ev.PY_RETURN)
            EXTRA['patched'].append(name)
        if name.endswith('urban_queue_model'):
            fn = getattr(module, '_movement_capacity_flow', None)
            if fn is not None:
                code = fn.__code__
                start_handlers[code] = capflow_start
                mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_START)
                EXTRA['patched'].append(name + '._movement_capacity_flow')
        if name.endswith('sdmpc_tangent_reverse'):
            code = module.Trace.jacobian.__code__
            start_handlers[code] = jacobian_start
            mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_START)
            EXTRA['patched'].append(name + '.Trace.jacobian')
        origin = getattr(module, '__file__', None)
        if origin and os.path.normcase(os.path.abspath(origin)).startswith(root):
            try:
                with open(origin, 'r', encoding='utf-8') as h:
                    lines = h.read().splitlines()
            except Exception as exc:
                note(exc)
                return
            hits = {}
            for i, text in enumerate(lines, start=1):
                body = text.split('#', 1)[0]
                for token in CAP_TOKENS:
                    if token in body:
                        hits[i] = (token, 'table' if ('dict(' in body and token in body and '[' not in
                                                      body.split(token, 1)[1][:3]) else 'read')
                        break
            if not hits:
                return
            codes = module_codes(module)
            for line, site in hits.items():
                owners = [k for k in codes if any(ln == line for _, _, ln in k.co_lines())]
                if not owners:
                    continue
                owner = max(owners, key=lambda k: k.co_firstlineno)
                line_sites.setdefault(owner, {})[line] = site
                mon.set_local_events(tool, owner, mon.get_local_events(tool, owner) | ev.LINE)
            EXTRA['patched'].append(name + ':%d lines' % len(hits))

    def on_start(code, offset):
        h = start_handlers.get(code)
        if h is None:
            return None
        try:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is not None:
                with lock:
                    h(frame)
                    maybe_dump()
        except Exception as exc:
            note(exc)
        return None

    def on_return(code, offset, retval):
        h = return_handlers.get(code)
        if h is None:
            if code is finder_ref.get('install_code'):
                f = finder_ref.get('finder')
                if f is not None and f in sys.meta_path and sys.meta_path[0] is not f:
                    sys.meta_path.remove(f)
                    sys.meta_path.insert(0, f)
                    C['tangent_install_seen'] += 1
            return None
        try:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is not None:
                with lock:
                    h(frame, retval)
        except Exception as exc:
            note(exc)
        return None

    def on_line(code, line):
        sites = line_sites.get(code)
        if not sites or line not in sites:
            return DISABLE
        try:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is not None:
                with lock:
                    handle_line(code, line, frame)
                    maybe_dump()
        except Exception as exc:
            note(exc)
        return None

    mon.register_callback(tool, ev.PY_START, on_start)
    mon.register_callback(tool, ev.PY_RETURN, on_return)
    mon.register_callback(tool, ev.LINE, on_line)
    finder_ref = {}

    class PassiveFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if not (fullname.startswith('evaluation.') or fullname.startswith('src.')
                    or fullname.startswith('diagnostics.')):
                return None
            mp = list(sys.meta_path)
            after = mp[mp.index(self) + 1:] if self in mp else mp
            spec = None
            for finder in after:
                if finder is self or not hasattr(finder, 'find_spec'):
                    continue
                spec = finder.find_spec(fullname, path, target)
                if spec is not None:
                    break
            if spec is None or spec.loader is None or not hasattr(spec.loader, 'exec_module'):
                return spec
            original = spec.loader.exec_module

            def exec_module(module, _original=original):
                _original(module)
                try:
                    patch_module(module)
                    if module.__name__.endswith('sdmpc_tangent_runtime'):
                        code = module.install.__code__
                        finder_ref['install_code'] = code
                        mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_RETURN)
                except Exception as exc:
                    note(exc)
            spec.loader.exec_module = exec_module
            return spec

    finder = PassiveFinder()
    finder_ref['finder'] = finder
    sys.meta_path.insert(0, finder)


if _OUT and _ON:
    try:
        _setup()
    except Exception as _exc:
        try:
            os.makedirs(_OUT, exist_ok=True)
            with open(os.path.join(_OUT, 'sa_setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
                _h.write(repr(_exc))
        except Exception:
            pass
