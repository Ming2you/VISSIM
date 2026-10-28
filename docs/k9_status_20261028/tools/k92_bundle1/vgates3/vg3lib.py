"""VerifyGates 2 (k92t, amendment 30 section 5.4) shared helpers.  Written from the amendment texts; imports no
harness, driver or judge module (no sa_*, k92_*, k8b_*, k92t*, vg_ja*, vglib).  Paths, sha, JSON, a stub unpickler,
the K9-1 G5 leaf rule, the amendment 21/24/27/29 decision comparison (N, HARD, F, D, A_K92, four outcomes)."""
import hashlib
import json
import math
import os
import pickle
import re
import time
from pathlib import Path

PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
KB = SP / 'k92' / 'bundle1'
VG3 = KB / 'vgates3'
OUTV = VG3 / 'out'
LOG_MD = KB / 'LOG.md'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
SEALED = OK2 / 'sealed_s47'
OUT30 = OK2 / 'a30'
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
TREE = TK / 'a27' / 'k92t'
K91T_TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k91t')
NC3 = Path(r'D:/VISSIM_runs/20261001_v3c3')
SA_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
LABEL = 'k92t'

# amendment 24 sections 5.2 / 5.3 (definitions, typed here from the text)
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))
ROBS61_T = (1,) + tuple(range(150, 9001, 150))
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
F3_LIMIT = 5.0                                       # amendment 24 :345 (+5 vehicles)
WALL_LIMIT = 1.05 / 1.033718118959995                # amendment 24 :290 / :328 (1.0158)
W_KEY = 'SC109_W_SC108_to_E'
L_KEY = 'SC109_W_SC108_to_N_SC16'
W_REPR = '5209.8'                                    # amendment 24 section 2.1 (D-K9-34)
SEED_REPR = '1045.1612903225805'                     # amendment 24 section 2.2 (H-b)
META7 = ('k8b_p1', 'k8b_p2', 'k8b_p2_init', 'k8b_p4', 'k9_w1', 'k9_w2a', 'k9_f17b')
INPX_RAW = {47: '1895ca30542cd50542a9376d5e3c77ff184d65a009d97dbe55a65f0b31bbced0',
            31: '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e',
            43: '51478c397b3a2570fc2254a9fa8120a2415304942589f5fb5c2eb1b6858f2dda'}
INPX_NORM = 'b7f05dcd07042fce8a439529853429a642f4de7b998c96ede51ce8c2d1230eb3'   # amendment 25 section 1
# P0-3 174-chain links (amendment 24 :225, the pinned list) and the F frames (amendment 24 :340)
CHAIN_LINKS = (21, 173, 174, 10024, 10112, 10280, 10281, 10285, 10286, 10293, 10300, 10303, 1220000600)
CHAIN_KEYS = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')


def lp(p):
    s = os.path.abspath(str(p))
    return s if s.startswith('\\\\?\\') else '\\\\?\\' + s


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def sha_file(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def rjson(p, default=None):
    try:
        with open(lp(p), 'rb') as f:
            return json.loads(f.read().decode('utf-8-sig'))
    except (OSError, ValueError):
        return default


def wjson(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=True, default=repr) + '\n')
    os.replace(tmp, p)


def canon(x):
    return json.dumps(x, sort_keys=True, allow_nan=True, default=repr)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def jf_fixed():
    """Amendment 30 section 4.5: J / F values fixed = the sha256 of OUTK/judge/f.json and jb.json both in KB/LOG.md."""
    text = LOG_MD.read_text(encoding='utf-8')
    out = {}
    for n in ('f', 'jb'):
        p = OUTK / 'judge' / ('%s.json' % n)
        out[n] = p.is_file() and sha_file(p) in text
    return all(out.values()), out


# ================================================================================================ stub unpickler
class Stub(object):
    """Stand-in for a project class of a pickle (no project module is imported)."""
    _vg3_name = 'Stub'

    def __init__(self, *a, **k):
        self.__dict__['_vg3_args'] = a
        self.__dict__['_vg3_kw'] = k

    def __setstate__(self, st):
        if isinstance(st, tuple) and len(st) == 2 and (st[0] is None or isinstance(st[0], dict)):
            if st[0]:
                self.__dict__.update(st[0])
            if st[1]:
                self.__dict__.update(st[1])
        elif isinstance(st, dict):
            self.__dict__.update(st)
        else:
            self.__dict__['_vg3_state'] = st

    def __setitem__(self, k, v):
        self.__dict__.setdefault('_vg3_items', {})[k] = v

    def append(self, v):
        self.__dict__.setdefault('_vg3_list', []).append(v)

    def extend(self, vs):
        self.__dict__.setdefault('_vg3_list', []).extend(vs)

    def add(self, v):
        self.__dict__.setdefault('_vg3_set', []).append(v)


_STUBS = {}
_REAL = ('builtins', 'collections', 'copyreg', 'numpy', 'datetime', 'decimal', 'fractions', '_codecs', 'pathlib',
         'enum', 'functools', 'operator', 'types')


class StubUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.split('.')[0] in _REAL:
            return super().find_class(module, name)
        key = (module, name)
        if key not in _STUBS:
            _STUBS[key] = type(str(name), (Stub,), {'_vg3_name': '%s.%s' % key, '__module__': 'vg3stub'})
        return _STUBS[key]


def load_stub(p):
    with open(lp(p), 'rb') as f:
        return StubUnpickler(f).load()


def attr(o, name):
    if isinstance(o, dict):
        return o[name]
    d = getattr(o, '__dict__', {})
    if name in d:
        return d[name]
    if '_vg3_items' in d and name in d['_vg3_items']:
        return d['_vg3_items'][name]
    raise KeyError(name)


def num(v):
    if v is None:
        return None
    if isinstance(v, Stub):
        d = v.__dict__
        if 'value' in d:
            return num(d['value'])
        if d.get('_vg3_args'):
            return num(d['_vg3_args'][0])
        raise ValueError('stub without value')
    return float(v)


def template_caps(p):
    """owned[0].cfg.network.movement_capacity_by_movement_veh_h of a capture template.pickle (stub load)."""
    t = load_stub(p)
    caps = attr(attr(attr(attr(t, 'owned')[0], 'cfg'), 'network'), 'movement_capacity_by_movement_veh_h')
    if isinstance(caps, Stub):
        caps = caps.__dict__.get('_vg3_items') or {}
    return {str(k): num(v) for k, v in dict(caps).items()}


# ================================================================================================ K9-1 G5 leaves
# K9-1 G5 rule (amendment 19 r2 section 4.2 G5 / K8b section 3.3): numeric leaves = int / float (bool excluded) of
# dicts and lists, as floats; string leaves listed apart; a leaf is excluded when its lower-case path holds a timing
# word or a G5 exclusion word (substring rule).
G5_SKIP = ('wall', 'sec', 'time', 'rss', 'elapsed')
G5_EXCLUDE = ('template_sha256', '/tree', '/label', '/template', '/forecast_long', '/coord', '/job_path', '/eo_dir',
              '/replay', '/robs', '/root', 'path', 'python_hash_seed', 'capture_spec')
HASH_KEY = re.compile(r'(?<![a-z])sha(1|256)?(?![a-z])|hash')


def g5_leaves(doc):
    nums, strs, deep = {}, {}, [0]

    def walk(x, p, d):
        if d > 60:
            deep[0] += 1
            nums[p + '#depth_cut'] = float('nan')
            return
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            nums[p] = float(x)
        elif isinstance(x, str):
            strs[p] = x
        elif isinstance(x, dict):
            for k in x:
                walk(x[k], '%s/%s' % (p, k), d + 1)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, '%s[%d]' % (p, i), d + 1)
    walk(doc, '', 0)
    return nums, strs, deep[0]


def g5_excluded(key):
    k = key.lower()
    return any(s in k for s in G5_SKIP) or any(e.lower() in k for e in G5_EXCLUDE)


def same_float(x, y):
    return x == y or (math.isnan(x) and math.isnan(y))


def g5_compare(a, b, path_roots=(), tol_rel=None):
    """Numeric leaves bit-equal (NaN = NaN), string leaves equal except sha / hash keys and strings holding one of
    `path_roots` (lower-case, '/'), one-sided leaves (after exclusions) counted.  tol_rel: also count the numeric
    differences above that relative tolerance (EXPLAIN form)."""
    na, sa_, deep_a = g5_leaves(a)
    nb, sb_, deep_b = g5_leaves(b)
    roots = [str(r).replace('\\', '/').lower().rstrip('/') for r in path_roots]
    num_diff, num_above = [], []
    for k in sorted(set(na) & set(nb)):
        if g5_excluded(k):
            continue
        x, y = na[k], nb[k]
        if same_float(x, y):
            continue
        num_diff.append(k)
        if tol_rel is not None:
            rel = abs(x - y) / max(abs(x), abs(y), 1e-300)
            if not rel <= tol_rel:
                num_above.append(k)
    str_diff, hash_diff, path_diff = [], [], []
    for k in sorted(set(sa_) & set(sb_)):
        if g5_excluded(k) or sa_[k] == sb_[k]:
            continue
        if HASH_KEY.search(k.lower()):
            hash_diff.append(k)
            continue
        if any(r and r in v.replace('\\', '/').lower() for v in (sa_[k], sb_[k]) for r in roots):
            path_diff.append(k)
            continue
        str_diff.append(k)
    ka, kb = set(na) | set(sa_), set(nb) | set(sb_)
    one_a = sorted(k for k in ka - kb if not g5_excluded(k))
    one_b = sorted(k for k in kb - ka if not g5_excluded(k))
    num_one = sorted(k for k in set(na) ^ set(nb) if not g5_excluded(k))
    return {'numeric_common': len(set(na) & set(nb)), 'numeric_differ': len(num_diff), 'numeric_differ_paths': num_diff[:20],
            'numeric_above_tol': len(num_above), 'string_differ': len(str_diff), 'string_differ_paths': str_diff[:20],
            'hash_strings_differ': len(hash_diff), 'path_strings_differ': len(path_diff),
            'one_sided': len(one_a) + len(one_b), 'one_sided_paths': (one_a + one_b)[:20],
            'numeric_one_sided': len(num_one), 'numeric_one_sided_paths': num_one[:20], 'depth_cut': deep_a + deep_b}


# ================================================================================================ amendment 21 section 6 + 24 / 27 / 29
# N (amendment 21 section 6.1; K9-2 rule and one-component rule as amendment 29 section 2.5 reads)
N_RULES = (
    (re.compile(r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}'), '<root>'),
    (re.compile(r'd:/vissim-merge/sim3-n31-k8'), '<root>'),
    (re.compile(r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?|k92attrib/)'
                r'(?!(?:a25|a26decl|a27)(?![a-z0-9_]))[a-z0-9_]+(?=/|$)'), '<root>'),
    (re.compile(r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|'
                r'(?!(?:k92b1|k92attrib)(?![a-z0-9_]))[a-z0-9_]+)'), '<root>'),
    (re.compile(r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/(?:[a-z0-9_]+/)*?'
                r't[0-9]{6}(?:_[a-z0-9]+)*'), '<bundle>'),
    (re.compile(r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+'), '<run>'),
    (re.compile(r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+'), '<run>'),
)
N_NAMES = ((re.compile(r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+'), '<name>'), (re.compile(r'sdmpc31_v3c3_nc_s[0-9]+'), '<name>'))
GROUPS = ('a25', 'a26decl', 'a27')
NAME_OK = re.compile(r'^[a-z0-9_]+$')


def n_str(s):
    s = s.lower().replace('\\\\', '/').replace('\\', '/')
    for rx, rep in N_RULES:
        s = rx.sub(rep, s)
    for rx, rep in N_NAMES:
        s = rx.sub(rep, s)
    return s


def k92_root_by_components(s):
    """Amendment 27 section 2.1 / 29 section 2.5 read by path components (not by regex): every occurrence of
    'd:/vissim-merge/k8_gate_trees/' followed by k92b1/<name>, k92b1/<group>/<name> or k92attrib/<name> (<name> a whole
    component of [a-z0-9_], not a group name, followed by '/' or the end) becomes '<root>'.  Only the K9-2 part of
    N; used as a cross-check on the strings where the K9-2 words occur."""
    base = 'd:/vissim-merge/k8_gate_trees/'
    out, i = [], 0
    while True:
        j = s.find(base, i)
        if j < 0:
            out.append(s[i:])
            break
        out.append(s[i:j])
        rest = s[j + len(base):]
        comps = rest.split('/')

        def whole(k):        # component k is a whole component (followed by '/' or end) of [a-z0-9_]+
            return k < len(comps) and NAME_OK.match(comps[k] or '') is not None
        took = None
        if comps and comps[0] in ('k92b1', 'k92attrib'):
            if comps[0] == 'k92b1' and len(comps) > 2 and comps[1] in GROUPS and whole(2) and comps[2] not in GROUPS:
                took = 3
            elif whole(1) and comps[1] not in GROUPS:
                took = 2
        if took is not None:
            # a whole component: the char after it in `rest` must be '/' or the end
            consumed = '/'.join(comps[:took])
            nxt = rest[len(consumed):len(consumed) + 1]
            if nxt in ('', '/'):
                out.append('<root>')
                i = j + len(base) + len(consumed)
                continue
        out.append(base)
        i = j + len(base)
    return ''.join(out)


class Collision(Exception):
    pass


def n_doc(x, where='$'):
    if isinstance(x, dict):
        o = {}
        for k, v in x.items():
            nk = n_str(k)
            if nk in o:
                raise Collision('key collision after N at %s' % where)
            o[nk] = n_doc(v, where + '/' + nk)
        return o
    if isinstance(x, list):
        return [n_doc(v, where + '[]') for v in x]
    if isinstance(x, str):
        return n_str(x)
    return x


MISSING = object()


def ddiff(a, b, p, out):
    """Amendment 21 section 6.4 deep difference: dict key '/k', list element '[i]', a one-sided key = its path once,
    a list of other length = the list path once; kinds presence / type / list_length / value (int != float,
    bool != int)."""
    if a is MISSING or b is MISSING:
        if not (a is MISSING and b is MISSING):
            out.append((p, 'presence', a, b))
        return
    if type(a) is not type(b):
        out.append((p, 'type', a, b))
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((p + '/' + k, 'presence', a.get(k, MISSING), b.get(k, MISSING)))
            else:
                ddiff(a[k], b[k], p + '/' + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((p, 'list_length', None, None))
            return
        for i, (u, v) in enumerate(zip(a, b)):
            ddiff(u, v, '%s[%d]' % (p, i), out)
    elif a != b:
        out.append((p, 'value', a, b))


def gen(p):
    return re.sub(r'\[\d+\]', '[*]', p)


def last_comp(p):
    return re.sub(r'\[\d+\]$', '', p.rsplit('/', 1)[-1])


def parent_comp(p):
    head = p.rsplit('/', 1)[0]
    return re.sub(r'\[\d+\]$', '', head.rsplit('/', 1)[-1]) if '/' in head else ''


CONTROL7 = ('n_p_star', 'n_uf_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
V7 = frozenset(('/metadata/decision_wall_sec', '/metadata/prediction_wall_sec', '/prediction/wall_sec',
                '/run_provenance/inputs/state_json/path', '/run_provenance/inputs/state_json/sha256',
                '/metadata/run_provenance/inputs/state_json/path', '/metadata/run_provenance/inputs/state_json/sha256'))
L_T = frozenset(('candidate_elapsed_sec', 'candidate_time_overrun_sec', 'compile_or_load_sec', 'cpu_sec', 'cpu_started',
                 'created_at', 'cyclic_gc_cleanup_cpu_sec', 'cyclic_gc_cleanup_wall_sec', 'deadline_monotonic',
                 'decision_deadline_monotonic', 'decision_time_remaining_sec', 'decision_wall_sec', 'elapsed_sec',
                 'elapsed_since_start_sec', 'endpoint_cpu_sec', 'endpoint_sec', 'finished_at', 'first_call_sec',
                 'initializer_cpu_sec', 'initializer_generation_wall_sec', 'initializer_wall_sec',
                 'leader_time_budget_overrun_sec', 'local_score_cpu_sec', 'local_score_sec', 'overrun_sec',
                 'pool_started_monotonic', 'post_guard_pfo_wall_sec', 'prediction_wall_sec', 'preparation_copy_cpu_sec',
                 'preparation_copy_wall_sec', 'preparation_cpu_sec', 'preparation_serialization_cpu_sec',
                 'preparation_serialization_wall_sec', 'preparation_wall_sec', 'ready_monotonic', 'reverse_sec',
                 'scalar_export_sec', 'scalar_load_sec', 'scalar_sec', 'sdmpc_after_pfo_seconds', 'seconds',
                 'serialization_cpu_sec', 'serialization_wall_sec', 'solve_wall_sec', 'started', 'started_at',
                 'state_check_sec', 'sweep_sec', 'tangent_sec', 'task_cpu_sec', 'task_wall_sec',
                 'waiting_after_hold_sec', 'waiting_after_trials_sec', 'wall_sec', 'wall_sec_including_spawn'))
ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:z|[+-]\d{2}:?\d{2})?$', re.I)
HEX_RE = re.compile(r'^[0-9a-f]{16,128}$')
F2_RE = re.compile(r'(?i)(sha256|sha1|sha|token|fingerprint|digest|hash)$')
SUB = r'(?:[/\[].*)?'
R3_RULES = (
    ('R3-01', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)')),
    ('R3-02', re.compile(r'/(?:metadata/)?run_provenance/imported_modules' + SUB)),
    ('R3-03', re.compile(r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256')),
    ('R3-04', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)')),
    ('R3-05', re.compile(r'/(?:metadata/)?run_provenance/inputs/(?:adapter_py|calibration_json|control_mapping_json|'
                         r'detector_mapping_json|fixed_signal_schedule_py|intersection_adjacency_json|'
                         r'link_assignment_json|main_vbs_runner|numsim_default_yaml|parameters_json|parameters_py|'
                         r'storage_capacity_json|strict_signal_program_py|tuning_json|watchdog_wrapper)/path')),
    ('R3-06', re.compile(r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)')),
    ('R3-08', re.compile(r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/transformed_source_sha256' + SUB)),
)
R3_FILES = ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper')
CAO_KEY = '<root>/evaluation/controllers/control_area_objective.py'
RS_KEY = '<root>/evaluation/controllers/runtime_setup.py'
D3_RE = re.compile(r'^/(metadata/)?run_provenance/(imported_modules/[^/]+/sha256|signal_program_sha256/.+|'
                   r'numsim_git_commit|numsim_snapshot_commit|run_id)$')
D4_RE = re.compile(r'^/(metadata/)?run_provenance/inputs/([^/]+)/sha256$')
D5_RE = re.compile(r'^/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256/(.+)$')
D2_NAMES = frozenset(('territory_sha256', 'policy_sha256', 'receipt_sha256', 'lane_plant_manifest_sha256',
                      'numsim_src_sha256'))
H3_KEYS = ('selected_objective', 'held_objective', 'warm_start_objective', 'selection_status', 'converged', 'feasible')
KNOWN_OLD_RS = frozenset(('8a5aec79c79e24e568f5f419cb0d9a70f7580c2c8db62d1eadff3eab672f93e1',
                          'ea79be3a6b60b300e660a88e7c3ec76c2df8321ca6c06a756e9b40b08a862a53',
                          '0ba3fa61ef61c25a402b47429fdc666598c5a5f83c7a3dde45aed060570adc3b',
                          '38c7a58010c9461c8180ed585db46ed45bdd50593980ee498a2c3a7d7cf7f70d',
                          '472d7f9cc5174ab82d2a3767a3259e54798a436e7e10a36aa34710cf0a5d101a'))
K92M_ALL = ('/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding',
            '/metadata/k92_attrib_capacity_override', '/metadata/k92_attrib_head_173_p4_seed')


def is_f3(p, kind, a, b):
    if kind not in ('value', 'type'):
        return False
    leaf = last_comp(p)
    if leaf not in L_T or (leaf == 'seconds' and parent_comp(p) == 'final_check_reserve'):
        return False
    if is_num(a) and is_num(b):
        return True
    if isinstance(a, str) and isinstance(b, str) and ISO_RE.match(a) and ISO_RE.match(b):
        return True
    return a is None and b is None


def f_class(p, kind, a, b):
    if kind not in ('value', 'type'):
        return None
    if isinstance(a, str) and isinstance(b, str) and HEX_RE.match(a) and HEX_RE.match(b):
        return 'F1'
    if F2_RE.search(last_comp(p)) and ((isinstance(a, str) and isinstance(b, str)) or (a is None and b is None)):
        return 'F2'
    if is_f3(p, kind, a, b):
        return 'F3'
    return None


def d_rule(p):
    g, leaf = gen(p), last_comp(p)
    if leaf.endswith('action_token'):
        return 'D1'
    if leaf.endswith('evidence_sha256') or leaf in D2_NAMES or g.endswith('/physical_ramp_recorded_csv/sha256'):
        return 'D2'
    if (g.startswith('/metadata/') and not g.startswith('/metadata/run_provenance')
            and '/joint_leader_selection/' not in g and leaf.endswith('sha256')):
        return 'D2b'
    if D3_RE.match(g):
        return 'D3'
    m = D4_RE.match(g)
    if m and m.group(2) not in ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper', 'state_json'):
        return 'D4'
    m = D5_RE.match(g)
    if m and m.group(1) != CAO_KEY:
        return 'D5'
    return None


def under(p, top):
    return p == top or p.startswith(top + '/') or p.startswith(top + '[')


def hard_region(p):
    for f in CONTROL7 + ('prediction', 'prediction_error'):
        if under(p, '/' + f):
            return True
    for top in ('/metadata/sdmpc_state', '/metadata/sdmpc_active', '/metadata/far_measured_seeded'):
        if under(p, top):
            return True
    if p.startswith('/metadata/far_rate_est_') or p.startswith('/metadata/head_'):
        return True
    return any(under(p, '/metadata/joint_leader_selection/' + k) for k in H3_KEYS)


def progress_row(path):
    """Amendment 21 section 6.2 H3: the last row of action_T.joint.progress.jsonl holding objective and
    held_objective, as repr strings; MISSING when there is no such file / row."""
    if not Path(path).is_file():
        return MISSING
    last = MISSING
    with open(lp(path), 'r', encoding='utf-8') as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and 'objective' in r and 'held_objective' in r:
                last = {'objective': repr(r.get('objective')), 'held_objective': repr(r.get('held_objective'))}
    return last


def hard_parts(doc, prog):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    jls = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else None
    parts = {'H2': {('/' + k): doc.get(k, MISSING) for k in CONTROL7}, 'H3': {}, 'H4': {}, 'H5': {}}
    if jls is not None:
        for k in ('selected_objective', 'held_objective', 'warm_start_objective'):
            parts['H3']['/metadata/joint_leader_selection/' + k] = repr(jls[k]) if k in jls else MISSING
        for k in ('selection_status', 'converged', 'feasible'):
            parts['H3']['/metadata/joint_leader_selection/' + k] = jls.get(k, MISSING)
    else:
        parts['H3']['/metadata/joint_leader_selection'] = MISSING
    parts['H3']['#progress_last'] = prog
    parts['H4']['/metadata/sdmpc_state'] = md.get('sdmpc_state', MISSING)
    parts['H5']['/metadata/sdmpc_active'] = md.get('sdmpc_active', MISSING)
    parts['H5']['/metadata/far_measured_seeded'] = md.get('far_measured_seeded', MISSING)
    for k in md:
        if k.startswith('far_rate_est_') or k.startswith('head_'):
            parts['H5']['/metadata/' + k] = md[k]
    parts['H5']['/prediction'] = doc.get('prediction', MISSING)
    parts['H5']['/prediction_error'] = doc.get('prediction_error', MISSING)
    return parts


def raw_get(doc, path):
    cur = doc
    for part in path.strip('/').split('/'):
        if not isinstance(cur, dict):
            return MISSING
        hits = [k for k in cur if k.lower() == part]
        if len(hits) != 1:
            return MISSING
        cur = cur[hits[0]]
    return cur


def own_k92_roots(raw):
    """The K9-2 tree roots named by the strings of a raw document (amendment 29 section 6.3 'own root only')."""
    roots = set()
    rx = re.compile(r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?|k92attrib/)'
                    r'(?!(?:a25|a26decl|a27)(?![a-z0-9_]))[a-z0-9_]+(?=/|$)')

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            s = x.lower().replace('\\\\', '/').replace('\\', '/')
            for m in rx.finditer(s):
                roots.add(m.group(0))
    walk(raw)
    return sorted(roots)


def n_crosscheck(raw):
    """Strings of a raw document that hold a K9-2 word: regex N (K9-2 part) vs the component reading."""
    n, bad = 0, []
    k92 = (N_RULES[2][0],)

    def walk(x):
        nonlocal n
        if isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            s = x.lower().replace('\\\\', '/').replace('\\', '/')
            if 'k8_gate_trees/k92b1' in s or 'k8_gate_trees/k92attrib' in s:
                n += 1
                a = k92[0].sub('<root>', s)
                b = k92_root_by_components(s)
                if a != b and len(bad) < 10:
                    bad.append([s[:160], a[:160], b[:160]])
    walk(raw)
    return {'strings': n, 'disagree': len(bad), 'examples': bad}


def decision_compare(dir_old, dir_new, T, new_root, old_root):
    """Amendment 21 section 6 + 24 section 4.2 (key-off: no A_K92-M allowance, no H5 declared difference) + 29
    (A_K92 four conditions with old_root).  Returns verdict PASS / FAIL / HOLD / INCOMPLETE and blind details."""
    s6 = '%06d' % int(T)
    do, dn = Path(dir_old), Path(dir_new)
    rep = {'T': int(T), 'old': str(do), 'new': str(dn), 'new_root': str(new_root), 'old_root': str(old_root)}
    co, cn = do / ('action_%s.csv' % s6), dn / ('action_%s.csv' % s6)
    jo, jn = do / ('action_%s.json' % s6), dn / ('action_%s.json' % s6)
    miss = [str(p) for p in (co, cn, jo, jn) if not p.is_file()]
    if miss:
        rep.update(verdict='INCOMPLETE', why='missing %s' % miss)
        return rep
    h1 = sha_file(co) == sha_file(cn)
    raw_o, raw_n = rjson(jo), rjson(jn)
    if not isinstance(raw_o, dict) or not isinstance(raw_n, dict):
        rep.update(verdict='INCOMPLETE', why='unreadable action JSON')
        return rep
    try:
        A, B = n_doc(raw_o), n_doc(raw_n)
    except Collision as e:
        rep.update(verdict='INCOMPLETE', why=str(e))
        return rep
    rep['n_crosscheck'] = {'old': n_crosscheck(raw_o), 'new': n_crosscheck(raw_n)}
    rep['own_k92_roots_new'] = own_k92_roots(raw_n)
    rep['own_k92_roots_old'] = own_k92_roots(raw_o)
    po = progress_row(do / ('action_%s.joint.progress.jsonl' % s6))
    pn = progress_row(dn / ('action_%s.joint.progress.jsonl' % s6))
    PA, PB = hard_parts(A, po), hard_parts(B, pn)
    hard = {'H1': {'same': h1}}
    for g in ('H2', 'H3', 'H4', 'H5'):
        diffs = []
        for key in sorted(set(PA[g]) | set(PB[g])):
            ddiff(PA[g].get(key, MISSING), PB[g].get(key, MISSING), key, diffs)
        kept, n_v, n_f3 = [], 0, 0
        for p, kind, va, vb in diffs:
            if p in V7:
                n_v += 1
            elif is_f3(p, kind, va, vb):
                n_f3 += 1
            else:
                kept.append(gen(p))
        hard[g] = {'same': not kept, 'n_diff': len(kept), 'paths': sorted(set(kept))[:40], 'dropped_V': n_v,
                   'dropped_F3': n_f3}
    rep['hard'] = hard
    rep['hard_same'] = all(h['same'] for h in hard.values())
    diffs = []
    ddiff(A, B, '', diffs)
    rep['n_diff_total'] = len(diffs)
    allowed, uncl, checks = {}, [], []

    def allow(k):
        allowed[k] = allowed.get(k, 0) + 1
    rs_new = sha_file(Path(new_root) / 'evaluation/controllers/runtime_setup.py') if (
        Path(new_root) / 'evaluation/controllers/runtime_setup.py').is_file() else None
    rs_old = sha_file(Path(old_root) / 'evaluation/controllers/runtime_setup.py') if (
        old_root is not None and (Path(old_root) / 'evaluation/controllers/runtime_setup.py').is_file()) else None
    cao_new = sha_file(Path(new_root) / 'evaluation/controllers/control_area_objective.py') if (
        Path(new_root) / 'evaluation/controllers/control_area_objective.py').is_file() else None
    for p, kind, va, vb in diffs:
        if hard_region(p):
            continue
        g = gen(p)
        if any(under(p, k) for k in K92M_ALL):
            uncl.append((g, kind, 'A_K92-M key-off'))
            continue
        m5 = D5_RE.match(g)
        if m5 and m5.group(1) == RS_KEY:
            c = {'path': g, 'kind': kind, 'new_is_root_rs': isinstance(vb, str) and vb == rs_new,
                 'old_is_root_rs': isinstance(va, str) and va == rs_old,
                 'old_known': isinstance(va, str) and va in KNOWN_OLD_RS}
            c['ok'] = kind == 'value' and c['new_is_root_rs'] and c['old_is_root_rs'] and c['old_known']
            checks.append(dict(c, rule='A_K92'))
            if c['ok']:
                allow('A_K92')
            else:
                uncl.append((g, kind, 'A_K92 condition false'))
            continue
        d = d_rule(p)
        if d:
            uncl.append((g, kind, d))
            continue
        if p in V7:
            allow('V')
            continue
        rid = None
        for r_id, rx in R3_RULES:
            if rx.fullmatch(p):
                rid = r_id
                break
        if rid == 'R3-03':
            name = p.rsplit('/', 2)[-2]
            ok, f_sha = False, None
            if name in R3_FILES:
                rp = raw_get(raw_n, p[:-len('/sha256')] + '/path')
                rv = raw_get(raw_n, p)
                if isinstance(rp, str) and Path(rp).is_file() and isinstance(rv, str):
                    f_sha = sha_file(rp)
                    ok = rv == f_sha
            checks.append({'rule': 'R3-03', 'path': p, 'ok': ok})
            if ok:
                allow(rid)
            else:
                uncl.append((g, kind, 'R3-03 new value != new file sha'))
            continue
        if rid == 'R3-08':
            ok = bool(m5) and m5.group(1) == CAO_KEY and isinstance(vb, str) and cao_new is not None and vb == cao_new
            checks.append({'rule': 'R3-08', 'path': g, 'ok': ok})
            if ok:
                allow(rid)
            else:
                uncl.append((g, kind, 'R3-08 not the CAO key or new value != new CAO sha'))
            continue
        if rid is not None:
            allow(rid)
            continue
        fc = f_class(p, kind, va, vb)
        if fc:
            allow(fc)
            continue
        uncl.append((g, kind, 'not allowed'))
    agg = {}
    for u in uncl:
        agg[u] = agg.get(u, 0) + 1
    rep['allowed'] = allowed
    rep['checks'] = checks
    rep['unclassified_n'] = len(uncl)
    rep['unclassified'] = [{'path': k[0], 'kind': k[1], 'why': k[2], 'n': n} for k, n in sorted(agg.items())][:100]
    rep['verdict'] = 'FAIL' if not rep['hard_same'] else ('HOLD' if uncl else 'PASS')
    return rep


# ================================================================================================ tracebacks
TB_HEAD = 'Traceback (most recent call last):'
FRAME_RE = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>.+?)\s*$')
RUNTIME_DIRS = ('/evaluation/', '/vendor/', '/scripts/', '/src/')


def tb_signature(text):
    """(exception line, runtime frames (path from the runtime folder, line, function)) of the LAST traceback; None
    without a traceback / exception line.  Runtime = a frame path holding /evaluation/, /vendor/, /scripts/ or /src/
    (K8 amendment 13 G-EB-14 'same place, same exception')."""
    text = str(text or '')
    at = text.rfind(TB_HEAD)
    if at < 0:
        return None
    frames, exc = [], None
    for ln in text[at:].splitlines()[1:]:
        m = FRAME_RE.match(ln)
        if m:
            path = m.group('path').replace('\\', '/').lower()
            for d in RUNTIME_DIRS:
                i = path.find(d)
                if i >= 0 and '/k8_gates/' not in path:
                    frames.append((path[i + 1:], int(m.group('line')), m.group('func')))
                    break
            continue
        if ln.strip() and ln[:1] not in (' ', '\t'):
            exc = ln.strip()
            break
    if exc is None:
        return None
    return exc, tuple(frames)
