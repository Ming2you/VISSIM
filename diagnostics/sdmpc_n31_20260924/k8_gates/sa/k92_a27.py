"""K9-2 amendment 27 comparison rules (K8_PREDECLARATION_AMENDMENT_27; user decisions D-K9-49, D-K9-50).
Diagnostics only: no VISSIM, no adapter, no child process.  BLIND: forms, verdicts, generalized paths, counts and sha
only; no objective or prediction value is printed or written.

1. Tree roots (amendment 27 section 2.1).  A K9-2 tree whose decision outputs are compared sits at
       D:/VISSIM-merge/k8_gate_trees/k92b1/<name>
       D:/VISSIM-merge/k8_gate_trees/k92b1/<group>/<name>      <group> in GROUPS = a25, a26decl, a27
       D:/VISSIM-merge/k8_gate_trees/k92attrib/<name>
   with <name> = [A-Za-z0-9_]+ (lower case after normalization N), a whole path component (followed by / or the end
   of the string) that is not itself a group name.  k92_compare.N2 maps exactly these roots to <root> with
   K92_ROOT_RULE, placed before the amendment-21 one-component gate-tree rule (review r2: a file or a group folder
   directly under k92b1 is not a root and keeps the amendment-21 one-component form).  tree_root_ok(path) tells
   whether a path is such a root.
2. CR pair rule (amendment 27 section 2.2).  CR_FILES = the 10 files of TK/cr_only_files.json (sha256 CR_LIST_SHA256)
   with the sha256 of their committed bytes (the b9734abe blob = FRZ_K8b bytes; the blob is the same at K9-2-1,
   K9-2-2 and K9-2-3) and of their git-archive bytes (core.autocrlf=true: every LF -> CRLF).  l_form(tree) gives per
   file C (committed bytes), A (archive bytes), X (other bytes: another blob) or - (absent).  cr_pair(ref_root,
   new_root) is ok when every file whose form in the reference tree is C or A has the same form in the new tree.
3. R-old (amendment 27 section 3.3, gate R4): existing outputs compared again with the K9-2-0 comparator blob (old)
   and this commit's comparator (new).  Group K (no K9-2 tree root in either output): the two reports are identical
   (canonical JSON).  Group R (outputs of K9-2 trees): rold_judge_r -- HARD results identical, every unclassified
   leaf that disappears is a D5 presence leaf under one of the two old-N tree tails (a root-depth artefact), every
   unclassified leaf that appears is a D5-family leaf at <root>/<rel> whose <rel> was such an artefact (value leaves:
   on both sides; presence leaves: on one side), allowed counts other than A_K92 / R3-08 identical except the
   path-string items PATH_ALLOWED (R3-02, R3-04, R3-05, R3-06), which may only stay or fall (a difference that was
   only the root depth disappears; review r2).
"""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
AMENDMENT = 27
GROUPS = ('a25', 'a26decl', 'a27')
K92_ROOT_RULE = (r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?(?!(?:a25|a26decl|a27)(?![a-z0-9_]))'
                 r'|k92attrib/)[a-z0-9_]+(?=/|$)')
_ROOT_FULL = re.compile('^' + K92_ROOT_RULE + '$')
CR_LIST_SHA256 = 'd7da2fe968a117180677e487cc2a8b45c3c5d6a9114230fa8940de17ead8312f'
CR_FILES = {
    'diagnostics/test_k8_s1_admission_owner.py': ('9f80cb5e2bfc92b18dc6a017645f7adb8bb117d96d53419948b956acba62e79d',
                                                  '8620e93ef8610e08f783636c6b132149134b5b093caccb5c52d959fbad9b0ee6'),
    'diagnostics/test_k8_s3_has_transfer.py': ('80ff6502da0787d2ab12b1e5e55e8313fb34e47e5bbfdb84f0d2c3b45565712f',
                                               'e6d16fde4e60842936c62233c7c8624215ce03c9675424ba9b2272102bc01a69'),
    'evaluation/controllers/lane_offramp_runtime.py': ('488a5afed8d27aec1ab3b397c963119d3bb24ffd4d4cce80babecd93363940a7',
                                                       'b425034c2208dec4ab1c0475de45e608775bb1f3a2bcbf01fb500282beb7e67e'),
    'evaluation/controllers/meter_spill.py': ('e2f3c21419bc257031cb3c81c509c51266494a38b9b8a6aa26a8432ca057c01a',
                                              '26e34e20d02a7c84b092e81195d6b0a26e247befb2b2fc3e6ab8629826c637a6'),
    'evaluation/controllers/offramp_split_forecast.py': ('e47b062492831b08f31caa084a10c042c28ec9b8760ddc94fd176b619ad32142',
                                                         'b5044e83d952c1256c16cd39773f9f1b1020fdffb72564659cba1a50e30452ca'),
    'evaluation/controllers/stopline_approach.py': ('6a0b1788133f68be7013bdd2254729842912605b770965a54b42357b106ea8a5',
                                                    '332cf6d3fcd0f89c38d1dd8c045b0e65e29752f70b666b9da11b3000163da77d'),
    'scripts/decision_hold.py': ('69e7a0a95fd5cabb73f060ff35facfa7f520ef20e3e38947c6a7d53f798452f7',
                                 '9ffc82ea7b846a2fe70f0fa9d28547743864e8794b77c512381f0f792ff773d6'),
    'scripts/tests/test_decision_hold.py': ('7d1a5fa2529a7f11b23862cbf9ca7d3e640dfd04589d8a115c5805caaefe124c',
                                            '3747f1a58bed1a855a0cd4dbe1c811e4ccdb9ccbea5a6ee37ad616d1749b1b8f'),
    'scripts/tests/test_k8_decision_hold_vbs.py': ('86d2701513f180211e60dc5653664142c334084ff519b015024daa0d1dfa2c7e',
                                                   'fa443c3ed1dc73ca8dd50e7f14db05efea184411d59688719b7ab8a1db3c35bd'),
    'scripts/tests/test_k8_s6_decision_capture_vbs.py': ('adfbce30c292644cf62753e7231f02aba3dba513d4b1bddb040a6391d3de310f',
                                                         '88ba8c716f0683843b1c2245d736046a9da758db94e4177e708f48d90a193bf0'),
}
D5_PREFIX = '/metadata/joint_leader_selection/tangent_derivatives[*]/transformed_source_sha256/'
HARD = ('H1', 'H2', 'H3', 'H4', 'H5')
RS_REL_A27 = 'evaluation/controllers/runtime_setup.py'
CAO_REL_A27 = 'evaluation/controllers/control_area_objective.py'
PATH_ALLOWED = ('R3-02', 'R3-04', 'R3-05', 'R3-06')     # path-string allowed items (amendment 21 R3)


# ------------------------------------------------------------------------------------------------ 1. tree roots
def norm_path(path):
    return str(path).replace('\\', '/').rstrip('/').lower()


def tree_root_ok(path):
    """True when `path` is a K9-2 tree root of section 2.1 (a root, not a file below it)."""
    return bool(_ROOT_FULL.match(norm_path(path)))


# ------------------------------------------------------------------------------------------------ 2. CR pair rule
def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def l_form(tree):
    """{file: 'C' | 'A' | 'X' | '-'} for the CR_FILES of one tree."""
    out = {}
    for rel, (committed, archive) in sorted(CR_FILES.items()):
        p = Path(tree) / rel
        if not p.is_file():
            out[rel] = '-'
            continue
        s = _sha(p)
        out[rel] = 'C' if s == committed else 'A' if s == archive else 'X'
    return out


def form_string(forms):
    return ''.join(forms[rel] for rel in sorted(CR_FILES))


def cr_pair(ref_root, new_root):
    """Section 2.2: ok when both roots are folders, the reference tree holds at least one file in form C or A, and
    every file whose reference form is C or A has the same form in the new tree."""
    ref, new = l_form(ref_root), l_form(new_root)
    bad = [rel for rel in sorted(CR_FILES) if ref[rel] in ('C', 'A') and new[rel] != ref[rel]]
    exist = Path(ref_root).is_dir() and Path(new_root).is_dir()
    known = any(v in ('C', 'A') for v in ref.values())
    return {'ok': exist and known and not bad, 'ref_form': form_string(ref), 'new_form': form_string(new), 'bad': bad,
            'roots_exist': exist, 'ref_has_known_form': known, 'files': sorted(CR_FILES)}


# ------------------------------------------------------------------------------------------------ 3. R-old
def load_comparator(path, name):
    """A k92_compare module loaded from an explicit file (the K9-2-0 blob copy, or this commit's file)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canonical(rep):
    return json.dumps(rep, sort_keys=True, default=str)


def full_unclassified(rep):
    """{(path, kind, why): count} of a compare() report; None when its 200-entry list was cut."""
    rows = rep.get('unclassified') or []
    if sum(int(u.get('count', 1)) for u in rows) != int(rep.get('unclassified_n') or 0):
        return None
    out = {}
    for u in rows:
        key = (u['path'], u['kind'], u['why'])
        out[key] = out.get(key, 0) + int(u.get('count', 1))
    return out


def rold_judge_k(old_rep, new_rep):
    """Group K: identical reports (canonical JSON) and a verdict present."""
    same = canonical(old_rep) == canonical(new_rep)
    return {'identical': same, 'old_verdict': old_rep.get('verdict'), 'new_verdict': new_rep.get('verdict'),
            'verdict': 'PASS' if same and new_rep.get('verdict') is not None else 'FAIL'}


def rold_judge_r(old_rep, new_rep, tails):
    """Group R.  tails = the two producing tree roots normalized by the OLD comparator's N (e.g. '<root>/a25/ref_t74_cwf',
    '<root>/k921_t74_w')."""
    checks = {}
    checks['complete'] = 'INCOMPLETE' not in (old_rep.get('verdict'), new_rep.get('verdict'))
    checks['hard_same'] = (old_rep.get('hard_verdict') == new_rep.get('hard_verdict')
                           and old_rep.get('h5_declared') == new_rep.get('h5_declared')
                           and all((old_rep.get(g) or {}).get('same') == (new_rep.get(g) or {}).get('same')
                                   for g in HARD)
                           and all((old_rep.get(g) or {}).get('diff_paths_generalized')
                                   == (new_rep.get(g) or {}).get('diff_paths_generalized') for g in HARD[1:]))
    ou, nu = full_unclassified(old_rep), full_unclassified(new_rep)
    checks['lists_not_cut'] = ou is not None and nu is not None
    res = {'checks': checks, 'tails': list(tails)}
    if not checks['lists_not_cut'] or not checks['complete']:
        res['verdict'] = 'INCOMPLETE'
        return res
    prefixes = sorted({D5_PREFIX + t.rstrip('/') + '/' for t in tails})
    removed = {k: v - nu.get(k, 0) for k, v in ou.items() if v > nu.get(k, 0)}
    added = {k: v - ou.get(k, 0) for k, v in nu.items() if v > ou.get(k, 0)}

    def side_of(path):
        hits = [x for x in prefixes if path.startswith(x)]
        return hits[0] if len(hits) == 1 else None
    sides_of_rel, removed_bad = {}, []
    for (path, kind, why) in removed:
        side = side_of(path)
        if why == 'D5' and kind == 'presence' and side is not None:
            sides_of_rel.setdefault(path[len(side):], set()).add(side)
        else:
            removed_bad.append([path, kind, why])
    added_bad, revealed = [], []
    root_prefix = D5_PREFIX + '<root>/'
    for (path, kind, why), n in sorted(added.items()):
        rel = path[len(root_prefix):] if path.startswith(root_prefix) else None
        sides = sides_of_rel.get(rel, set()) if rel is not None else set()
        if rel is None or not sides:
            added_bad.append([path, kind, why])
        elif kind == 'presence' and len(sides) != 1:
            added_bad.append([path, kind, why])
        elif kind != 'presence' and len(sides) != len(prefixes):
            added_bad.append([path, kind, why])
        else:
            revealed.append({'path': path, 'kind': kind, 'why': why, 'count': n})
    oa, na = old_rep.get('allowed_counts') or {}, new_rep.get('allowed_counts') or {}
    keys = (set(oa) | set(na)) - {'A_K92', 'R3-08'}
    other_diff = sorted(k for k in keys if k not in PATH_ALLOWED and oa.get(k) != na.get(k))
    path_up = sorted(k for k in PATH_ALLOWED if int(na.get(k, 0)) > int(oa.get(k, 0)))
    checks['removed_only_artefacts'] = not removed_bad
    checks['added_only_from_artefacts'] = not added_bad
    checks['allowed_counts_other_same'] = not other_diff
    checks['path_allowed_not_increased'] = not path_up
    res.update(removed_n=sum(removed.values()), added_n=sum(added.values()), removed_bad=removed_bad[:20],
               added_bad=added_bad[:20], allowed_other_diff=other_diff, path_allowed_up=path_up,
               path_allowed_delta={k: int(na.get(k, 0)) - int(oa.get(k, 0)) for k in PATH_ALLOWED
                                   if int(na.get(k, 0)) != int(oa.get(k, 0))}, revealed=revealed[:60],
               a_k92_delta=int((new_rep.get('allowed_counts') or {}).get('A_K92', 0))
               - int((old_rep.get('allowed_counts') or {}).get('A_K92', 0)),
               r308_delta=int((new_rep.get('allowed_counts') or {}).get('R3-08', 0))
               - int((old_rep.get('allowed_counts') or {}).get('R3-08', 0)),
               old_verdict=old_rep.get('verdict'), new_verdict=new_rep.get('verdict'),
               old_unclassified_n=old_rep.get('unclassified_n'), new_unclassified_n=new_rep.get('unclassified_n'))
    res['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    return res


# ------------------------------------------------------------------------------------------------ self-test
SELFTEST_N = [
    # (raw string, expected after this commit's N, expected after the K9-2-0 N)
    (r'D:\VISSIM-merge\k8_gate_trees\k92b1\k921_t74_W\evaluation\controllers\a.py',
     '<root>/evaluation/controllers/a.py', '<root>/k921_t74_w/evaluation/controllers/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25/ref_t74_CWf/evaluation/controllers/a.py',
     '<root>/evaluation/controllers/a.py', '<root>/a25/ref_t74_cwf/evaluation/controllers/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a26decl/tc/vendor/x.py', '<root>/vendor/x.py', '<root>/a26decl/tc/vendor/x.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a27/rj_k921_t74_W_cr/evaluation/controllers/a.py',
     '<root>/evaluation/controllers/a.py', '<root>/a27/rj_k921_t74_w_cr/evaluation/controllers/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/vb_b887f99f/diagnostics/x.json', '<root>/diagnostics/x.json',
     '<root>/vb_b887f99f/diagnostics/x.json'),
    ('D:/VISSIM-merge/k8_gate_trees/k92attrib/t74_CW/evaluation/controllers/a.py',
     '<root>/evaluation/controllers/a.py', '<root>/t74_cw/evaluation/controllers/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1', '<root>', '<root>'),
    # review r2: only a whole path component that is a tree name; a file or a group folder keeps the old form
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25', '<root>/a25', '<root>/a25'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25/k92b1_probe.build.json', '<root>/a25/k92b1_probe.build.json',
     '<root>/a25/k92b1_probe.build.json'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/k921.build.json', '<root>/k921.build.json', '<root>/k921.build.json'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a27/a.py', '<root>/a27/a.py', '<root>/a27/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/k921-x/a.py', '<root>/k921-x/a.py', '<root>/k921-x/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/k92attrib/t74_CW.build.json', '<root>/t74_cw.build.json',
     '<root>/t74_cw.build.json'),
    ('x D:/VISSIM-merge/k8_gate_trees/k92b1/a25/ref_t74_CWf;y', 'x <root>/a25/ref_t74_cwf;y',
     'x <root>/a25/ref_t74_cwf;y'),
    # unchanged by amendment 27
    ('D:/VISSIM-merge/k8_gate_trees/k91t/evaluation/controllers/a.py', '<root>/evaluation/controllers/a.py',
     '<root>/evaluation/controllers/a.py'),
    ('D:/VISSIM-merge/k8_gate_trees/s31fail/tree74_base/evaluation/a.py', '<root>/evaluation/a.py',
     '<root>/evaluation/a.py'),
    ('D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821/evaluation/a.py', '<root>/evaluation/a.py',
     '<root>/evaluation/a.py'),
    (r'D:\VISSIM-merge\sim3-n31-k8\evaluation\a.py', '<root>/evaluation/a.py', '<root>/evaluation/a.py'),
    ('D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43/decisions_sdmpc31_v3c3_k8j1_s43/x.json',
     '<run>/decisions_<name>/x.json', '<run>/decisions_<name>/x.json'),
    ('D:/VISSIM_runs/20261001_v3c3/reports/k8/offline_gates_k8h/gb7/A/T000150/replay/x.json', '<bundle>/replay/x.json',
     '<bundle>/replay/x.json'),
    ('ok', 'ok', 'ok'),
]
SELFTEST_ROOTS = [
    (r'D:\VISSIM-merge\k8_gate_trees\k92b1\k921_t74_W', True),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25/ref_t74_CWf', True),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a27/rj_k922_t74_B1', True),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/vb_b887f99f/', True),
    ('D:/VISSIM-merge/k8_gate_trees/k92attrib/t74_X1H1', True),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a27decl/tc', False),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25', False),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/a25/k92b1_probe.build.json', False),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/x/y/z', False),
    ('D:/VISSIM-merge/k8_gate_trees/k91t', False),
    ('D:/VISSIM-merge/k8_gate_trees/k92b1/k92-x', False),
    ('D:/VISSIM-merge/sim3-n31-k8', False),
]


def selftest():
    """No child process, no file outside a temporary folder: N table (this commit's N and the N without the amendment
    27 rule = the K9-2-0 N), tree roots, CR forms, R-old judges on synthetic reports."""
    global CR_FILES
    import tempfile
    sys.path.insert(0, str(HERE))
    import k92_compare as cmp
    cases = []
    old_n2 = [r for r in cmp.N2 if r[0] != K92_ROOT_RULE]

    def old_norm(s):
        s = s.lower().replace('\\\\', '/').replace('\\', '/')
        for a, b in old_n2:
            s = re.sub(a, b, s)
        for a, b in cmp.N3:
            s = re.sub(a, b, s)
        return s
    rule_at = [i for i, r in enumerate(cmp.N2) if r[0] == K92_ROOT_RULE]
    generic_at = [i for i, r in enumerate(cmp.N2) if r[0].startswith('d:/vissim-merge/k8_gate_trees/(?:s31fail')]
    cases.append({'case': 'rule_once_before_generic', 'ok': len(rule_at) == 1 and len(generic_at) == 1
                  and rule_at[0] < generic_at[0] and cmp.N2[rule_at[0]][1] == '<root>'})
    for raw, want_new, want_old in SELFTEST_N:
        got_new, got_old = cmp.norm_s(raw), old_norm(raw)
        cases.append({'case': 'N ' + raw[-60:], 'ok': got_new == want_new and got_old == want_old,
                      'new': got_new, 'old': got_old})
    for raw, want in SELFTEST_ROOTS:
        cases.append({'case': 'root ' + raw[-50:], 'ok': tree_root_ok(raw) is want})
    with tempfile.TemporaryDirectory(prefix='k92a27_') as td:
        keep = CR_FILES
        try:
            body = b'x = 1\ny = 2\n'
            c, a = hashlib.sha256(body).hexdigest(), hashlib.sha256(body.replace(b'\n', b'\r\n')).hexdigest()
            CR_FILES = {'p/a.py': (c, a), 'p/b.py': (c, a), 'p/c.py': (c, a)}
            trees = {}
            for name, files in (('ref_c', {'p/a.py': body, 'p/b.py': body}),
                                ('new_c', {'p/a.py': body, 'p/b.py': body, 'p/c.py': body.replace(b'\n', b'\r\n')}),
                                ('new_a', {'p/a.py': body.replace(b'\n', b'\r\n'), 'p/b.py': body}),
                                ('new_x', {'p/a.py': b'other\n', 'p/b.py': body})):
                t = Path(td) / name
                for rel, data in files.items():
                    (t / rel).parent.mkdir(parents=True, exist_ok=True)
                    (t / rel).write_bytes(data)
                trees[name] = t
            cases.append({'case': 'l_form', 'ok': form_string(l_form(trees['new_c'])) == 'CCA'
                          and form_string(l_form(trees['ref_c'])) == 'CC-'})
            cases.append({'case': 'cr_pair_ok', 'ok': cr_pair(trees['ref_c'], trees['new_c'])['ok'] is True})
            cases.append({'case': 'cr_pair_archive_vs_committed', 'ok': cr_pair(trees['ref_c'], trees['new_a'])['bad']
                          == ['p/a.py']})
            cases.append({'case': 'cr_pair_other_bytes', 'ok': cr_pair(trees['ref_c'], trees['new_x'])['ok'] is False})
        finally:
            CR_FILES = keep
    tails = ['<root>/a25/ref_t74_cwf', '<root>/k921_t74_w']
    p_old = D5_PREFIX + '<root>/a25/ref_t74_cwf/evaluation/controllers/'
    p_new = D5_PREFIX + '<root>/k921_t74_w/evaluation/controllers/'
    base = {'verdict': 'HOLD', 'hard_verdict': 'SAME', 'h5_declared': [],
            **{g: {'same': True, 'diff_paths_generalized': []} for g in HARD}}
    old = dict(base, unclassified_n=4, allowed_counts={'V': 6},
               unclassified=[{'path': p_old + 'x.py', 'kind': 'presence', 'why': 'D5', 'count': 1},
                             {'path': p_new + 'x.py', 'kind': 'presence', 'why': 'D5', 'count': 1},
                             {'path': p_old + 'runtime_setup.py', 'kind': 'presence', 'why': 'D5', 'count': 1},
                             {'path': p_new + 'runtime_setup.py', 'kind': 'presence', 'why': 'D5', 'count': 1}])
    new_ok = dict(base, unclassified_n=1, allowed_counts={'V': 6, 'A_K92': 1},
                  unclassified=[{'path': D5_PREFIX + '<root>/evaluation/controllers/x.py', 'kind': 'value', 'why': 'D5',
                                 'count': 1}])
    new_pass = dict(base, verdict='PASS', unclassified_n=0, unclassified=[], allowed_counts={'V': 6, 'A_K92': 1})
    new_bad = dict(new_ok, unclassified_n=2, unclassified=new_ok['unclassified'] + [
        {'path': '/metadata/other', 'kind': 'value', 'why': 'not allowed', 'count': 1}])
    new_hard = dict(new_ok, hard_verdict='DIFFERENT', H2={'same': False, 'diff_paths_generalized': ['/green_times']})
    new_lost = dict(base, unclassified_n=0, unclassified=[], allowed_counts={'V': 5, 'A_K92': 1})
    cases.append({'case': 'rold_r_revealed', 'ok': rold_judge_r(old, new_ok, tails)['verdict'] == 'PASS'
                  and len(rold_judge_r(old, new_ok, tails)['revealed']) == 1})
    cases.append({'case': 'rold_r_pass', 'ok': rold_judge_r(old, new_pass, tails)['verdict'] == 'PASS'})
    cases.append({'case': 'rold_r_new_leaf', 'ok': rold_judge_r(old, new_bad, tails)['verdict'] == 'FAIL'})
    cases.append({'case': 'rold_r_hard', 'ok': rold_judge_r(old, new_hard, tails)['verdict'] == 'FAIL'})
    cases.append({'case': 'rold_r_allowed_other', 'ok': rold_judge_r(old, new_lost, tails)['verdict'] == 'FAIL'})
    hidden = dict(old, unclassified_n=5, unclassified=old['unclassified'] + [
        {'path': '/metadata/other', 'kind': 'value', 'why': 'not allowed', 'count': 1}])
    cases.append({'case': 'rold_r_hidden_leaf', 'ok': rold_judge_r(hidden, new_pass, tails)['verdict'] == 'FAIL'
                  and rold_judge_r(hidden, new_pass, tails)['removed_bad'] == [['/metadata/other', 'value',
                                                                                 'not allowed']]})
    one_side = dict(old, unclassified_n=3, unclassified=[u for u in old['unclassified'] if u['path'] != p_new + 'x.py'])
    cases.append({'case': 'rold_r_value_needs_both_sides',
                  'ok': rold_judge_r(one_side, new_ok, tails)['verdict'] == 'FAIL'})
    old_p = dict(old, allowed_counts={'V': 6, 'R3-02': 60, 'R3-04': 4, 'R3-05': 30, 'R3-06': 2})
    new_p = dict(new_ok, allowed_counts={'V': 6, 'A_K92': 1})
    cases.append({'case': 'rold_r_path_allowed_fall', 'ok': rold_judge_r(old_p, new_p, tails)['verdict'] == 'PASS'
                  and rold_judge_r(old_p, new_p, tails)['path_allowed_delta'] == {'R3-02': -60, 'R3-04': -4,
                                                                                   'R3-05': -30, 'R3-06': -2}})
    new_up = dict(new_ok, allowed_counts={'V': 6, 'A_K92': 1, 'R3-05': 31, 'R3-02': 60, 'R3-04': 4, 'R3-06': 2})
    cases.append({'case': 'rold_r_path_allowed_rise', 'ok': rold_judge_r(old_p, new_up, tails)['verdict'] == 'FAIL'})
    new_f1 = dict(new_p, allowed_counts={'V': 6, 'A_K92': 1, 'F1': 1})
    cases.append({'case': 'rold_r_other_allowed_new', 'ok': rold_judge_r(old_p, new_f1, tails)['verdict'] == 'FAIL'})
    cut = dict(old, unclassified_n=999)
    cases.append({'case': 'rold_r_cut', 'ok': rold_judge_r(cut, new_ok, tails)['verdict'] == 'INCOMPLETE'})
    cases.append({'case': 'rold_k', 'ok': rold_judge_k(old, dict(old))['verdict'] == 'PASS'
                  and rold_judge_k(old, new_ok)['verdict'] == 'FAIL'})
    ok = all(x['ok'] for x in cases)
    return {'schema': 'k92-a27-selftest/v1', 'cases': cases, 'n': len(cases), 'child_processes': 0,
            'verdict': 'PASS' if ok else 'FAIL'}


if __name__ == '__main__':
    r = selftest()
    print('K92_A27_SELFTEST %s n=%d bad=%s' % (r['verdict'], r['n'], [c['case'] for c in r['cases'] if not c['ok']]))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(r, indent=1, default=str), encoding='utf-8')
    sys.exit(0 if r['verdict'] == 'PASS' else 1)
