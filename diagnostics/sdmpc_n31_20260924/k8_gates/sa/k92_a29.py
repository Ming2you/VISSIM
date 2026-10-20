"""K9-2 amendment 29 judge additions (K8_PREDECLARATION_AMENDMENT_29; user decisions D-K9-53, D-K9-54, D-K9-55).
Diagnostics only: no VISSIM, no adapter, no child process.  BLIND: verdicts, generalized paths, counts and sha only;
no objective or prediction value is printed or written.

1. Added fields.  The amendment 29 comparator (k92_compare at K9-2-5) adds to an amendment 27 report exactly
   ADDED_REPORT_KEY = 'old_root' (top level of a compare() report) and ADDED_CHECK_KEY = 'old_is_root_rs' (in every
   k92_checks entry whose rule is 'A_K92').  strip29(x) removes exactly these two from a compare() report or a judge
   row (judge_hard / judge_g2 / judge_g4_decision_full); same29(x4, x5) = the canonical JSON of strip29(x5) equals
   that of x4, every A_K92 check of x5 carries old_is_root_rs and (report form) x5 carries old_root -- the
   re-comparison of existing outputs (amendment 29 section 4).
2. rold29(rep0, rep5, group, tails): the amendment 27 R-old judge (k92_a27.rold_judge_k / rold_judge_r) on
   (rep0, strip29(rep5)): the R-old pairs judged again with this commit's comparator.
3. w12(row, n): the check amendment 29 adds to A28-W: the row's A_K92 checks are exactly n, each with exactly the
   keys A29_CHECK_KEYS and old_is_root_rs True.  A28-W itself (a28w.py of amendment 28, unchanged) reads
   strip29(row).
4. plant_source_same(text4, text5): judge_g4_plant, _blind and TOL_REL of two k92_gates.py texts are the same
   (ast dump): with the module blobs it reads unchanged, the G-K4 plant rows carry over by bytes before k92t
   (D-K9-55).
5. selftest(): the amendment 29 N table (this commit's N, the K9-2-4 N and the K9-2-0 N), a generated merge check of
   the K9-2 root rule, the synthetic A_K92 / A_K92-M / judge cases, strip29 / same29 / w12 / plant_source_same.
"""
import ast
import copy
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
AMENDMENT = 29
ADDED_REPORT_KEY = 'old_root'
ADDED_CHECK_KEY = 'old_is_root_rs'
A29_CHECK_KEYS = frozenset({'path', 'rule', 'ok', 'new_is_root_rs', 'old_is_root_rs', 'old_known'})
PLANT_NAMES = ('judge_g4_plant', '_blind', 'TOL_REL')
RS_KEY = '<root>/evaluation/controllers/runtime_setup.py'
LEAF_A_K92 = '/metadata/joint_leader_selection/tangent_derivatives[*]/transformed_source_sha256/' + RS_KEY


# ------------------------------------------------------------------------------------------------ 1. added fields
def canonical(x):
    return json.dumps(x, sort_keys=True, default=str)


def _is_report(x):
    return isinstance(x, dict) and 'new_root' in x and 'T' in x


def _a_k92(x):
    return [c for c in ((x or {}).get('k92_checks') or []) if isinstance(c, dict) and c.get('rule') == 'A_K92']


def strip29(x):
    """A copy of a compare() report or a judge row without the two amendment 29 fields."""
    y = copy.deepcopy(x)
    if not isinstance(y, dict):
        return y
    if _is_report(y):
        y.pop(ADDED_REPORT_KEY, None)
    for c in _a_k92(y):
        c.pop(ADDED_CHECK_KEY, None)
    return y


def added29(x):
    checks = _a_k92(x)
    rep = _is_report(x)
    return {'report': rep, 'old_root_key': (ADDED_REPORT_KEY in x) if rep else None,
            'old_root': x.get(ADDED_REPORT_KEY) if rep else None, 'a_k92_n': len(checks),
            'a_k92_with_key': sum(1 for c in checks if ADDED_CHECK_KEY in c),
            'a_k92_old_root_true': sum(1 for c in checks if c.get(ADDED_CHECK_KEY) is True)}


def _same_path(a, b):
    def n(p):
        return str(p).replace('\\', '/').rstrip('/').lower()
    return a is not None and b is not None and n(a) == n(b)


def same29(x4, x5, old_root=None):
    """x4 = the amendment 27 result (recorded or recomputed with the K9-2-4 judge), x5 = this commit's result of the
    same comparison.  ok = same after strip29 and the added fields present; old_root (report form): the declared old
    root must be the one x5 records."""
    a = added29(x5)
    keys = a['a_k92_with_key'] == a['a_k92_n'] and a['old_root_key'] is not False
    root = True if not a['report'] or old_root is None else _same_path(a['old_root'], old_root)
    same = canonical(strip29(x5)) == canonical(x4)
    return {'same': same, 'added_keys_present': keys, 'old_root_declared': root, 'added': a,
            'ok': same and keys and root}


# ------------------------------------------------------------------------------------------------ 2. R-old
def _a27():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import k92_a27
    return k92_a27


def rold29(rep0, rep5, group, tails):
    """rep0 = the K9-2-0 comparator report, rep5 = this commit's report; tails as k92_a27.rold_judge_r (normalized by the
    K9-2-0 N).  The amendment 27 R-old judge on (rep0, strip29(rep5)), with the group tag the R6 rows carry."""
    a27 = _a27()
    s = strip29(rep5)
    j = a27.rold_judge_k(rep0, s) if group == 'K' else a27.rold_judge_r(rep0, s, tails)
    j['group'] = group
    return j


# ------------------------------------------------------------------------------------------------ 3. A28-W check 12
def w12(row, n):
    checks = _a_k92(row)
    ok = (n is not None and len(checks) == n
          and all(set(c) == A29_CHECK_KEYS and c.get(ADDED_CHECK_KEY) is True for c in checks))
    return {'check': 'a_k92_old_root', 'ok': ok, 'n': len(checks), 'n_expected': n}


# ------------------------------------------------------------------------------------------------ 4. plant rows
def _plant_defs(text):
    out = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name in PLANT_NAMES:
            out[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in PLANT_NAMES
                                                  for t in node.targets):
            out[[t.id for t in node.targets if isinstance(t, ast.Name)][0]] = ast.dump(node, include_attributes=False)
    return out


def plant_source_same(text4, text5):
    a, b = _plant_defs(text4), _plant_defs(text5)
    differ = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return {'ok': all(n in a for n in PLANT_NAMES) and not differ, 'names': sorted(a), 'differ': differ}


# ------------------------------------------------------------------------------------------------ 5. self-test
G = 'D:/VISSIM-merge/k8_gate_trees/'
LIT = 'd:/vissim-merge/k8_gate_trees/'
SELFTEST_N29 = [
    # (raw, this commit's N, the K9-2-4 N, the K9-2-0 N)
    (G + 'k92b1/k921_t74_W/evaluation/controllers/runtime_setup.py', '<root>/evaluation/controllers/runtime_setup.py',
     '<root>/evaluation/controllers/runtime_setup.py', '<root>/k921_t74_w/evaluation/controllers/runtime_setup.py'),
    (G + 'k92b1/k921.build.json', LIT + 'k92b1/k921.build.json', '<root>/k921.build.json', '<root>/k921.build.json'),
    (G + 'k92b1/k921_t74_W/k921.build.json', '<root>/k921.build.json', '<root>/k921.build.json',
     '<root>/k921_t74_w/k921.build.json'),
    (G + 'k92b1/a25/k92b1_probe.build.json', LIT + 'k92b1/a25/k92b1_probe.build.json',
     '<root>/a25/k92b1_probe.build.json', '<root>/a25/k92b1_probe.build.json'),
    (G + 'k92attrib/a25', LIT + 'k92attrib/a25', '<root>', '<root>/a25'),
    (G + 'k92attrib/a25/x.py', LIT + 'k92attrib/a25/x.py', '<root>/x.py', '<root>/a25/x.py'),
    (G + 'k92attrib/t74_X1H1/evaluation/x.py', '<root>/evaluation/x.py', '<root>/evaluation/x.py',
     '<root>/t74_x1h1/evaluation/x.py'),
    (G + 'k92b1/a27/k925/diagnostics/x.json', '<root>/diagnostics/x.json', '<root>/diagnostics/x.json',
     '<root>/a27/k925/diagnostics/x.json'),
    (G + 'k92b1', LIT + 'k92b1', '<root>', '<root>'),
    (G + 'k92attrib', LIT + 'k92attrib', '<root>', '<root>'),
    (G + 'k92b1/a27', LIT + 'k92b1/a27', '<root>/a27', '<root>/a27'),
    (G + 'k92b1.x', LIT + 'k92b1.x', '<root>.x', '<root>.x'),
    (G + 'k91t/evaluation/a.py', '<root>/evaluation/a.py', '<root>/evaluation/a.py', '<root>/evaluation/a.py'),
    (G + 'k92b1x/a.py', '<root>/a.py', '<root>/a.py', '<root>/a.py'),
    ('D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/evaluation/a.py', '<root>/evaluation/a.py',
     '<root>/evaluation/a.py', '<root>/evaluation/a.py'),
]
MERGE_ROOTS = ['k92b1/k921_t74_W', 'k92b1/a25/ref_t74_CWf', 'k92b1/a27/k925', 'k92b1/a26decl/tc', 'k92attrib/t74_CW',
               'k92b1/vb_12345678']
MERGE_OTHER = ['k92b1', 'k92attrib', 'k92b1/a25', 'k92b1/a26decl', 'k92b1/a27', 'k92attrib/a25', 'k92attrib/a27']
MERGE_SUFFIX = ['', '/k921.build.json', '/evaluation/controllers/a.py', '/a.py', '/a25/a.py', '/k921_t74_W/a.py', '.x',
                ';y', '-z/a.py']


def _norm_with(cmp, n2, s):
    s = s.lower().replace('\\\\', '/').replace('\\', '/')
    for a, b in n2:
        s = re.sub(a, b, s)
    for a, b in cmp.N3:
        s = re.sub(a, b, s)
    return s


def _n2_variants(cmp, a27):
    k924 = [(a27.K92_ROOT_RULE_A27, b) if a == a27.K92_ROOT_RULE else (a27.GENERIC_RULE_A21, b)
            if a == a27.GENERIC_RULE_A29 else (a, b) for a, b in cmp.N2]
    k920 = [(a27.GENERIC_RULE_A21, b) if a == a27.GENERIC_RULE_A29 else (a, b) for a, b in cmp.N2
            if a != a27.K92_ROOT_RULE]
    return k924, k920


GROUPS29 = ('a25', 'a26decl', 'a27')
_NAME = re.compile(r'^[a-z0-9_]+$')


def _meaning(rest):
    """Amendment 27 section 2.1 read component by component (not by the regex): ('tree', rest below the root) when
    `rest` (the text after k8_gate_trees/) starts with a declared K9-2 tree root, else ('plain', rest)."""
    r = rest.lower()
    parts = r.split('/')

    def name(c):
        return bool(_NAME.match(c)) and c not in GROUPS29
    below = None
    if parts[0] == 'k92b1' and len(parts) >= 3 and parts[1] in GROUPS29 and name(parts[2]):
        below = parts[3:]
    elif parts[0] in ('k92b1', 'k92attrib') and len(parts) >= 2 and name(parts[1]):
        below = parts[2:]
    return ('tree', ''.join('/' + p for p in below)) if below is not None else ('plain', r)


def _merge_check(norm):
    """Generated strings: two strings share N only when they mean the same (the same rest below some declared tree
    root, or the same plain text); the same rest below two declared roots shares N."""
    by_n, by_m = {}, {}
    for base in MERGE_ROOTS + MERGE_OTHER:
        for suf in MERGE_SUFFIX:
            n, m = norm(G + base + suf), _meaning(base + suf)
            by_n.setdefault(n, set()).add(m)
            by_m.setdefault(m, set()).add(n)
    merged = sorted([n, sorted(ms)] for n, ms in by_n.items() if len(ms) > 1)
    split = sorted([list(m), sorted(ns)] for m, ns in by_m.items() if m[0] == 'tree' and len(ns) > 1)
    return merged, split


def _w(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _tree(path, rs, extra=None):
    _w(Path(path) / 'evaluation' / 'controllers' / 'runtime_setup.py', rs)
    for rel, data in (extra or {}).items():
        _w(Path(path) / rel, data)
    return Path(path)


def _dec(path, T, root_tag, rs_value, md=None, green=30.0, extra_src=None, csv='x\n'):
    src = {} if rs_value is None else {root_tag + '/evaluation/controllers/runtime_setup.py': rs_value}
    src.update({root_tag + '/' + k: v for k, v in (extra_src or {}).items()})
    doc = {'N_P_star': {}, 'N_UF_star': {}, 'ramp_metering': {}, 'vsl': {}, 'green_times': {'SC109_p3': green},
           'offsets': {}, 'inflow_outflow_allocation': {},
           'metadata': dict(md or {}, joint_leader_selection={
               'selected_objective': 1.0, 'held_objective': 1.0, 'warm_start_objective': 1.0,
               'selection_status': 'ok', 'converged': True, 'feasible': True,
               'tangent_derivatives': [{'transformed_source_sha256': src}]})}
    _w(Path(path) / ('action_%06d.json' % T), json.dumps(doc).encode('utf-8'))
    if csv is not None:
        _w(Path(path) / ('action_%06d.csv' % T), csv.encode('utf-8'))
    return Path(path)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def selftest():
    """No child process, no file outside a temporary folder."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import k92_a27 as a27
    import k92_compare as cmp
    import k92_gates as kg
    cases = []

    def case(name, ok, **kw):
        cases.append(dict({'case': name, 'ok': bool(ok)}, **kw))

    # N (D-K9-54): the table, the generated merge check, and K9-2-free strings as the K9-2-0 N
    n24, n20 = _n2_variants(cmp, a27)
    case('n2_rules', [a for a, _ in cmp.N2].count(a27.K92_ROOT_RULE) == 1
         and [a for a, _ in cmp.N2].count(a27.GENERIC_RULE_A29) == 1
         and [a for a, _ in cmp.N2].index(a27.K92_ROOT_RULE) < [a for a, _ in cmp.N2].index(a27.GENERIC_RULE_A29))
    for raw, w5, w4, w0 in SELFTEST_N29:
        g5, g4, g0 = cmp.norm_s(raw), _norm_with(cmp, n24, raw), _norm_with(cmp, n20, raw)
        case('N ' + raw[-50:], (g5, g4, g0) == (w5, w4, w0), got=[g5, g4, g0])
    m5, s5 = _merge_check(cmp.norm_s)
    m4, s4 = _merge_check(lambda s: _norm_with(cmp, n24, s))
    case('merge_only_same_meaning_k925', not m5 and not s5, merged=len(m5), split=len(s5), first=(m5 + s5)[:3])
    case('merge_k924_shows_o2', len(m4) > 0 and not s4, merged=len(m4))
    plain = ['D:/VISSIM-merge/k8_gate_trees/k91t/a.py', 'D:/VISSIM-merge/sim3-n31-k8/evaluation/a.py',
             'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43/x.json', 'ok', 'D:/x/k92b1/a.py']
    case('k92_free_strings_as_k920', all(cmp.norm_s(s) == _norm_with(cmp, n20, s) for s in plain))
    case('roots_k92attrib_group', not a27.tree_root_ok(G + 'k92attrib/a25') and a27.tree_root_ok(G + 'k92attrib/t74_CW')
         and not a27.tree_root_ok(G + 'k92b1'))

    keep_known, keep_cr = cmp.KNOWN_OLD_RS, a27.CR_FILES
    with tempfile.TemporaryDirectory(prefix='k92a29_') as td:
        t = Path(td)
        try:
            body = b'a = 1\nb = 2\n'
            lane = 'evaluation/controllers/lane_offramp_runtime.py'
            a27.CR_FILES = {lane: (_sha(body), _sha(body.replace(b'\n', b'\r\n')))}
            old_rs, new_rs = b'old rs\n', b'new rs\n'
            cmp.KNOWN_OLD_RS = frozenset({_sha(old_rs)})
            ro = _tree(t / 'k8_gate_trees' / 'ro', old_rs, {lane: body})
            rn = _tree(t / 'k8_gate_trees' / 'rn', new_rs, {lane: body})
            rx = _tree(t / 'k8_gate_trees' / 'rx', b'other rs\n', {lane: body})
            rcr = _tree(t / 'k8_gate_trees' / 'rcr', new_rs, {lane: body.replace(b'\n', b'\r\n')})
            rnone = t / 'k8_gate_trees' / 'rnone'
            rnone.mkdir(parents=True)
            tag_o, tag_n = 'd:/vissim-merge/k8_gate_trees/k92b1/a25/ref_t74_cwf', 'd:/vissim-merge/k8_gate_trees/k92b1/k921_t74_w'

            def pair(name, va=_sha(old_rs), vb=_sha(new_rs), md_o=None, md_n=None, green_n=30.0, xs_o=None, xs_n=None):
                o = _dec(t / name / 'o', 3750, tag_o, va, md=md_o, extra_src=xs_o)
                n = _dec(t / name / 'n', 3750, tag_n, vb, md=md_n, green=green_n, extra_src=xs_n)
                return o, n

            # A_K92 (D-K9-53: amendment 24 section 4.2 :270)
            o, n = pair('a1')
            r = cmp.compare(o, n, 3750, rn, old_root=ro)
            ak = [c for c in r['k92_checks'] if c.get('rule') == 'A_K92']
            case('a_k92_pass', r['verdict'] == 'PASS' and r['allowed_counts'].get('A_K92') == 1 and len(ak) == 1
                 and set(ak[0]) == A29_CHECK_KEYS and ak[0]['old_is_root_rs'] is True
                 and r['old_root'] == str(ro))
            r = cmp.compare(o, n, 3750, rn)
            case('a_k92_no_old_root', r['verdict'] == 'HOLD' and r['old_root'] is None
                 and r['unclassified'][0]['why'] == 'A_K92 condition false')
            r = cmp.compare(o, n, 3750, rn, old_root=rx)
            case('a_k92_old_not_old_root_rs', r['verdict'] == 'HOLD'
                 and [c['old_is_root_rs'] for c in r['k92_checks']] == [False])
            cmp.KNOWN_OLD_RS = frozenset()
            r = cmp.compare(o, n, 3750, rn, old_root=ro)
            case('a_k92_old_not_known', r['verdict'] == 'HOLD' and [c['old_known'] for c in r['k92_checks']] == [False])
            cmp.KNOWN_OLD_RS = frozenset({_sha(old_rs)})
            o2, n2 = pair('a5', vb='f' * 64)
            r = cmp.compare(o2, n2, 3750, rn, old_root=ro)
            case('a_k92_new_not_new_root_rs', r['verdict'] == 'HOLD'
                 and [c['new_is_root_rs'] for c in r['k92_checks']] == [False])
            r = cmp.compare(o, n, 3750, rnone, old_root=ro)
            case('a_k92_new_root_without_rs', r['verdict'] == 'HOLD')
            r = cmp.compare(o, n, 3750, rn, old_root=t / 'no_such_tree')
            case('a_k92_old_root_missing', r['verdict'] == 'HOLD')
            o3, n3 = pair('a8', va=None)
            r = cmp.compare(o3, n3, 3750, rn, old_root=ro)
            case('a_k92_presence', r['verdict'] == 'HOLD' and r['k92_checks'][0]['ok'] is False)

            # A_K92-M (D-K9-53: sides per amendment 24 section 4.2 :271, deterministic nodes at any depth)
            ev = b'{"schema": "ev"}'
            _w(rn / 'ev.json', ev)
            _w(ro / 'ev_old.json', ev)
            _w(rn / 'ev_old.json', ev)          # so that an old side read from the new root would pass
            keyed = {'seed': None, 'floor_key': None, 'evidence_sha256': {'k92_w': _sha(ev)},
                     'evidence_file': {'k92_w': 'ev.json'}}
            w = {'evidence_sha256': _sha(ev), 'u4_sha256': cmp.U4_SHA256, 'heads': ['a', 'b'], 'after': 1.0}
            o, n = pair('m1', md_n={'k92_w': w})
            case('k92m_new_side', cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'PASS')
            o, n = pair('m2', md_o={'k92_w': w})
            r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
            case('k92m_new_key_on_old_side', r['verdict'] == 'HOLD'
                 and any(c.get('why', '').startswith('side:') for c in r['k92_checks']))
            cap = {'before': {'x': 1.0}, 'after': {'x': 2.0}}
            o, n = pair('m3', md_o={'k92_attrib_capacity_override': cap})
            case('k92m_old_side', cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'PASS')
            o, n = pair('m4', md_n={'k92_attrib_capacity_override': cap})
            r = cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)
            case('k92m_old_key_on_new_side', r['verdict'] == 'HOLD'
                 and any(c.get('why', '').startswith('side:') for c in r['k92_checks']))
            for name, sub in (('k92m_deep_evidence', dict(w, x={'evidence_sha256': '0' * 64})),
                              ('k92m_deep_sha_leaf', dict(w, x={'y_sha256': 'a' * 64})),
                              ('k92m_sha_leaf_in_list', dict(w, heads=[{'z_sha256': 'a' * 64}])),
                              ('k92m_decisive_container', dict(w, u4_sha256={'v': cmp.U4_SHA256})),
                              ('k92m_deep_action_token', dict(w, x={'action_token': 't'}))):
                o, n = pair(name, md_n={'k92_w': sub})
                case(name, cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'HOLD')
            keyed_o = {'seed': None, 'floor_key': None,
                       'evidence_sha256': {'k92_attrib_capacity_override': _sha(ev)},
                       'evidence_file': {'k92_attrib_capacity_override': 'ev_old.json'}}
            # the same RS value on both sides: no A_K92 leaf, so only the A_K92-M rule decides
            o, n = pair('m9', va=_sha(new_rs), md_o={'k92_attrib_capacity_override': dict(cap, evidence_sha256=_sha(ev))})
            case('k92m_old_side_evidence_old_root',
                 cmp.compare(o, n, 3750, rn, keyed=keyed_o, old_root=ro)['verdict'] == 'PASS'
                 and cmp.compare(o, n, 3750, rn, keyed=keyed_o)['verdict'] == 'HOLD')
            _w(rn / 'ev_bad.json', b'{"schema": "other"}')
            keyed_bad = {'seed': None, 'floor_key': None, 'evidence_sha256': {'k92_w': _sha(ev)},
                         'evidence_file': {'k92_w': 'ev_bad.json'}}
            o, n = pair('m12', va=_sha(new_rs), md_n={'k92_w': w})
            case('k92m_evidence_file_differs', cmp.compare(o, n, 3750, rn, keyed=keyed_bad, old_root=ro)['verdict']
                 == 'HOLD' and cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'PASS')
            o, n = pair('m10', md_o={'k92_w': dict(w, after=0.5)}, md_n={'k92_w': w})
            case('k92m_both_sides_differ', cmp.compare(o, n, 3750, rn, keyed=keyed, old_root=ro)['verdict'] == 'HOLD')
            o, n = pair('m11', md_n={'k92_w': w})
            case('k92m_key_off', cmp.compare(o, n, 3750, rn, old_root=ro)['verdict'] == 'HOLD')

            # judge functions pass the old root (D-K9-53)
            o, n = pair('j1')
            g2 = kg.judge_g2(o, n, 3750, rn, None, ro)
            case('judge_g2_old_root', g2['verdict'] == 'PASS' and g2['allowed_counts'].get('A_K92') == 1)
            g4 = kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)
            case('judge_g4_old_root', g4['verdict'] == 'PASS' and g4['allowed_counts'].get('A_K92') == 1)
            case('judge_g4_cr_pair', kg.judge_g4_decision_full(o, n, 3750, rcr, None, ro)['verdict'] == 'INCOMPLETE')
            o, n = pair('j4', green_n=30.0 * (1 + 1e-12))
            case('judge_g4_explain', kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)['verdict'] == 'EXPLAIN')
            o, n = pair('j5', green_n=30.0 * (1 + 1e-12), xs_o={'evaluation/controllers/x.py': 'c' * 64},
                        xs_n={'evaluation/controllers/x.py': 'd' * 64})
            case('judge_g4_explain_needs_no_unclassified',
                 kg.judge_g4_decision_full(o, n, 3750, rn, None, ro)['verdict'] == 'FAIL')
            o, n = pair('j6')
            d6 = kg.judge_decisions([('x', str(o), str(n), 3750, str(rn), str(ro))])
            d5 = kg.judge_decisions([('x', str(o), str(n), 3750, str(rn))])
            case('judge_decisions_old_root', d6['verdict'] == 'PASS' and d5['verdict'] == 'FAIL'
                 and d5['rows']['x']['verdict'] == 'HOLD')
            h = kg.judge_hard(o, n, 3750, rn, None, old_root=ro)
            case('judge_hard_old_root', h['verdict_full'] == 'PASS')

            # strip29 / same29 / rold29 on the real report shape
            rep5 = cmp.compare(o, n, 3750, rn, old_root=ro)
            rep4 = strip29(rep5)
            case('strip29_exact', ADDED_REPORT_KEY not in rep4 and all(ADDED_CHECK_KEY not in c for c in _a_k92(rep4))
                 and set(rep5) - set(rep4) == {ADDED_REPORT_KEY} and len(_a_k92(rep4)) == len(_a_k92(rep5)) == 1
                 and set(_a_k92(rep4)[0]) == A29_CHECK_KEYS - {ADDED_CHECK_KEY})
            case('same29_ok', same29(rep4, rep5, old_root=ro)['ok'])
            bad = copy.deepcopy(rep5)
            bad['allowed_counts']['V'] = 99
            case('same29_other_field', not same29(rep4, bad)['ok'])
            bad = copy.deepcopy(rep5)
            _a_k92(bad)[0].pop(ADDED_CHECK_KEY)
            case('same29_missing_key', not same29(rep4, bad)['ok'] and same29(rep4, bad)['same'])
            case('same29_old_root_declared', not same29(rep4, rep5, old_root=rx)['ok'])
            row5 = kg.judge_g2(o, n, 3750, rn, None, ro)
            row4 = strip29(row5)
            case('same29_row', same29(row4, row5)['ok'] and not same29(row5, row5)['ok']
                 and all(ADDED_CHECK_KEY not in c for c in _a_k92(row4)))
            base = {'verdict': 'PASS', 'hard_verdict': 'SAME', 'h5_declared': [], 'unclassified_n': 0,
                    'unclassified': [], 'allowed_counts': {'A_K92': 1},
                    **{gg: {'same': True, 'diff_paths_generalized': []} for gg in ('H1', 'H2', 'H3', 'H4', 'H5')}}
            r5 = dict(copy.deepcopy(base), new_root='x', T=1, old_root='y',
                      k92_checks=[{'path': 'p', 'rule': 'A_K92', 'ok': True, 'new_is_root_rs': True,
                                   'old_is_root_rs': True, 'old_known': True}])
            jk = rold29(dict(strip29(r5)), r5, 'K', [])
            case('rold29_k', jk['verdict'] == 'PASS' and jk['group'] == 'K' and jk['identical'])

            # A28-W check 12
            c1 = {'path': LEAF_A_K92, 'rule': 'A_K92', 'ok': False, 'new_is_root_rs': True, 'old_is_root_rs': True,
                  'old_known': False}
            case('w12_ok', w12({'k92_checks': [dict(c1), dict(c1)]}, 2)['ok'])
            case('w12_false', not w12({'k92_checks': [dict(c1), dict(c1, old_is_root_rs=False)]}, 2)['ok'])
            case('w12_count', not w12({'k92_checks': [dict(c1)]}, 2)['ok'])
            case('w12_keys', not w12({'k92_checks': [dict(c1, extra=1)]}, 1)['ok']
                 and not w12({'k92_checks': [{k: v for k, v in c1.items() if k != 'old_is_root_rs'}]}, 1)['ok'])
        finally:
            cmp.KNOWN_OLD_RS, a27.CR_FILES = keep_known, keep_cr

    # plant rows carry over by bytes (D-K9-55)
    text = (HERE / 'k92_gates.py').read_text(encoding='utf-8')
    case('plant_source_same_self', plant_source_same(text, text)['ok'])
    case('plant_source_body_changed', not plant_source_same(
        text, text.replace("v = 'EXPLAIN'", "v = 'PASS'", 1))['ok'] and "v = 'EXPLAIN'" in text)
    case('plant_source_tol_changed', not plant_source_same(text, text.replace('TOL_REL = 1e-9', 'TOL_REL = 1e-6', 1))['ok']
         and 'TOL_REL = 1e-9' in text)
    ok = all(c['ok'] for c in cases)
    return {'schema': 'k92-a29-selftest/v1', 'cases': cases, 'n': len(cases), 'child_processes': 0,
            'verdict': 'PASS' if ok else 'FAIL'}


if __name__ == '__main__':
    r = selftest()
    print('K92_A29_SELFTEST %s n=%d bad=%s' % (r['verdict'], r['n'], [c['case'] for c in r['cases'] if not c['ok']]))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
    sys.exit(0 if r['verdict'] == 'PASS' else 1)
