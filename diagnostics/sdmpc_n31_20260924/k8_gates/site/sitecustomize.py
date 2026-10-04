# K8 gate-tool site hook (ported from the K8 scratch harness, 2026-10-04). Diagnostics only.
# Loaded only through PYTHONPATH=<k8_gates>/site, which k8common.base_env sets for the child processes of
# capture.py / jobs.py / full.py. Inert unless K8_LONGPATH=1 or K8_HOOK_DIR is set.
#
# (1) K8_LONGPATH=1: long-path shim, load-bearing only for a code root under a long directory (the scratch copy
#     k8/r sat under a 121-char directory, and two pinned plant sources reached 260/276 characters; MAX_PATH 259,
#     LongPathsEnabled=0; pinlen.py lists such files for a given root). For an absolute path longer
#     than 259 characters ONLY, the OS call gets the '\\?\' form of the same path. Shorter paths are passed
#     through unchanged, so nothing that worked before can behave differently. No model value is touched.
# (2) K8_HOOK_DIR set: PASSIVE activation monitors (sys.monitoring PY_START/PY_RETURN, Python 3.12) on
#       physical_ramp_boundary.PhysicalRampBoundary.admit_current / finish_interval / apply_head_service (S1, S3)
#       control_area_objective.ModelAreaLedger.transfer                                   (S3 ledger zero return)
#       offramp_routing._future_distribution / inventory_enabled                           (S2)
#     plus, in the adapter process only, a one-shot profile on build_local_observation_summary (S4/S5, S9).
#     Callbacks read primal values only (x.value of a Dual; never a comparison/arithmetic on a Dual, never a
#     method that touches caches). Aggregated counters are written to <K8_HOOK_DIR>/hook_<pid>.json at exit
#     and every 20 s.
import os
import sys

_LP = os.environ.get('K8_LONGPATH') == '1'
_OUT = os.environ.get('K8_HOOK_DIR')


def _install_longpath():
    import builtins
    import io
    prefix = '\\\\?\\'

    def lp(p):
        try:
            s = os.fspath(p)
        except TypeError:
            return p
        if not isinstance(s, str) or s.startswith(prefix) or len(s) < 240:
            return p
        a = os.path.abspath(s)
        if len(a) <= 259:
            return p
        return prefix + a

    orig_open = io.open

    def k8_open(file, *args, **kwargs):
        return orig_open(lp(file) if not isinstance(file, int) else file, *args, **kwargs)
    io.open = k8_open
    builtins.open = k8_open

    def wrap1(name):
        orig = getattr(os, name)

        def f(path, *args, **kwargs):
            return orig(lp(path), *args, **kwargs)
        f.__name__ = name
        setattr(os, name, f)
    for name in ('stat', 'lstat', 'listdir', 'scandir', 'mkdir', 'remove', 'unlink', 'rmdir'):
        wrap1(name)

    def wrap2(name):
        orig = getattr(os, name)

        def f(src, dst, *args, **kwargs):
            return orig(lp(src), lp(dst), *args, **kwargs)
        f.__name__ = name
        setattr(os, name, f)
    for name in ('replace', 'rename'):
        wrap2(name)

    import ntpath
    orig_realpath = ntpath.realpath

    def k8_realpath(path, *args, **kwargs):
        q = lp(path)
        if q is path:
            return orig_realpath(path, *args, **kwargs)
        r = orig_realpath(q, *args, **kwargs)
        return r[4:] if isinstance(r, str) and r.startswith(prefix) else r
    ntpath.realpath = k8_realpath
    os.path.realpath = k8_realpath


if _LP:
    try:
        _install_longpath()
    except Exception as _e:  # never break the process
        sys.stderr.write('K8_LONGPATH_SETUP_ERROR %r\n' % (_e,))


def _setup_hooks():
    import atexit
    import importlib.abc
    import json
    import threading
    import time
    from collections import defaultdict

    mon = sys.monitoring
    ev = mon.events
    tool = None
    for candidate in (4, 3, 5):
        try:
            mon.use_tool_id(candidate, 'k8_passive')
            tool = candidate
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('no free sys.monitoring tool id')
    role = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else 'python'
    lock = threading.Lock()
    C = defaultdict(float)           # flat counters
    M = defaultdict(float)           # maxima
    BY = defaultdict(lambda: defaultdict(float))   # per-key counters
    EXTRA = {}
    state = {'last': time.time()}

    def primal(x):
        if x is None:
            return None
        v = getattr(x, 'value', x)
        try:
            return float(v)
        except Exception:
            return None

    def is_dual(x):
        return x is not None and not isinstance(x, (int, float)) and hasattr(x, 'value')

    def dump(final=False):
        try:
            os.makedirs(_OUT, exist_ok=True)
            rec = {'pid': os.getpid(), 'ppid': os.getppid(), 'role': role, 'argv': [str(a)[-120:] for a in sys.argv[:5]],
                   'final': final, 'wall': time.time(), 'counters': dict(C), 'maxima': dict(M),
                   'by_key': {k: dict(v) for k, v in BY.items()}, 'extra': EXTRA}
            tmp = os.path.join(_OUT, 'hook_%d.json.tmp' % os.getpid())
            with open(tmp, 'w', encoding='utf-8') as h:
                json.dump(rec, h)
            os.replace(tmp, os.path.join(_OUT, 'hook_%d.json' % os.getpid()))
        except Exception:
            pass

    def maybe_dump():
        now = time.time()
        if now - state['last'] > 20.0:
            state['last'] = now
            dump()

    atexit.register(lambda: dump(True))

    def mark(key, n=1.0):
        C[key] += n

    def mx(key, v):
        if v is not None and v > M.get(key, float('-inf')):
            M[key] = v

    # ------------------------------------------------------------- S1 / S3 ramp boundary
    def ramp_space_terms(me):
        up = sum(primal(n) or 0.0 for _, n in me._upstream)
        head = primal(me._head_ready) or 0.0
        down = sum(primal(n) or 0.0 for _, n in me._downstream)
        ready = primal(me._merge_ready) or 0.0
        cap = float(me.capacity_veh)
        total_free = max(0.0, cap - (up + head + down + ready))
        if me.head_position_m == 0:
            return total_free, total_free, up + head, None
        pre_cap = float(me.head_position_m) * me.lanes / float(me.spacing_m)
        pre = up + head
        fixed = min(total_free, max(0.0, pre_cap - pre))
        return total_free, fixed, pre, pre_cap

    def admit_start(frame):
        loc = frame.f_locals
        me, vehicles = loc.get('self'), loc.get('vehicles')
        if me is None:
            return
        with lock:
            amount = primal(vehicles)
            dual = is_dual(vehicles)
            cid = str(getattr(me, 'connector_id', '?'))
            mark('admit_calls')
            if dual:
                mark('admit_dual_calls')
                if amount == 0.0:
                    mark('S3_admit_zero_dual')
                    BY['S3_admit_zero_dual_by_cid'][cid] += 1
            if amount is None or amount <= 0.0:
                return
            mark('admit_positive')
            total_free, fixed, pre, pre_cap = ramp_space_terms(me)
            borrowed = max(0.0, amount - fixed)
            if pre_cap is not None and pre > pre_cap + 1e-9:
                mark('S1_prehead_overfull_at_admit')
                BY['S1_prehead_overfull_by_cid'][cid] += 1
            if borrowed > 1e-9:
                mark('S1_borrow_events')
                mark('S1_borrow_veh', borrowed)
                mx('S1_borrow_max_veh', borrowed)
                BY['S1_borrow_veh_by_cid'][cid] += borrowed
                BY['S1_borrow_events_by_cid'][cid] += 1
                if dual:
                    mark('S1_borrow_events_dual')
                    mark('S1_borrow_veh_dual', borrowed)
            maybe_dump()

    def finish_start(frame):
        loc = frame.f_locals
        me, req = loc.get('self'), loc.get('request_arrivals_veh')
        with lock:
            mark('finish_calls')
            r = primal(req)
            if r is not None and r > 0.0:
                mark('finish_requested_positive')
            if me is not None and (primal(getattr(me, 'backlog_veh', 0.0)) or 0.0) > 0.0:
                mark('finish_backlog_positive')

    def head_return(frame, result):
        with lock:
            mark('head_service_calls')
            if is_dual(result):
                mark('head_service_dual')
                if primal(result) == 0.0:
                    mark('S3_served_zero_dual')
                    me = frame.f_locals.get('self')
                    BY['S3_served_zero_dual_by_cid'][str(getattr(me, 'connector_id', '?'))] += 1

    def ledger_start(frame):
        loc = frame.f_locals
        v = loc.get('vehicles')
        with lock:
            mark('ledger_transfer_calls')
            if is_dual(v):
                mark('ledger_transfer_dual')
                if primal(v) == 0.0:
                    mark('S3_ledger_zero_dual')
                    BY['S3_ledger_zero_dual_by_source'][str(loc.get('source')).split(':', 1)[0]] += 1

    def future_start(frame):
        with lock:
            mark('S2_future_distribution_calls')

    def inventory_return(frame, result):
        with lock:
            mark('S2_inventory_enabled_true' if result else 'S2_inventory_enabled_false')

    start_handlers, return_handlers = {}, {}

    def enable(code, on_start=None, on_return=None):
        events = 0
        if on_start is not None:
            start_handlers[code] = on_start
            events |= ev.PY_START
        if on_return is not None:
            return_handlers[code] = on_return
            events |= ev.PY_RETURN
        mon.set_local_events(tool, code, events)

    def patch_prb(module):
        cls = module.PhysicalRampBoundary
        enable(cls.admit_current.__code__, admit_start)
        enable(cls.finish_interval.__code__, finish_start)
        enable(cls.apply_head_service.__code__, None, head_return)
        mark('patched_prb')

    def patch_cao(module):
        enable(module.ModelAreaLedger.transfer.__code__, ledger_start)
        mark('patched_cao')

    def patch_routing(module):
        enable(module._future_distribution.__code__, future_start)
        enable(module.inventory_enabled.__code__, None, inventory_return)
        mark('patched_routing')

    finder_ref = {}

    def install_return(frame, result):
        f = finder_ref.get('finder')
        if f is not None and f in sys.meta_path and sys.meta_path[0] is not f:
            sys.meta_path.remove(f)
            sys.meta_path.insert(0, f)
            mark('tangent_install_seen')

    def patch_runtime(module):
        enable(module.install.__code__, None, install_return)
        mark('patched_tangent_runtime')

    targets = {'evaluation.controllers.physical_ramp_boundary': patch_prb,
               'evaluation.controllers.control_area_objective': patch_cao,
               'evaluation.controllers.offramp_routing': patch_routing,
               'evaluation.controllers.sdmpc_tangent_runtime': patch_runtime}

    def on_start(code, offset):
        h = start_handlers.get(code)
        if h is not None:
            try:
                frame = sys._getframe(1)
                while frame is not None and frame.f_code is not code:
                    frame = frame.f_back
                if frame is not None:
                    h(frame)
            except Exception as exc:
                C['hook_errors'] += 1
                EXTRA.setdefault('errors', []).append(repr(exc)[:200]) if len(EXTRA.get('errors', [])) < 5 else None

    def on_return(code, offset, retval):
        h = return_handlers.get(code)
        if h is not None:
            try:
                frame = sys._getframe(1)
                while frame is not None and frame.f_code is not code:
                    frame = frame.f_back
                if frame is not None:
                    h(frame, retval)
            except Exception as exc:
                C['hook_errors'] += 1
                EXTRA.setdefault('errors', []).append(repr(exc)[:200]) if len(EXTRA.get('errors', [])) < 5 else None

    mon.register_callback(tool, ev.PY_START, on_start)
    mon.register_callback(tool, ev.PY_RETURN, on_return)

    class PassiveFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname not in targets:
                return None
            spec = None
            mp = list(sys.meta_path)
            after = mp[mp.index(self) + 1:] if self in mp else mp
            for finder in after:
                if finder is self or not hasattr(finder, 'find_spec'):
                    continue
                spec = finder.find_spec(fullname, path, target)
                if spec is not None:
                    break
            if spec is None or spec.loader is None:
                return spec
            original = spec.loader.exec_module

            def exec_module(module, _original=original, _name=fullname):
                _original(module)
                try:
                    targets[_name](module)
                except Exception as exc:
                    C['patch_errors'] += 1
                    EXTRA['patch_error_' + _name] = repr(exc)[:300]
            spec.loader.exec_module = exec_module
            return spec

    finder = PassiveFinder()
    finder_ref['finder'] = finder
    sys.meta_path.insert(0, finder)

    # ------------------------------------------------------------- S4/S5 + S9 projection (adapter process only)
    if role.lower() == 'vissim_stackelberg_adapter.py' or os.environ.get('K8_PROJECTION_HOOK') == '1':
        def projection_return(frame):
            loc = frame.f_locals
            sj = loc.get('state_json') or {}
            local = sj.get('local_observation') or {}
            inst_counts = local.get('link_counts') or {}
            inst_stopped = local.get('link_stopped_counts') or {}
            link_counts = loc.get('link_counts') or {}
            stopped = loc.get('link_stopped_counts') or {}
            qsrc = loc.get('queue_source_by_link') or {}
            qcount = loc.get('queue_count_by_link') or {}
            scount = loc.get('storage_count_by_link') or {}
            slinks = loc.get('storage_links_by_link') or {}
            speeds = loc.get('link_speeds_kph') or {}
            w = dict(loc.get('speed_weight_by_storage') or {})
            m = dict(loc.get('speed_moment_by_storage') or {})
            moving_enabled = bool((loc.get('_moving_speed_diag') or {}).get('enabled'))
            rec = {'moving_speed_enabled': moving_enabled, 'links': len(link_counts)}
            # S5: stopped share assigned to storage, orig (stopped/count) vs residual (stopped - ready queue)
            orig_st = fixed_st = 0.0
            viol = viol_veh = 0.0
            by_src = defaultdict(float)
            for link, count in link_counts.items():
                link = str(link)
                c = float(count)
                n = float(scount.get(link, 0.0))
                if c <= 0.0 or n <= 0.0 or not slinks.get(link):
                    continue
                s = min(c, max(0.0, float(stopped.get(link, 0.0))))
                q = float(qcount.get(link, 0.0))
                o = n * min(1.0, s / c)
                src = qsrc.get(link)
                if src in ('contiguous', 'stopped_instant') and link in stopped:
                    if q > s + 1e-8:
                        viol += 1
                        viol_veh += q - s
                    f = max(0.0, s - q)
                    f = min(f, n)
                else:
                    f = o
                orig_st += o
                fixed_st += f
                by_src[str(src)] += o - f
            rec['S5_storage_stopped_orig_veh'] = orig_st
            rec['S5_storage_stopped_fixed_veh'] = fixed_st
            rec['S5_shift_105_to_15_veh'] = orig_st - fixed_st
            rec['S5_shift_by_source'] = dict(by_src)
            rec['S5_ready_queue_exceeds_stopped_links'] = viol
            rec['S5_ready_queue_exceeds_stopped_veh'] = viol_veh
            rec['storage_occupancy_total_veh'] = float(sum((loc.get('urban_link_storage_occupancy') or {}).values()))
            rec['storage_stopped_total_veh_reported'] = float(sum((loc.get('urban_link_storage_stopped') or {}).values()))
            # S9: storage speed weights count (orig) vs moving count (fixed), same moving-only speeds
            fw, fm = dict(w), dict(m)
            changed_links = 0
            for link, count in link_counts.items():
                link = str(link)
                c = float(count)
                sl = slinks.get(link) or []
                if c <= 0.0 or link not in speeds or not sl:
                    continue
                v = float(speeds[link])
                ic = float(inst_counts.get(link, 0.0) or 0.0)
                ist = float(inst_stopped.get(link, 0.0) or 0.0)
                wm = max(0.0, ic - ist)
                if wm < 0.5:
                    wm = 0.0
                if wm != c:
                    changed_links += 1
                for s_ in sl:
                    fw[s_] = fw.get(s_, 0.0) - c + wm
                    fm[s_] = fm.get(s_, 0.0) - c * v + wm * v
            orig = {k: m[k] / x for k, x in w.items() if x > 1e-9}
            fixed = {k: fm[k] / x for k, x in fw.items() if x > 1e-9}
            diffs = []
            dropped = [k for k in orig if k not in fixed]
            for k in orig:
                if k in fixed:
                    diffs.append((fixed[k] - orig[k], k, orig[k], fixed[k]))
            diffs.sort(key=lambda t: -abs(t[0]))
            rec['S9_storages_observed'] = len(orig)
            rec['S9_links_weight_changed'] = changed_links
            rec['S9_storages_changed_gt1pct'] = sum(1 for d, k, o, f in diffs if abs(d) > 0.01 * max(o, 1e-9))
            rec['S9_storages_to_nominal'] = len(dropped)
            rec['S9_mean_abs_delta_kph'] = (sum(abs(d) for d, *_ in diffs) / len(diffs)) if diffs else 0.0
            rec['S9_top'] = [[k, round(o, 2), round(f, 2)] for d, k, o, f in diffs[:12]]
            rec['S9_dropped_to_nominal'] = dropped[:20]
            EXTRA['projection'] = rec
            dump()

        def prof(frame, event, arg):
            if event == 'return' and frame.f_code.co_name == 'build_local_observation_summary':
                try:
                    projection_return(frame)
                except Exception as exc:
                    EXTRA['projection_error'] = repr(exc)[:300]
                sys.setprofile(None)
        sys.setprofile(prof)


if _OUT:
    try:
        _setup_hooks()
    except Exception as _exc:
        try:
            os.makedirs(_OUT, exist_ok=True)
            with open(os.path.join(_OUT, 'setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
                _h.write(repr(_exc))
        except Exception:
            pass
