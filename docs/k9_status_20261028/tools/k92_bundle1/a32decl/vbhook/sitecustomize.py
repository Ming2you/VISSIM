# K9-2 V-B measurement hook (K8_PREDECLARATION_AMENDMENT_32 section 3; user decision D-K9-63).  Diagnostics only,
# never committed.  READ-ONLY with respect to the program it is loaded into.
# Loaded only through the V-B launcher's extra PYTHONPATH entry (this folder holds this one file); the tangent worker
# processes inherit PYTHONPATH and the environment.  Inert unless env K92VB_HOOK_DIR is set.
# Same mechanism as the attribution-study hook (SP/k92/attrib/hook/sitecustomize.py, METHOD.md section 5.1):
# sys.monitoring (Python 3.12), one tool id, global PY_START; every code location that is not the target returns
# sys.monitoring.DISABLE.  Target (basename must match exactly): omega_costs in sdmpc.py, PY_START only.
# At each target call the hook runs the committed K9-2-0 recorder k92_record.py (blob aebc6f0e, sha256 of its bytes
# given in K92VB_RECORDER_SHA256 and verified once at setup) in a FRESH module namespace (the verified bytes compiled
# once, exec'ed into a new module object per call; nothing is inserted into sys.modules), through its own entry points:
#     network_facts(cfg); collect(point.control_area_response, T, dt); write(folder, job, T, dt, 3, None)
# with T = K92VB_T (the decision time), dt = cfg.simulation.T_c_sec, H = 3 blocks (450 s), keyed = None and
# job = {'label': K92VB_LABEL, 'harness': 'k92vb_hook', 'seed': K92VB_SEED, 'T': T}.  write() puts k92_record.json and
# k92_series.npz into <K92VB_HOOK_DIR>/c_<pid>_<seq:04d>/; the hook adds cand.json there (the action signature read
# from the caller frame's local `action`, flags, timing).  Choosing the candidate of the decision's written action is
# done afterwards by vb_select.py, outside the program.
# Reading rules (attribution hook rules): attribute reads, dict/list iteration, isinstance, number extraction only.  A
# number is taken as is when int/float, from an AD value only through its `.value` slot (an AD value is a class whose
# MRO holds `Dual` of module evaluation.controllers.sdmpc_dual), numpy scalars by float().  No method of a model object
# is called (dict get/items/keys excepted; the recorder's own reads are the same kind).  No `evaluation` / `src` module
# is imported.  Nothing reachable from a frame is written.  Every exception inside the hook is caught and written to
# hook_error_<pid>.txt (setup: hook_setup_error_<pid>.txt); nothing is raised into the original program.  The per-call
# folder number comes from a counter under a threading.Lock.
import os
import sys

_OUT = os.environ.get('K92VB_HOOK_DIR')
_TARGET = ('omega_costs', 'sdmpc.py')
_H = 3
_SCHEMA = 'k92vb-candidate/v1'


def _setup():
    import hashlib
    import json
    import threading
    import time
    import traceback
    import types

    mon = sys.monitoring
    lock = threading.Lock()
    pid = os.getpid()
    argv0 = os.path.basename(sys.argv[0]) if getattr(sys, 'argv', None) else ''
    os.makedirs(_OUT, exist_ok=True)
    rec_path = os.environ.get('K92VB_RECORDER', '')
    rec_want = os.environ.get('K92VB_RECORDER_SHA256', '')
    label = os.environ.get('K92VB_LABEL', '')
    loaded = {'schema': 'k92vb-loaded/v1', 'pid': pid, 'ppid': os.getppid(), 'argv0': argv0,
              'executable': os.path.basename(sys.executable or ''), 'python': sys.version.split()[0],
              'hook_out': _OUT, 'recorder': rec_path, 'recorder_sha256_expected': rec_want, 'label': label,
              'started_ns': time.time_ns()}
    try:
        T = float(os.environ['K92VB_T'])
        seed = int(os.environ['K92VB_SEED'])
        with open(rec_path, 'rb') as h:
            src = h.read()
        got = hashlib.sha256(src).hexdigest()
    except Exception:  # noqa: BLE001
        loaded['recorder_ok'] = False
        with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:
            json.dump(loaded, h)
        raise
    loaded.update(T=T, seed=seed, recorder_sha256=got, recorder_ok=(got == rec_want and len(rec_want) == 64))
    with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:
        json.dump(loaded, h)
    if not loaded['recorder_ok']:
        raise RuntimeError('K92VB: recorder bytes differ from K92VB_RECORDER_SHA256 (%s)' % got)
    code_obj = compile(src, rec_path, 'exec')
    tool = None
    for cand in (3, 4, 5, 1, 2):
        try:
            mon.use_tool_id(cand, 'k92vb_hook')
            tool = cand
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('K92VB: no free sys.monitoring tool id')
    DISABLE = mon.DISABLE
    state = {'seq': 0}

    def error(where):
        try:
            with lock:
                with open(os.path.join(_OUT, 'hook_error_%d.txt' % pid), 'a', encoding='utf-8') as h:
                    h.write('%s %s\n%s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), where, traceback.format_exc()))
        except Exception:  # noqa: BLE001
            pass

    def is_dual(v):
        try:
            for cls in type(v).__mro__:
                if cls.__name__ == 'Dual' and cls.__module__ == 'evaluation.controllers.sdmpc_dual':
                    return True
        except Exception:  # noqa: BLE001
            return False
        return False

    class Num:
        def __init__(self):
            self.ad = False
            self.bad = {}

        def __call__(self, v):
            t = type(v)
            if t is float or t is int:
                return float(v)
            if t is bool:
                self.bad['bool'] = self.bad.get('bool', 0) + 1
                return None
            if isinstance(v, float) or (isinstance(v, int) and not isinstance(v, bool)):
                return float(v)
            if is_dual(v):
                self.ad = True
                x = getattr(v, 'value', None)
                if type(x) is float or type(x) is int:
                    return float(x)
                self.bad['Dual.value:' + type(x).__name__] = self.bad.get('Dual.value:' + type(x).__name__, 0) + 1
                return None
            if getattr(t, '__module__', '') == 'numpy' and t.__name__ in ('float64', 'float32', 'int64', 'int32'):
                return float(v)
            if v is None:
                return None
            self.bad[t.__name__] = self.bad.get(t.__name__, 0) + 1
            return None

    def find_frame(code):
        f = sys._getframe(1)
        while f is not None and f.f_code is not code:
            f = f.f_back
        return f

    def callers(frame, n=3):
        out, f = [], frame.f_back if frame is not None else None
        while f is not None and len(out) < n:
            out.append([f.f_code.co_name, os.path.basename(f.f_code.co_filename)])
            f = f.f_back
        return out

    def caller_action(frame, n=3):
        f = frame.f_back if frame is not None else None
        level = 0
        while f is not None and level < n:
            loc = f.f_locals
            if 'action' in loc:
                return loc['action'], level + 1, f.f_code.co_name
            f = f.f_back
            level += 1
        return None, None, None

    def greens(d, num):
        if not isinstance(d, dict):
            return None
        return {str(k): num(v) for k, v in d.items()}

    def signature(action, num):
        if action is None:
            return None
        diag = getattr(action, 'diagnostics', None)
        fut = None
        if isinstance(diag, dict):
            seq = diag.get('sdmpc_prediction_sequence')
            if isinstance(seq, dict) and isinstance(seq.get('future'), list):
                fut = [greens(row.get('green_times'), num) if isinstance(row, dict) else None
                       for row in seq.get('future')]
        return {'green_times': greens(getattr(action, 'green_times', None), num),
                'offsets': greens(getattr(action, 'offsets', None), num),
                'future_green_times': fut}

    def candidate(frame):
        t0 = time.perf_counter()
        with lock:
            state['seq'] += 1
            seq = state['seq']
        folder = os.path.join(_OUT, 'c_%d_%04d' % (pid, seq))
        os.makedirs(folder)
        num = Num()
        L = frame.f_locals
        point, cfg = L.get('point'), L.get('cfg')
        meta = {'schema': _SCHEMA, 'seq': seq, 'pid': pid, 'ppid': os.getppid(), 'argv0': argv0,
                'thread': threading.get_ident(), 'time_ns': time.time_ns(), 'label': label, 'T': T, 'seed': seed,
                'H': _H, 'callers': callers(frame), 'recorder_sha256': got}
        act, level, fname = caller_action(frame)
        meta['action_from'] = [level, fname]
        meta['signature'] = signature(act, num)
        resp = getattr(point, 'control_area_response', None)
        rows = resp.get('residence') if isinstance(resp, dict) else None
        tr = resp.get('transfers') if isinstance(resp, dict) else None
        first = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else None
        meta['n_residence_rows'] = len(rows) if isinstance(rows, list) else None
        meta['n_transfer_rows'] = len(tr) if isinstance(tr, list) else None
        meta['first_row_start_sec'] = num(first.get('start_sec')) if first is not None else None
        if first is not None and isinstance(first.get('model_stock_veh'), dict):
            for i, v in enumerate(first['model_stock_veh'].values()):
                if i >= 50:
                    break
                if is_dual(v):
                    num.ad = True
                    break
        states = getattr(point, 'states', None)
        meta['n_states'] = len(states) if isinstance(states, (list, tuple)) else None
        dt = num(getattr(getattr(cfg, 'simulation', None), 'T_c_sec', None))
        meta['dt_sec'] = dt
        mod = types.ModuleType('k92_record')
        mod.__file__ = rec_path
        exec(code_obj, mod.__dict__)
        mod.network_facts(cfg)
        mod.collect(resp, T, dt)
        job = {'label': label, 'harness': 'k92vb_hook', 'seed': seed, 'T': T}
        rec = mod.write(folder, job, T, dt, _H, None)
        meta['record_errors'] = list(rec.get('errors') or []) if isinstance(rec, dict) else ['write returned no dict']
        meta['is_ad'] = bool(num.ad)
        meta['incomplete_types'] = dict(num.bad)
        meta['hook_sec'] = time.perf_counter() - t0
        with open(os.path.join(folder, 'cand.json'), 'w', encoding='utf-8') as h:
            json.dump(meta, h, separators=(',', ':'), default=str)

    def on_start(code, offset):
        try:
            if (code.co_name, os.path.basename(code.co_filename)) != _TARGET:
                return DISABLE
        except Exception:  # noqa: BLE001
            return DISABLE
        try:
            frame = find_frame(code)
            if frame is None:
                raise RuntimeError('target frame not found')
            candidate(frame)
        except Exception:  # noqa: BLE001
            error('on_start omega_costs')
        return None

    mon.register_callback(tool, mon.events.PY_START, on_start)
    mon.set_events(tool, mon.events.PY_START)


if _OUT:
    try:
        _setup()
    except Exception:  # noqa: BLE001
        try:
            import traceback as _tb
            os.makedirs(_OUT, exist_ok=True)
            with open(os.path.join(_OUT, 'hook_setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
                _h.write(_tb.format_exc())
        except Exception:  # noqa: BLE001
            pass
