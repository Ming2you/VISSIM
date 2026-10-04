# K8-0b S3 31-site passive line hook (diagnostics only). Port of the K8 amend1 scratch hook
# scratchpad/k8/amend1/s3/site/sitecustomize.py (sha256 69c3665e29f716cf..., S3_WIDE.md §2). Loaded only through
# PYTHONPATH=<k8_gates>/s3site (s3run.py puts it first, in place of <k8_gates>/site). Inert unless K8_LONGPATH=1 or
# K8_HOOK_DIR is set.
#
# Port changes, nothing else: this header; the site table is SITES_K81 (rows byte-identical to the scratch hook,
# K7/K8-1 line numbers) or SITES_K82 (the six DEFECTS §4 rows re-anchored to the K8-2 commit's lines and text),
# selected by env K8_S3_ANCHORS = k81 (default) | k82; EXTRA['anchors'] records the table used. Site ids keep the
# K7 line numbers so the two tables are compared row by row.
#
# (1) K8_LONGPATH=1: the same long-path shim as k8_gates/site/sitecustomize.py (absolute paths > 259 chars only get
#     the '\\?\' form of the same path; shorter paths pass through unchanged; no model value is touched).
# (2) K8_HOOK_DIR set: PASSIVE line monitors (sys.monitoring LINE, Python 3.12) at the zero-transfer sites of
#     K8_REVIEW B5 plus their siblings and the DEFECTS §4 sites. At each site line the callback reads the
#     tested local(s) from frame.f_locals and classifies the value: plain float, reverse Dual with tape node,
#     reverse Dual with node 0 (primal-guard result), forward Dual. It never compares, adds, or calls a method on a
#     Dual; it reads .value / .node / .support / .tangent attributes only.
#     For every "drop" event (the site's ORIGINAL skip/cleanup predicate is true on the primal while the value
#     carries a tape node) it remembers (trace, node). At the start of Trace.jacobian (tape complete, no further
#     appends) one read-only forward sweep over copies-by-view of the tape arrays computes, for a fixed random
#     direction r over the control axes, the directional tangent t = J_node . r and the no-cancellation bound
#     s = |J_node| . |r| for every node; each event is then "exact nonzero" (|t| > 1e-13 s), "exact zero", or
#     "unevaluated". Counters go to <K8_HOOK_DIR>/hook_<pid>.json at exit and every 20 s.
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


# --------------------------------------------------------------------------------------------- site table
# id, file basename, line, anchor (must occur in that source line), kind, local name(s), tier
#   kinds: bool   'if x:'                     drop when primal == 0
#          not    'if not x:'                 drop when primal == 0
#          le0    'if x <= 0' / '<= 0.0'      drop when primal <= 0
#          gt0    'if x > 0.0'                drop when not primal > 0
#          eq0    'if x == 0'                 drop when primal == 0
#          le_eps 'if x <= 1e-12'             drop when primal <= 1e-12
#          abs_le_eps 'abs(x) <= 1e-12'       drop when |primal| <= 1e-12
#          cleanup dict comprehension '> 1e-12' on a dict local: each value with primal <= 1e-12 is dropped
#          listmax  'max(0.0, x[i])' over a list local: each element with primal <= 0 is replaced by float 0
SITES_K81 = [
    # --- K8_REVIEW B5 list (primary)
    ('SA:304', 'shared_approach.py', 304, 'if accepted:', 'bool', 'accepted', 'B5'),
    ('SA:310', 'shared_approach.py', 310, 'if value > 1e-12}', 'cleanup', 'bins', 'B5'),
    ('SC:325', 'sc2001_corridor.py', 325, 'if amount <= 0:', 'le0', 'amount', 'B5'),
    ('SC:341', 'sc2001_corridor.py', 341, 'if pending <= 1e-12:', 'le_eps', 'pending', 'B5'),
    ('SC:353', 'sc2001_corridor.py', 353, 'if amount > 1e-12}', 'cleanup', 'branches[key]', 'B5'),
    ('UFA:345', 'urban_flow_accounting.py', 345, 'if departed <= 0.0:', 'le0', 'departed', 'B5'),
    ('UFA:376', 'urban_flow_accounting.py', 376, 'if arrived <= 0.0:', 'le0', 'arrived', 'B5'),
    ('UFA:585', 'urban_flow_accounting.py', 585, 'if departed <= 0.0:', 'le0', 'departed', 'B5'),
    ('UFA:794', 'urban_flow_accounting.py', 794, 'if arrived <= 0.0:', 'le0', 'arrived', 'B5'),
    ('LOR:85', 'lane_offramp_runtime.py', 85, 'if n<=0:continue', 'le0', 'n', 'B5'),
    ('PRBbr:304', 'physical_ramp_branches.py', 304, 'if not tagged:', 'not', 'tagged', 'B5'),
    # --- same functions, same class (siblings found while reading the B5 functions)
    ('SA:307', 'shared_approach.py', 307, 'or left <= 0:', 'le0_left', 'left', 'sib'),
    ('SA:344', 'shared_approach.py', 344, 'if admitted:', 'bool', 'admitted', 'sib'),
    ('SC:336', 'sc2001_corridor.py', 336, '/total if total else 0.', 'bool', 'total', 'sib'),
    ('SC:337', 'sc2001_corridor.py', 337, 'if allocated:', 'bool', 'allocated', 'sib'),
    ('UFA:253', 'urban_flow_accounting.py', 253, 'if released > 0.0:', 'gt0', 'released', 'sib'),
    ('UFA:314', 'urban_flow_accounting.py', 314, 'if split and arrived > 0.0:', 'gt0_split', 'arrived', 'sib'),
    ('UFA:325', 'urban_flow_accounting.py', 325, 'if ramp_in <= 0.0:', 'le0', 'ramp_in', 'sib'),
    ('UFA:389', 'urban_flow_accounting.py', 389, 'if landed > 0.0:', 'gt0', 'landed', 'sib'),
    ('UFA:413', 'urban_flow_accounting.py', 413, 'if landed > 0.0 and movements:', 'gt0', 'landed', 'sib'),
    ('UFA:817', 'urban_flow_accounting.py', 817, 'if allowed > 0.0:', 'gt0', 'allowed', 'sib'),
    ('UFA:842', 'urban_flow_accounting.py', 842, 'if requested > 0.0 else 0.0', 'gt0', 'requested', 'sib'),
    ('UFA:887', 'urban_flow_accounting.py', 887, 'if extra > 0.0:', 'gt0', 'extra', 'sib'),
    ('UFA:892', 'urban_flow_accounting.py', 892, 'if abs(delta) <= 1.0e-12:', 'abs_le_eps', 'delta', 'sib'),
    ('LOR:80', 'lane_offramp_runtime.py', 80, '/limit if limit else 0.', 'bool', 'limit', 'sib'),
    # --- DEFECTS §4 sites, re-counted with the same machinery
    ('PRBbd:306', 'physical_ramp_boundary.py', 306, 'if served:', 'bool', 'served', 'D4'),
    ('PRBbd:331', 'physical_ramp_boundary.py', 331, 'if admitted:', 'bool', 'admitted', 'D4'),
    ('PRBbd:369', 'physical_ramp_boundary.py', 369, 'if amount:', 'bool', 'amount', 'D4'),
    ('CAO:607', 'control_area_objective.py', 607, 'if count == 0:', 'eq0', 'count', 'D4'),
    ('AFA:244', 'area_freeway_accounting.py', 244, 'max(0.0, ramp_in_by_link[link][i])', 'listmax', 'ramp_in_by_link[link]', 'D4'),
    ('AFA:390', 'area_freeway_accounting.py', 390, 'and ramp_in_by_link[link][i] > 0.0:', 'gt0_delta', 'ramp_in_by_link[link][i]', 'D4'),
]
# K8-2 commit: the six DEFECTS §4 rows at their new lines/text (module imports shift PRB/CAO by +1, AFA by +1
# and +2 comment lines before :244). All other rows are the SITES_K81 rows.
SITES_K82 = [
    # --- K8_REVIEW B5 list (primary)
    ('SA:304', 'shared_approach.py', 304, 'if accepted:', 'bool', 'accepted', 'B5'),
    ('SA:310', 'shared_approach.py', 310, 'if value > 1e-12}', 'cleanup', 'bins', 'B5'),
    ('SC:325', 'sc2001_corridor.py', 325, 'if amount <= 0:', 'le0', 'amount', 'B5'),
    ('SC:341', 'sc2001_corridor.py', 341, 'if pending <= 1e-12:', 'le_eps', 'pending', 'B5'),
    ('SC:353', 'sc2001_corridor.py', 353, 'if amount > 1e-12}', 'cleanup', 'branches[key]', 'B5'),
    ('UFA:345', 'urban_flow_accounting.py', 345, 'if departed <= 0.0:', 'le0', 'departed', 'B5'),
    ('UFA:376', 'urban_flow_accounting.py', 376, 'if arrived <= 0.0:', 'le0', 'arrived', 'B5'),
    ('UFA:585', 'urban_flow_accounting.py', 585, 'if departed <= 0.0:', 'le0', 'departed', 'B5'),
    ('UFA:794', 'urban_flow_accounting.py', 794, 'if arrived <= 0.0:', 'le0', 'arrived', 'B5'),
    ('LOR:85', 'lane_offramp_runtime.py', 85, 'if n<=0:continue', 'le0', 'n', 'B5'),
    ('PRBbr:304', 'physical_ramp_branches.py', 304, 'if not tagged:', 'not', 'tagged', 'B5'),
    # --- same functions, same class (siblings found while reading the B5 functions)
    ('SA:307', 'shared_approach.py', 307, 'or left <= 0:', 'le0_left', 'left', 'sib'),
    ('SA:344', 'shared_approach.py', 344, 'if admitted:', 'bool', 'admitted', 'sib'),
    ('SC:336', 'sc2001_corridor.py', 336, '/total if total else 0.', 'bool', 'total', 'sib'),
    ('SC:337', 'sc2001_corridor.py', 337, 'if allocated:', 'bool', 'allocated', 'sib'),
    ('UFA:253', 'urban_flow_accounting.py', 253, 'if released > 0.0:', 'gt0', 'released', 'sib'),
    ('UFA:314', 'urban_flow_accounting.py', 314, 'if split and arrived > 0.0:', 'gt0_split', 'arrived', 'sib'),
    ('UFA:325', 'urban_flow_accounting.py', 325, 'if ramp_in <= 0.0:', 'le0', 'ramp_in', 'sib'),
    ('UFA:389', 'urban_flow_accounting.py', 389, 'if landed > 0.0:', 'gt0', 'landed', 'sib'),
    ('UFA:413', 'urban_flow_accounting.py', 413, 'if landed > 0.0 and movements:', 'gt0', 'landed', 'sib'),
    ('UFA:817', 'urban_flow_accounting.py', 817, 'if allowed > 0.0:', 'gt0', 'allowed', 'sib'),
    ('UFA:842', 'urban_flow_accounting.py', 842, 'if requested > 0.0 else 0.0', 'gt0', 'requested', 'sib'),
    ('UFA:887', 'urban_flow_accounting.py', 887, 'if extra > 0.0:', 'gt0', 'extra', 'sib'),
    ('UFA:892', 'urban_flow_accounting.py', 892, 'if abs(delta) <= 1.0e-12:', 'abs_le_eps', 'delta', 'sib'),
    ('LOR:80', 'lane_offramp_runtime.py', 80, '/limit if limit else 0.', 'bool', 'limit', 'sib'),
    # --- DEFECTS §4 sites, re-counted with the same machinery
    ('PRBbd:306', 'physical_ramp_boundary.py', 307, 'if has_transfer(served):', 'bool', 'served', 'D4'),
    ('PRBbd:331', 'physical_ramp_boundary.py', 332, 'if has_transfer(admitted):', 'bool', 'admitted', 'D4'),
    ('PRBbd:369', 'physical_ramp_boundary.py', 370, 'if has_transfer(amount):', 'bool', 'amount', 'D4'),
    ('CAO:607', 'control_area_objective.py', 608, 'if count == 0 and not has_tape(count):', 'eq0', 'count', 'D4'),
    ('AFA:244', 'area_freeway_accounting.py', 247, 'max(ramp_in_by_link[link][i], 0.0)', 'listmax', 'ramp_in_by_link[link]', 'D4'),
    ('AFA:390', 'area_freeway_accounting.py', 393, 'or has_tape(ramp_in_by_link[link][i])):', 'gt0_delta', 'ramp_in_by_link[link][i]', 'D4'),
]
ANCHORS = os.environ.get('K8_S3_ANCHORS', 'k81')
if ANCHORS not in ('k81', 'k82'):
    raise SystemExit('K8_S3_ANCHORS must be k81 or k82')
SITES = SITES_K82 if ANCHORS == 'k82' else SITES_K81


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
            mon.use_tool_id(candidate, 'k8_s3_passive')
            tool = candidate
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('no free sys.monitoring tool id')
    DISABLE = mon.DISABLE
    role = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else 'python'
    lock = threading.RLock()
    C = defaultdict(float)
    BY = defaultdict(lambda: defaultdict(float))
    MAXV = defaultdict(float)
    SAMPLES = defaultdict(list)
    EXTRA = {'anchor_mismatch': [], 'patched_files': [], 'errors': [], 'sweeps': [], 'anchors': ANCHORS}
    state = {'last': time.time()}
    site_of_id = {s[0]: s for s in SITES}
    by_file = defaultdict(dict)
    for s in SITES:
        by_file[s[1]][s[2]] = s
    # pending events per trace: id(trace) -> (trace, [(site_id, node, primal, popcount)])
    PENDING = {}
    DONE_TRACES = set()

    def dump(final=False):
        try:
            os.makedirs(_OUT, exist_ok=True)
            with lock:
                pend = sum(len(v[1]) for v in PENDING.values())
                rec = {'pid': os.getpid(), 'ppid': os.getppid(), 'role': role,
                       'argv': [str(a)[-120:] for a in sys.argv[:5]], 'final': final, 'wall': time.time(),
                       'counters': dict(C), 'by_site': {k: dict(v) for k, v in BY.items()},
                       'max': dict(MAXV), 'samples': {k: v[:8] for k, v in SAMPLES.items()},
                       'pending_unevaluated_events': pend, 'extra': EXTRA}
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

    def final_dump():
        with lock:
            for key, (trace, events) in list(PENDING.items()):
                for sid, node, p, pc in events:
                    if sid.endswith('#probe'):
                        BY[sid[:-6]]['probe_unevaluated'] += 1
                    else:
                        BY[sid]['ev_unevaluated'] += 1
            PENDING.clear()
        dump(True)

    atexit.register(final_dump)

    # ------------------------------------------------------------------ value classification (attribute reads only)
    def classify(x):
        """('float'|'rdual'|'rdual0'|'fdual'|'other', primal, node, popcount)."""
        if x is None:
            return 'other', None, 0, 0
        if isinstance(x, (int, float)) and not hasattr(x, 'value'):
            return 'float', float(x), 0, 0
        v = getattr(x, 'value', None)
        try:
            p = float(v)
        except Exception:
            return 'other', None, 0, 0
        try:
            node = object.__getattribute__(x, 'node')
        except AttributeError:
            node = None
        if node is not None:
            sup = object.__getattribute__(x, 'support')
            pc = bin(sup).count('1') if isinstance(sup, int) else 0
            return ('rdual' if node else 'rdual0'), p, int(node), pc
        tan = getattr(x, 'tangent', None)
        if isinstance(tan, dict) and tan:
            return 'fdual', p, 0, len(tan)
        return 'rdual0', p, 0, 0

    def dropped(kind, p):
        if kind in ('bool', 'not', 'eq0'):
            return p == 0.0
        if kind in ('le0', 'le0_left', 'listmax'):
            return p <= 0.0
        if kind in ('gt0', 'gt0_split', 'gt0_delta'):
            return not (p > 0.0)
        if kind in ('le_eps', 'cleanup'):
            return p <= 1e-12
        if kind == 'abs_le_eps':
            return abs(p) <= 1e-12
        raise ValueError(kind)

    def bucket(p):
        if p == 0.0:
            return 'eq0'
        if p < 0.0:
            return 'lt0'
        if p <= 1e-12:
            return 'pos_le_eps'
        return 'gt_eps'

    def record(sid, kind, x, loc, extra_cond=True):
        cls, p, node, pc = classify(x)
        B = BY[sid]
        B['values_seen'] += 1
        if cls == 'other' or p is None:
            B['values_other'] += 1
            return
        B['values_' + cls] += 1
        if not dropped(kind, p) or not extra_cond:
            if cls == 'rdual' and B['probe_taken'] < 200:
                # detector self-check: a few non-dropped taped values are classified by the same sweep
                trace = getattr(x, 'trace', None)
                if trace is not None:
                    B['probe_taken'] += 1
                    ent = PENDING.get(id(trace))
                    if ent is None:
                        ent = PENDING[id(trace)] = (trace, [])
                    ent[1].append((sid + '#probe', node, p, pc))
            return
        B['drop_' + cls] += 1
        if cls == 'float':
            if p != 0.0:
                B['drop_float_nonzero_primal'] += 1
                MAXV[sid + ':drop_float_abs_primal'] = max(MAXV[sid + ':drop_float_abs_primal'], abs(p))
            return
        B['drop_' + cls + '_' + bucket(p)] += 1
        if cls == 'rdual':
            B['ev_struct'] += 1
            MAXV[sid + ':ev_max_support'] = max(MAXV[sid + ':ev_max_support'], pc)
            MAXV[sid + ':ev_max_abs_primal'] = max(MAXV[sid + ':ev_max_abs_primal'], abs(p))
            trace = getattr(x, 'trace', None)
            if trace is not None:
                ent = PENDING.get(id(trace))
                if ent is None:
                    ent = PENDING[id(trace)] = (trace, [])
                ent[1].append((sid, node, p, pc))
            if len(SAMPLES[sid]) < 8:
                step = loc.get('urban_step_index', loc.get('step_idx', loc.get('step', loc.get('idx'))))
                SAMPLES[sid].append({'primal': p, 'node': node, 'support': pc,
                                     'step': step if isinstance(step, int) else None,
                                     'ctx': {k: str(loc.get(k))[:60] for k in ('key', 'movement', 'link', 'source', 'ramp', 'off', 'due')
                                             if k in loc}})
        elif cls == 'fdual':
            B['ev_struct'] += 1
            B['ev_fdual_tangent_nonzero'] += 1

    # ------------------------------------------------------------------ line handlers
    def handle(site, frame):
        sid, _, line, _, kind, name, _ = site
        loc = frame.f_locals
        B = BY[sid]
        B['reached'] += 1
        if kind == 'cleanup':
            if name == 'bins':
                d = loc.get('bins')
            else:
                br, key = loc.get('branches'), loc.get('key')
                d = br.get(key) if isinstance(br, dict) else None
            if not isinstance(d, dict):
                B['cleanup_no_dict'] += 1
                return
            for value in d.values():
                record(sid, kind, value, loc)
            return
        if kind == 'listmax':
            rib, link = loc.get('ramp_in_by_link'), loc.get('link')
            seq = rib.get(link) if isinstance(rib, dict) else None
            if seq is None:
                B['list_missing'] += 1
                return
            for value in seq:
                record(sid, kind, value, loc)
            return
        if kind == 'gt0_delta':
            rib, link = loc.get('ramp_in_by_link'), loc.get('link')
            i = loc.get('i')
            dm = loc.get('delta_m')
            try:
                x = rib[link][i]
            except Exception:
                B['list_missing'] += 1
                return
            cond = True
            try:
                cond = float(getattr(dm, 'value', dm)) > 0.0
            except Exception:
                pass
            if not cond:
                B['skipped_by_other_operand'] += 1
            record(sid, kind, x, loc, extra_cond=cond)
            return
        if kind == 'gt0_split':
            if not loc.get('split'):
                B['skipped_by_other_operand'] += 1
                return
            record(sid, kind, loc.get(name), loc)
            return
        if kind == 'le0_left':
            due, idx = loc.get('due'), loc.get('urban_step_index')
            cond = isinstance(due, int) and isinstance(idx, int) and due <= idx
            if not cond:
                B['skipped_by_other_operand'] += 1
            record(sid, kind, loc.get(name), loc, extra_cond=cond)
            return
        if name not in loc:
            B['local_missing'] += 1
            return
        record(sid, kind, loc[name], loc)
        if kind == 'le_eps' and sid == 'SC:341':
            cls, p, node, pc = classify(loc[name])
            if cls == 'rdual' and p <= 1e-12:
                dues, due = loc.get('dues') or [], loc.get('due')
                if due in dues and dues.index(due) < len(dues) - 1:
                    B['ev_struct_with_later_dues'] += 1

    code_sites = {}   # code -> {line: site}

    def on_line(code, line):
        sites = code_sites.get(code)
        site = sites.get(line) if sites else None
        if site is None:
            return DISABLE
        try:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is not None:
                with lock:
                    handle(site, frame)
                    maybe_dump()
        except Exception as exc:
            with lock:
                C['hook_errors'] += 1
                if len(EXTRA['errors']) < 8:
                    EXTRA['errors'].append(site[0] + ' ' + repr(exc)[:200])
        return None

    mon.register_callback(tool, ev.LINE, on_line)

    def all_codes(code):
        yield code
        for c in code.co_consts:
            if hasattr(c, 'co_lines'):
                yield from all_codes(c)

    def module_codes(module):
        seen = set()
        out = []

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

    def patch_sites(module, base):
        table = by_file.get(base)
        if not table:
            return
        try:
            with open(module.__file__, 'r', encoding='utf-8') as h:
                lines = h.read().splitlines()
        except Exception as exc:
            EXTRA['errors'].append('read ' + base + ' ' + repr(exc)[:120])
            return
        codes = module_codes(module)
        for line, site in table.items():
            text = lines[line - 1] if 0 < line <= len(lines) else ''
            if site[3] not in text:
                EXTRA['anchor_mismatch'].append([site[0], text.strip()[:120]])
                continue
            owners = [c for c in codes if any(ln == line for _, _, ln in c.co_lines())]
            if not owners:
                EXTRA['anchor_mismatch'].append([site[0], 'no code object owns the line'])
                continue
            # innermost owner = the one with the smallest first-line span containing the line
            owner = max(owners, key=lambda c: c.co_firstlineno)
            code_sites.setdefault(owner, {})[line] = site
            mon.set_local_events(tool, owner, mon.get_local_events(tool, owner) | ev.LINE)
            BY[site[0]]['patched'] += 1
        EXTRA['patched_files'].append([module.__name__, base])

    # ------------------------------------------------------------------ jacobian-start sweep (read-only)
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
            kernel['f'] = numba.njit(cache=False, nogil=False, fastmath=False)(sweep)
            kernel['np'] = np
        return kernel['f'], kernel['np']

    def jacobian_start(frame):
        trace = frame.f_locals.get('self')
        if trace is None or id(trace) in DONE_TRACES:
            return
        DONE_TRACES.add(id(trace))
        with lock:
            ent = PENDING.pop(id(trace), None)
        C['jacobian_traces'] += 1
        events = ent[1] if ent else []
        outputs = frame.f_locals.get('outputs') or []
        out_nodes = [int(getattr(v, 'node', 0) or 0) for v in outputs]
        t0 = time.time()
        f, np = get_kernel()
        n = len(trace.p1)
        n_axes = len(trace.steps)
        r = np.random.default_rng(20261004).standard_normal(n_axes)
        views = [np.frombuffer(trace.p1, dtype=np.int64), np.frombuffer(trace.p2, dtype=np.int64),
                 np.frombuffer(trace.w1, dtype=np.float64), np.frombuffer(trace.w2, dtype=np.float64),
                 np.frombuffer(trace.seed_nodes, dtype=np.int64), np.frombuffer(trace.seed_axes, dtype=np.int64),
                 np.frombuffer(trace.seed_weights, dtype=np.float64)]
        try:
            t, s = f(views[0], views[1], views[2], views[3], views[4], views[5], views[6], r, n)
        finally:
            del views
        with lock:
            for sid, node, p, pc in events:
                tv, sv = float(t[node]), float(s[node])
                probe = sid.endswith('#probe')
                B = BY[sid[:-6]] if probe else BY[sid]
                pre = 'probe_' if probe else 'ev_'
                if tv != 0.0 and (not (sv < float('inf')) or abs(tv) > 1e-13 * sv):
                    B[pre + 'exact_nonzero'] += 1
                    if not probe:
                        MAXV[sid + ':ev_max_abs_dir_tangent'] = max(MAXV[sid + ':ev_max_abs_dir_tangent'], abs(tv))
                elif tv != 0.0:
                    B[pre + 'exact_cancellation_level'] += 1
                else:
                    B[pre + 'exact_zero'] += 1
                if not probe:
                    MAXV[sid + ':ev_max_bound_s'] = max(MAXV[sid + ':ev_max_bound_s'], sv)
            EXTRA['sweeps'].append({'nodes': n - 1, 'axes': n_axes, 'events': len(events),
                                    'real_events': sum(1 for e in events if not e[0].endswith('#probe')),
                                    'sec': round(time.time() - t0, 2), 'rng_seed': 20261004,
                                    'out_nodes': out_nodes[:40],
                                    'out_t': [float(t[k]) if k else 0.0 for k in out_nodes[:40]],
                                    'out_s': [float(s[k]) if k else 0.0 for k in out_nodes[:40]]})
        del t, s
        dump()

    start_handlers = {}

    def on_start(code, offset):
        h = start_handlers.get(code)
        if h is None:
            return None
        try:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code is not code:
                frame = frame.f_back
            if frame is not None:
                h(frame)
        except Exception as exc:
            with lock:
                C['hook_errors'] += 1
                if len(EXTRA['errors']) < 8:
                    EXTRA['errors'].append('jacobian ' + repr(exc)[:300])
        return None

    mon.register_callback(tool, ev.PY_START, on_start)

    def patch_reverse(module):
        code = module.Trace.jacobian.__code__
        start_handlers[code] = jacobian_start
        mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_START)
        EXTRA['patched_files'].append([module.__name__, 'sdmpc_tangent_reverse.py'])

    TARGET_BASES = {os.path.splitext(b)[0] for b in by_file} | {'sdmpc_tangent_reverse'}
    finder_ref = {}

    class PassiveFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.rsplit('.', 1)[-1] not in TARGET_BASES:
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
            if spec is None or spec.loader is None or not spec.origin:
                return spec
            base = os.path.basename(spec.origin)
            original = spec.loader.exec_module

            def exec_module(module, _original=original, _base=base):
                _original(module)
                try:
                    if _base == 'sdmpc_tangent_reverse.py':
                        patch_reverse(module)
                    else:
                        patch_sites(module, _base)
                except Exception as exc:
                    C['patch_errors'] += 1
                    EXTRA['patch_error_' + _base] = repr(exc)[:300]
            spec.loader.exec_module = exec_module
            return spec

    finder = PassiveFinder()
    finder_ref['finder'] = finder
    sys.meta_path.insert(0, finder)

    # keep the passive finder in front when the tangent runtime inserts its own finder
    def install_return(code, offset, retval):
        if code is not finder_ref.get('install_code'):
            return None
        f = finder_ref.get('finder')
        if f is not None and f in sys.meta_path and sys.meta_path[0] is not f:
            sys.meta_path.remove(f)
            sys.meta_path.insert(0, f)
            C['tangent_install_seen'] += 1
        return None

    mon.register_callback(tool, ev.PY_RETURN, install_return)

    class RuntimeFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != 'evaluation.controllers.sdmpc_tangent_runtime':
                return None
            mp = list(sys.meta_path)
            after = mp[mp.index(self) + 1:] if self in mp else mp
            spec = None
            for f in after:
                if f is self or not hasattr(f, 'find_spec'):
                    continue
                spec = f.find_spec(fullname, path, target)
                if spec is not None:
                    break
            if spec is None or spec.loader is None:
                return spec
            original = spec.loader.exec_module

            def exec_module(module, _original=original):
                _original(module)
                code = module.install.__code__
                finder_ref['install_code'] = code
                mon.set_local_events(tool, code, mon.get_local_events(tool, code) | ev.PY_RETURN)
            spec.loader.exec_module = exec_module
            return spec

    sys.meta_path.insert(1, RuntimeFinder())


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
