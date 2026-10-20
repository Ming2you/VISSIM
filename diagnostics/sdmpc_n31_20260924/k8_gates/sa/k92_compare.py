"""K9-2 bundle 1 decision-output comparison (K8_PREDECLARATION_AMENDMENT_24 section 4.2 = amendment 21 section 6
unchanged + A_K92, A_K92-M and the declared H5 difference).  Diagnostics only.  BLIND: same / different, generalized
paths, kinds, counts and sha only -- no objective or prediction value is printed or written.

    compare(dir_old, dir_new, T, new_root, *, keyed=None, old_root=None, label='') -> report dict

dir_x holds action_<T>.json, action_<T>.csv and (SDMPC) action_<T>.joint.progress.jsonl.  "new" = the side whose new
values are checked against real files (the K9-2 run); old_root = the tree that produced dir_old (amendment 29).
Amendment 21 section 6 (ca369954...), ported unchanged from the K8 gate comparator (SP/j1/fix/gates/cmp21.py sha
see K9-2-0 README): N (6.1), HARD H1-H5 (6.2), F1-F3 / L_T 55 (6.3), D1-D5 (6.3a), allowed = (V u R3-01..06,08 u F) - D
with the R3-03 / R3-08 new-value file checks, verdicts PASS / FAIL / HOLD (= 보류) / INCOMPLETE (6.4).
Amendment 24 section 4.2 additions:
  A_K92    the D5 leaf .../transformed_source_sha256/<root>/evaluation/controllers/runtime_setup.py may differ in value
           only when the NEW value = the sha256 of the new root's RS bytes, the OLD value = the sha256 of the old
           root's RS bytes (old_root given; amendment 29) and the OLD value is one of the known RS bytes (b9734abe /
           OUTH / RR 8a5aec79, CWf ea79be3a, X1f 0ba3fa61, attribution CW 38c7a580, X1H1 472d7f9c); else unclassified.
  A_K92-M  key-on comparisons only (keyed given): the subtrees /metadata/k92_w, /metadata/k92_hb,
           /metadata/k92_hb_seed_binding may be present on the NEW side only and /metadata/k92_attrib_capacity_override,
           /metadata/k92_attrib_head_173_p4_seed on the OLD side only (amendment 29; present on the other side only, or
           on both sides and different = unclassified).  Their deterministic nodes at any depth (amendment 29: every
           node that an amendment 21 section 6.3a D rule names on the normalized (N) path, read from the normalized
           side document) must be one of: evidence_sha256 = the pinned sha
           (keyed['evidence_sha256'][subtree]) = the sha256 of that evidence file in the side's root
           (keyed['evidence_file'][subtree]; the old side's root = old_root); u4_sha256 = 22384c00...;
           rule_code_sha256 = d9bd5392...; else unclassified.
  H5 decl. key-on (keyed['seed'] set): HARD H5 path /metadata/head_discharge_floor_173_p4_<hash16> differs only as
           (a) new side only with value = seed, or (b) both sides with old < seed and new = seed, and in both cases the
           new side's /metadata/k92_hb_seed_binding = 1.0 and the key name = keyed['floor_key'] (P0-2 (f)); then the
           leaf is a declared expected difference (listed), else it stays a HARD difference.  head_observation_*
           counter differences are never allowed.
hard_verdict = SAME when H1-H5 are equal after the declared H5 exception (the probe rule 2 criterion).
Amendment 27 (K8_PREDECLARATION_AMENDMENT_27; D-K9-49): N2 holds one more rule, before the amendment-21
one-component gate-tree rule: the K9-2 tree roots D:/VISSIM-merge/k8_gate_trees/k92b1/<name>,
.../k92b1/{a25,a26decl,a27}/<name> and .../k92attrib/<name> -> <root>, <name> a whole path component (followed by
/ or the end of the string) that is not a group name (with one component stripped, the D5 keys of two K9-2 trees
never met and every one became a one-sided unclassified leaf).  The result of a comparison is
`verdict` (PASS / FAIL / HOLD / INCOMPLETE, amendment 21 section 6.4); hard_verdict is one part of it.
Amendment 29 (K8_PREDECLARATION_AMENDMENT_29; D-K9-53, D-K9-54): compare() takes old_root for the A_K92 old-value
condition and the old-side A_K92-M evidence (a report holds old_root, every A_K92 check holds old_is_root_rs), the
A_K92-M sides and depths above, and N2 exactly as amendment 27 section 2.1 reads: the group names are excluded on the
k92attrib branch too, and the amendment-21 one-component rule no longer takes the bundle folders k92b1 / k92attrib
themselves as a tree, so a bundle folder, a group folder or a file directly under them keeps its own text and never
meets a path inside a declared tree root."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BS = chr(92)
N2 = [
    (r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}', '<root>'),
    (r'd:/vissim-merge/sim3-n31-k8', '<root>'),
    (r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?|k92attrib/)(?!(?:a25|a26decl|a27)(?![a-z0-9_]))[a-z0-9_]+(?=/|$)', '<root>'),   # amendment 29 (K9-2 tree roots)
    (r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|(?!(?:k92b1|k92attrib)(?![a-z0-9_]))[a-z0-9_]+)', '<root>'),   # amendment 29 (bundle folders are not trees)
    (r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/(?:[a-z0-9_]+/)*?t[0-9]{6}(?:_[a-z0-9]+)*',
     '<bundle>'),
    (r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+', '<run>'),
    (r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+', '<run>'),
]
N3 = [(r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+', '<name>'), (r'sdmpc31_v3c3_nc_s[0-9]+', '<name>')]
CONTROL = ('n_p_star', 'n_uf_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
V = frozenset({'/metadata/decision_wall_sec', '/metadata/prediction_wall_sec', '/prediction/wall_sec',
               '/run_provenance/inputs/state_json/path', '/run_provenance/inputs/state_json/sha256',
               '/metadata/run_provenance/inputs/state_json/path', '/metadata/run_provenance/inputs/state_json/sha256'})
LT = frozenset('''candidate_elapsed_sec candidate_time_overrun_sec compile_or_load_sec cpu_sec cpu_started created_at
cyclic_gc_cleanup_cpu_sec cyclic_gc_cleanup_wall_sec deadline_monotonic decision_deadline_monotonic
decision_time_remaining_sec decision_wall_sec elapsed_sec elapsed_since_start_sec endpoint_cpu_sec endpoint_sec
finished_at first_call_sec initializer_cpu_sec initializer_generation_wall_sec initializer_wall_sec
leader_time_budget_overrun_sec local_score_cpu_sec local_score_sec overrun_sec pool_started_monotonic
post_guard_pfo_wall_sec prediction_wall_sec preparation_copy_cpu_sec preparation_copy_wall_sec preparation_cpu_sec
preparation_serialization_cpu_sec preparation_serialization_wall_sec preparation_wall_sec ready_monotonic reverse_sec
scalar_export_sec scalar_load_sec scalar_sec sdmpc_after_pfo_seconds seconds serialization_cpu_sec
serialization_wall_sec solve_wall_sec started started_at state_check_sec sweep_sec tangent_sec task_cpu_sec
task_wall_sec waiting_after_hold_sec waiting_after_trials_sec wall_sec wall_sec_including_spawn'''.split())
assert len(LT) == 55, len(LT)
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:z|[+-]\d{2}:?\d{2})?$', re.I)
HEX = re.compile(r'^[0-9a-f]{16,128}$')
F2_RE = re.compile(r'(?i)(sha256|sha1|sha|token|fingerprint|digest|hash)$')
_SUB = r'(?:[/\[].*)?'
R3 = (
    ('R3-01', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)')),
    ('R3-02', re.compile(r'/(?:metadata/)?run_provenance/imported_modules' + _SUB)),
    ('R3-03', re.compile(r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256')),
    ('R3-04', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)')),
    ('R3-05', re.compile(r'/(?:metadata/)?run_provenance/inputs/(?:adapter_py|calibration_json|control_mapping_json|'
                         r'detector_mapping_json|fixed_signal_schedule_py|intersection_adjacency_json|link_assignment_json|'
                         r'main_vbs_runner|numsim_default_yaml|parameters_json|parameters_py|storage_capacity_json|'
                         r'strict_signal_program_py|tuning_json|watchdog_wrapper)/path')),
    ('R3-06', re.compile(r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)')),
    ('R3-08', re.compile(r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/transformed_source_sha256' + _SUB)),
)
R3_FILE_NAMES = ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper')
CAO_KEY = '<root>/evaluation/controllers/control_area_objective.py'
RS_KEY = '<root>/evaluation/controllers/runtime_setup.py'
D3 = re.compile(r'^/(metadata/)?run_provenance/(imported_modules/[^/]+/sha256|signal_program_sha256/.+|numsim_git_commit|'
                r'numsim_snapshot_commit|run_id)$')
D4 = re.compile(r'^/(metadata/)?run_provenance/inputs/([^/]+)/sha256$')
D5 = re.compile(r'^/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256/(.+)$')
D2_NAMES = frozenset({'territory_sha256', 'policy_sha256', 'receipt_sha256', 'lane_plant_manifest_sha256',
                      'numsim_src_sha256'})
H3_KEYS = ('selected_objective', 'held_objective', 'warm_start_objective', 'selection_status', 'converged', 'feasible')
# amendment 24 section 4.2
KNOWN_OLD_RS = frozenset({'8a5aec79c79e24e568f5f419cb0d9a70f7580c2c8db62d1eadff3eab672f93e1',   # b9734abe / OUTH / RR
                          'ea79be3a6b60b300e660a88e7c3ec76c2df8321ca6c06a756e9b40b08a862a53',   # CWf
                          '0ba3fa61ef61c25a402b47429fdc666598c5a5f83c7a3dde45aed060570adc3b',   # X1f
                          '38c7a58010c9461c8180ed585db46ed45bdd50593980ee498a2c3a7d7cf7f70d',   # attribution CW
                          '472d7f9cc5174ab82d2a3767a3259e54798a436e7e10a36aa34710cf0a5d101a'})  # attribution X1H1
K92M = ('/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding', '/metadata/k92_attrib_capacity_override',
        '/metadata/k92_attrib_head_173_p4_seed')
# amendment 29 (amendment 24 section 4.2 :271): the side each one-sided subtree belongs to
K92M_NEW = ('/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding')
K92M_OLD = ('/metadata/k92_attrib_capacity_override', '/metadata/k92_attrib_head_173_p4_seed')
RS_REL = Path('evaluation') / 'controllers' / 'runtime_setup.py'
U4_SHA256 = '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b'
RULE_CODE_SHA256 = 'd9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106'
FLOOR_PREFIX = '/metadata/head_discharge_floor_173_p4_'
MISSING = object()


class Collision(Exception):
    pass


def norm_s(s):
    s = s.lower().replace(BS + BS, '/').replace(BS, '/')
    for a, b in N2:
        s = re.sub(a, b, s)
    for a, b in N3:
        s = re.sub(a, b, s)
    return s


def norm(x, where='$'):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            nk = norm_s(k)
            if nk in out:
                raise Collision('key collision after N at %s: %s' % (where, nk))
            out[nk] = norm(v, where + '/' + nk)
        return out
    if isinstance(x, list):
        return [norm(v, where + '[]') for v in x]
    if isinstance(x, str):
        return norm_s(x)
    return x


def deep_diff(a, b, p, out):
    if a is MISSING or b is MISSING:
        if not (a is MISSING and b is MISSING):
            out.append((p, 'presence', a, b))
        return
    if type(a) is not type(b):
        out.append((p, 'type', a, b))
        return
    if isinstance(a, dict):
        for k in sorted(a.keys() | b.keys()):
            if k not in a or k not in b:
                out.append((p + '/' + k, 'presence', a.get(k, MISSING), b.get(k, MISSING)))
            else:
                deep_diff(a[k], b[k], p + '/' + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((p, 'list_length', None, None))
            return
        for i, (u, v) in enumerate(zip(a, b)):
            deep_diff(u, v, p + '[%d]' % i, out)
    elif a != b:
        out.append((p, 'value', a, b))


def gen(p):
    return re.sub(r'\[\d+\]', '[*]', p)


def last(p):
    return re.sub(r'\[\d+\]$', '', p.rsplit('/', 1)[-1])


def parent(p):
    head = p.rsplit('/', 1)[0]
    return re.sub(r'\[\d+\]$', '', head.rsplit('/', 1)[-1]) if '/' in head else ''


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_f3(path, kind, a, b):
    if kind not in ('value', 'type'):
        return False
    leaf = last(path)
    if leaf not in LT:
        return False
    if leaf == 'seconds' and parent(path) == 'final_check_reserve':
        return False
    if is_num(a) and is_num(b):
        return True
    if isinstance(a, str) and isinstance(b, str) and ISO.match(a) and ISO.match(b):
        return True
    return a is None and b is None


def f_class(path, kind, a, b):
    if kind not in ('value', 'type'):
        return None
    if isinstance(a, str) and isinstance(b, str) and HEX.match(a) and HEX.match(b):
        return 'F1'
    if F2_RE.search(last(path)) and ((isinstance(a, str) and isinstance(b, str)) or (a is None and b is None)):
        return 'F2'
    if is_f3(path, kind, a, b):
        return 'F3'
    return None


def d_rule(path):
    g, l = gen(path), last(path)
    if l.endswith('action_token'):
        return 'D1'
    if l.endswith('evidence_sha256') or l in D2_NAMES or g.endswith('/physical_ramp_recorded_csv/sha256'):
        return 'D2'
    if (g.startswith('/metadata/') and not g.startswith('/metadata/run_provenance') and '/joint_leader_selection/' not in g
            and l.endswith('sha256')):
        return 'D2b'
    if D3.match(g):
        return 'D3'
    m = D4.match(g)
    if m and m.group(2) not in ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper', 'state_json'):
        return 'D4'
    m = D5.match(g)
    if m and m.group(1) != CAO_KEY:
        return 'D5'
    return None


def r3_item(path):
    for rid, rx in R3:
        if rx.fullmatch(path):
            return rid
    return None


def in_hard(path):
    for f in CONTROL + ('prediction', 'prediction_error'):
        top = '/' + f
        if path == top or path.startswith(top + '/') or path.startswith(top + '['):
            return True
    for top in ('/metadata/sdmpc_state', '/metadata/sdmpc_active', '/metadata/far_measured_seeded'):
        if path == top or path.startswith(top + '/') or path.startswith(top + '['):
            return True
    if path.startswith('/metadata/far_rate_est_') or path.startswith('/metadata/head_'):
        return True
    for k in H3_KEYS:
        top = '/metadata/joint_leader_selection/' + k
        if path == top or path.startswith(top + '/') or path.startswith(top + '['):
            return True
    return False


def progress_last(path):
    if not Path(path).is_file():
        return MISSING
    for line in reversed(Path(path).read_text(encoding='utf-8').splitlines()):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if (record.get('stage') or record.get('event')) == 'sdmpc_completed':
            return {'objective': repr(record.get('objective')), 'held_objective': repr(record.get('held_objective'))}
    return MISSING


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def hard_blocks(doc, progress):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    jls = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else None
    blocks = {'H2': {k: doc.get(k, MISSING) for k in CONTROL}, 'H3': {}, 'H4': {}, 'H5': {}}
    if jls is not None:
        for k in ('selected_objective', 'held_objective', 'warm_start_objective'):
            blocks['H3']['jls_' + k] = repr(jls[k]) if k in jls else MISSING
        for k in ('selection_status', 'converged', 'feasible'):
            blocks['H3']['jls_' + k] = jls.get(k, MISSING)
    else:
        blocks['H3']['jls'] = MISSING
    blocks['H3']['progress_last'] = progress
    blocks['H4']['sdmpc_state'] = md.get('sdmpc_state', MISSING)
    blocks['H5'] = {'sdmpc_active': md.get('sdmpc_active', MISSING),
                    'far_measured_seeded': md.get('far_measured_seeded', MISSING)}
    for k in md:
        if k.startswith('far_rate_est_') or k.startswith('head_'):
            blocks['H5'][k] = md[k]
    blocks['H5']['prediction'] = doc.get('prediction', MISSING)
    blocks['H5']['prediction_error'] = doc.get('prediction_error', MISSING)
    return blocks


def block_path(group, key):
    if group == 'H2':
        return '/' + key
    if group == 'H3':
        return '/metadata/joint_leader_selection/' + key[4:] if key.startswith('jls_') else '/#' + key
    if group == 'H4':
        return '/metadata/' + key
    if key in ('prediction', 'prediction_error'):
        return '/' + key
    return '/metadata/' + key


def _raw_get(doc, path):
    cur = doc
    for part in path.strip('/').split('/'):
        if not isinstance(cur, dict):
            return MISSING
        hits = [k for k in cur if k.lower() == part]
        if len(hits) != 1:
            return MISSING
        cur = cur[hits[0]]
    return cur


def h5_declared(path, kind, va, vb, B, keyed):
    """Amendment 24 section 4.2 H5 declared difference (key-on only)."""
    if not keyed or keyed.get('seed') is None or not path.startswith(FLOOR_PREFIX):
        return False
    s = keyed['seed']
    name = path[len('/metadata/'):]
    if keyed.get('floor_key') is None or name != keyed['floor_key']:
        return False
    md = B.get('metadata') if isinstance(B.get('metadata'), dict) else {}
    if md.get('k92_hb_seed_binding') != 1.0:
        return False
    if kind == 'presence' and va is MISSING and is_num(vb) and vb == s:
        return True                                                     # (a)
    if kind == 'value' and is_num(va) and is_num(vb) and va < s and vb == s:
        return True                                                     # (b)
    return False


def _nodes(x, p, out):
    """Every node below a subtree root (amendment 29), depth first in document order: (path, value)."""
    if isinstance(x, dict):
        for k, v in x.items():
            out.append((p + '/' + k, v))
            _nodes(v, p + '/' + k, out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out.append((p + '[%d]' % i, v))
            _nodes(v, p + '[%d]' % i, out)


def k92m_check(path, side_doc, keyed, side_root):
    """A_K92-M deterministic nodes of a one-sided subtree at any depth (amendment 29); returns (ok, why).
    side_doc = the normalized (N) document of that side, so that the D rules read the N path (amendment 21 section
    6.3a); side_root = the tree of that side (the old side: old_root, None when not given)."""
    name = path[len('/metadata/'):]
    sub = (side_doc.get('metadata') or {}).get(name, MISSING)
    if sub is MISSING:
        return False, 'subtree missing'
    nodes = []
    _nodes(sub, path, nodes)
    for q, v in nodes:
        leaf = last(q)
        if leaf == 'evidence_sha256':
            want = ((keyed or {}).get('evidence_sha256') or {}).get(name)
            rel = ((keyed or {}).get('evidence_file') or {}).get(name)
            f = Path(side_root) / rel if side_root is not None and rel else None
            actual = sha_file(f) if f is not None and f.is_file() else None
            if not (isinstance(v, str) and want is not None and v == want and actual == want):
                return False, 'evidence_sha256 != pinned / file sha'
        elif leaf == 'u4_sha256':
            if v != U4_SHA256:
                return False, 'u4_sha256'
        elif leaf == 'rule_code_sha256':
            if v != RULE_CODE_SHA256:
                return False, 'rule_code_sha256'
        elif d_rule(q) is not None:
            return False, 'unexpected decisive node %s' % gen(q)[len(path):]
    return True, ('ok' if isinstance(sub, dict) else 'leaf')


def compare(dir_old, dir_new, T, new_root, *, keyed=None, old_root=None, label=''):
    """keyed (key-on comparisons only): {'seed': s or None, 'floor_key': name or None,
    'evidence_sha256': {subtree: sha}, 'evidence_file': {subtree: repo-relative path}}.
    old_root (amendment 29): the tree that produced dir_old; None leaves every A_K92 leaf unclassified."""
    s6 = '%06d' % T
    do, dn = Path(dir_old), Path(dir_new)
    rep = {'T': T, 'label': label, 'old': str(do), 'new': str(dn), 'new_root': str(new_root),
           'old_root': None if old_root is None else str(old_root), 'keyed': bool(keyed)}
    co, cn = do / ('action_%s.csv' % s6), dn / ('action_%s.csv' % s6)
    jo, jn = do / ('action_%s.json' % s6), dn / ('action_%s.json' % s6)
    missing = [str(p) for p in (co, cn, jo, jn) if not p.is_file()]
    if missing:
        rep.update(verdict='INCOMPLETE', hard_verdict='INCOMPLETE', why='missing output: %s' % missing)
        return rep
    rep['H1'] = {'old_sha256': sha_file(co), 'new_sha256': sha_file(cn)}
    rep['H1']['same'] = rep['H1']['old_sha256'] == rep['H1']['new_sha256']
    raw_o = json.loads(jo.read_text(encoding='utf-8-sig'))
    raw_n = json.loads(jn.read_text(encoding='utf-8-sig'))
    rep['json_sha256'] = {'old': sha_file(jo), 'new': sha_file(jn)}
    try:
        A, B = norm(raw_o), norm(raw_n)
    except Collision as e:
        rep.update(verdict='INCOMPLETE', hard_verdict='INCOMPLETE', why=str(e))
        return rep
    BA = hard_blocks(A, progress_last(do / ('action_%s.joint.progress.jsonl' % s6)))
    BB = hard_blocks(B, progress_last(dn / ('action_%s.joint.progress.jsonl' % s6)))
    declared = []
    for group in ('H2', 'H3', 'H4', 'H5'):
        diffs = []
        for key in sorted(set(BA[group]) | set(BB[group])):
            deep_diff(BA[group].get(key, MISSING), BB[group].get(key, MISSING), block_path(group, key), diffs)
        kept, dv, df3 = [], [], []
        for p, kind, va, vb in diffs:
            if p in V:
                dv.append(p)
            elif is_f3(p, kind, va, vb):
                df3.append(p)
            elif group == 'H5' and h5_declared(p, kind, va, vb, B, keyed):
                declared.append({'path': gen(p), 'kind': kind})
            else:
                kept.append((p, kind))
        rep[group] = {'same': not kept, 'n_diff_leaves': len(kept), 'diff_kinds': sorted({k for _, k in kept}),
                      'diff_paths_generalized': sorted({gen(p) for p, _ in kept})[:80], 'dropped_V': sorted(set(dv)),
                      'dropped_F3_count': len(df3), 'dropped_F3_paths_generalized': sorted({gen(p) for p in df3})[:80]}
    rep['h5_declared'] = declared
    rep['hard_all_same'] = all(rep[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5'))
    rep['hard_verdict'] = 'SAME' if rep['hard_all_same'] else 'DIFFERENT'
    diffs = []
    deep_diff(A, B, '', diffs)
    rep['n_diff_leaves_total'] = len(diffs)
    allowed, unclassified, r3_checks, k92_checks = {}, [], [], []
    f_paths = {'F1': set(), 'F2': set(), 'F3': set()}
    for p, kind, va, vb in diffs:
        if in_hard(p):
            continue
        if p in K92M:
            if keyed and kind == 'presence':
                side = 'new' if va is MISSING else 'old'
                if side != ('new' if p in K92M_NEW else 'old'):
                    ok, why = False, 'side: belongs to the %s side only' % ('new' if p in K92M_NEW else 'old')
                else:
                    # the normalized documents: the D rules of amendment 21 section 6.3a read the N path
                    side_doc, side_root = (B, new_root) if side == 'new' else (A, old_root)
                    ok, why = k92m_check(p, side_doc, keyed, side_root)
                k92_checks.append({'path': p, 'side': side, 'ok': ok, 'why': why})
                if ok:
                    allowed['A_K92-M'] = allowed.get('A_K92-M', 0) + 1
                    continue
                unclassified.append({'path': p, 'kind': kind, 'why': 'A_K92-M ' + why})
                continue
            unclassified.append({'path': gen(p), 'kind': kind, 'why': 'A_K92-M: not one-sided or not key-on'})
            continue
        if any(p.startswith(x + '/') for x in K92M):
            unclassified.append({'path': gen(p), 'kind': kind, 'why': 'A_K92-M: both sides present and differ'})
            continue
        g = gen(p)
        m5 = D5.match(g)
        if m5 and m5.group(1) == RS_KEY:
            nf = Path(new_root) / RS_REL
            actual = sha_file(nf) if nf.is_file() else None
            of = Path(old_root) / RS_REL if old_root is not None else None
            old_actual = sha_file(of) if of is not None and of.is_file() else None
            new_is = actual is not None and vb == actual
            old_is = old_actual is not None and va == old_actual      # amendment 29 (amendment 24 section 4.2 :270)
            ok = (kind == 'value' and isinstance(vb, str) and new_is and isinstance(va, str) and old_is
                  and va in KNOWN_OLD_RS)
            k92_checks.append({'path': g, 'rule': 'A_K92', 'ok': ok, 'new_is_root_rs': new_is, 'old_is_root_rs': old_is,
                               'old_known': va in KNOWN_OLD_RS if isinstance(va, str) else False})
            if ok:
                allowed['A_K92'] = allowed.get('A_K92', 0) + 1
            else:
                unclassified.append({'path': g, 'kind': kind, 'why': 'A_K92 condition false'})
            continue
        d = d_rule(p)
        if d:
            unclassified.append({'path': g, 'kind': kind, 'why': d})
            continue
        if p in V:
            allowed['V'] = allowed.get('V', 0) + 1
            continue
        rid = r3_item(p)
        if rid == 'R3-03':
            name = p.rsplit('/', 2)[-2]
            if name in R3_FILE_NAMES:
                prefix = p[:-len('/sha256')]
                raw_path = _raw_get(raw_n, prefix + '/path')
                raw_sha = _raw_get(raw_n, p)
                ok = False
                actual = None
                if isinstance(raw_path, str) and Path(raw_path).is_file() and isinstance(raw_sha, str):
                    actual = sha_file(raw_path)
                    ok = raw_sha == actual
                r3_checks.append({'path': p, 'kind': kind, 'file': raw_path if isinstance(raw_path, str) else None,
                                  'new_value_is_file_sha256': ok, 'file_sha256': actual})
                if ok:
                    allowed[rid] = allowed.get(rid, 0) + 1
                else:
                    unclassified.append({'path': g, 'kind': kind, 'why': 'R3-03 new value != file sha256'})
                continue
            unclassified.append({'path': g, 'kind': kind, 'why': 'R3-03 other name'})
            continue
        if rid == 'R3-08':
            m = D5.match(g)
            if m and m.group(1) == CAO_KEY:
                cao = Path(new_root) / 'evaluation' / 'controllers' / 'control_area_objective.py'
                actual = sha_file(cao) if cao.is_file() else None
                newv = vb if isinstance(vb, str) else None
                ok = actual is not None and newv == actual
                r3_checks.append({'path': p, 'kind': kind, 'file': str(cao), 'new_value_is_file_sha256': ok,
                                  'file_sha256': actual})
                if ok:
                    allowed[rid] = allowed.get(rid, 0) + 1
                else:
                    unclassified.append({'path': g, 'kind': kind, 'why': 'R3-08 CAO new value != file sha256'})
                continue
            unclassified.append({'path': g, 'kind': kind, 'why': 'R3-08 not the CAO key'})
            continue
        if rid is not None:
            allowed[rid] = allowed.get(rid, 0) + 1
            continue
        fc = f_class(p, kind, va, vb)
        if fc:
            allowed[fc] = allowed.get(fc, 0) + 1
            f_paths[fc].add(g)
            continue
        unclassified.append({'path': g, 'kind': kind, 'why': 'not allowed'})
    rep['allowed_counts'] = allowed
    rep['f_paths_generalized'] = {k: sorted(v)[:80] for k, v in f_paths.items()}
    rep['f_paths_count'] = {k: len(v) for k, v in f_paths.items()}
    rep['r3_checks'] = r3_checks
    rep['k92_checks'] = k92_checks
    uniq = {}
    for u in unclassified:
        key = (u['path'], u['kind'], u['why'])
        uniq[key] = uniq.get(key, 0) + 1
    rep['unclassified_n'] = len(unclassified)
    rep['unclassified'] = [{'path': k[0], 'kind': k[1], 'why': k[2], 'count': n} for k, n in sorted(uniq.items())][:200]
    rep['sdmpc_active'] = {'old': (A.get('metadata') or {}).get('sdmpc_active'),
                           'new': (B.get('metadata') or {}).get('sdmpc_active')}
    if not rep['hard_all_same']:
        rep['verdict'] = 'FAIL'
    elif unclassified:
        rep['verdict'] = 'HOLD'
    else:
        rep['verdict'] = 'PASS'
    return rep


def numeric_hard(dir_a, dir_b, T, tol_rel=1e-9):
    """G-K4 helper: the HARD blocks H2-H5 of two decision outputs compared leaf by leaf, numbers within relative
    tol_rel (repr strings of the H3 objectives parsed back to floats), CSV bytes reported; returns counts / paths only."""
    s6 = '%06d' % T
    da, db = Path(dir_a), Path(dir_b)
    ja, jb = da / ('action_%s.json' % s6), db / ('action_%s.json' % s6)
    if not ja.is_file() or not jb.is_file():
        return {'T': T, 'status': 'INCOMPLETE'}
    A = norm(json.loads(ja.read_text(encoding='utf-8-sig')))
    B = norm(json.loads(jb.read_text(encoding='utf-8-sig')))
    BA = hard_blocks(A, progress_last(da / ('action_%s.joint.progress.jsonl' % s6)))
    BB = hard_blocks(B, progress_last(db / ('action_%s.joint.progress.jsonl' % s6)))
    worst, n_num, n_other, other = 0.0, 0, 0, []

    def as_num(x):
        if is_num(x):
            return float(x)
        if isinstance(x, str):
            try:
                return float(x)
            except ValueError:
                return None
        return None
    for group in ('H2', 'H3', 'H4', 'H5'):
        diffs = []
        for key in sorted(set(BA[group]) | set(BB[group])):
            deep_diff(BA[group].get(key, MISSING), BB[group].get(key, MISSING), block_path(group, key), diffs)
        for p, kind, va, vb in diffs:
            if p in V or is_f3(p, kind, va, vb):
                continue
            x, y = as_num(va), as_num(vb)
            if kind == 'value' and x is not None and y is not None:
                rel = abs(x - y) / max(abs(x), abs(y), 1e-300)
                worst = max(worst, rel)
                n_num += 1
                if rel > tol_rel:
                    other.append({'path': gen(p), 'rel': 'above'})
            else:
                n_other += 1
                other.append({'path': gen(p), 'kind': kind})
    csv_same = sha_file(da / ('action_%s.csv' % s6)) == sha_file(db / ('action_%s.csv' % s6))
    status = 'PASS' if not other else 'FAIL'
    return {'T': T, 'status': status, 'csv_same': csv_same, 'numeric_diffs': n_num, 'worst_rel': worst,
            'non_numeric_or_above': other[:50], 'n_problem': len(other)}


if __name__ == '__main__':
    r = compare(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4],
                old_root=sys.argv[6] if len(sys.argv) > 6 else None)       # argv[6] = old_root (amendment 29)
    if len(sys.argv) > 5:
        Path(sys.argv[5]).write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
    print('K92CMP T=%s verdict=%s hard=%s unclassified=%s allowed=%s' % (
        r['T'], r.get('verdict'), {g: r[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5') if g in r},
        r.get('unclassified_n'), r.get('allowed_counts')))
