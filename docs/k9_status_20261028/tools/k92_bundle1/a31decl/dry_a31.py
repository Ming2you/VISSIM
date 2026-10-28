"""Amendment 31 Declare: data-free checks of the new tools (synthetic inputs only; no sealed record, no jb_unit log, no
b9734abe run, no worktree).

    python -B dry_a31.py static     compile, CR, base copy, judge diff = only _seed47_path, imports, A31_JUDGE.diff
    python -B dry_a31.py truth      the declared truth table T1-T22 on the base and the new _seed47_path, synthetic
                                    sealed roots A / B through scan_vissim_blind(sealed=True), mutants M1-M8,
                                    the judge's own main() 'sealedscan --dest' on A / B (SEALED patched)
    python -B dry_a31.py unit       synthetic pytest projects run twice (two roots), k92t31_unit.judge cases U1-U14,
                                    mutants UM1-UM8 of k92t31_unit.py, the k92t31_unit.py command line on U1
    python -B dry_a31.py drive      k92t31.py check31 --mode decl (read-only) as a child
Outputs: KB/a31decl/dry/decl/*.json (LF, sorted keys); synthetic trees dry/decl/synth_scan and TK/a31decl/su."""
import ast
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
SP = KB.parent.parent
OUTD = HERE / 'dry' / 'decl'
SYNTH_UNIT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a31decl/su')
PY =r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
RUN_PYTEST_BN = SP / 'k8b_impl' / 'run_pytest_bn.py'
BASE_JUDGE = HERE / 'base' / 'k92t30_judge.py'
NEW_JUDGE = HERE / 'k92t31_judge.py'
UNIT = HERE / 'k92t31_unit.py'
DRIVER = HERE / 'k92t31.py'
JUDGE30 = KB / 'a30decl' / 'k92t30_judge.py'
JUDGE30_SHA = 'a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf'
SEALED_REAL = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/sealed_s47'
K = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1'
KW = r'\\?\D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_b1'
# amendment 31 section 2.2: the closed truth table (path, base _seed47_path, new _seed47_path)
TRUTH = [
    ('T1', K + '/sealed_s47', True, False),
    ('T2', K + '/sealed_s47/K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3/k92_record.json', True, False),
    ('T3', K + '/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_1050_s43_SAF_OBS_H3/k92_record.json', True, False),
    ('T4', K + '/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_900_s47_SAF_OBS_H3/k92_record.json', True, True),
    ('T5', K + '/sealed_s47/K9-2-2/probe/sa/cap/k922/TL3/000900_s47/SAF/capture.json', True, True),
    ('T6', K + '/sealed_s47/K9-2-0/s47/x/k92_record.json', True, True),
    ('T7', K + '/sealed_s47/K9-2-0/s47_extra/k92_record.json', True, True),
    ('T8', K + '/sealed_s47/K9-2-0/v3c3-s47/k92_record.json', True, False),
    ('T9', K + '/sealed_s47/K9-2-0/s470/k92_record.json', True, False),
    ('T10', K + '/sealed_s47/K9-2-3/sealed_s47/k92_record.json', True, True),
    ('T11', K + '/sealed_s47/k92t/logs/f_f_off_jobs.log', True, False),
    ('T12', KW + r'\sealed_s47\K9-2-0\probe\sa\jobs\k92p0\TL3_1500_SAF_OBS_H3\k92_record.json', True, False),
    ('T13', KW + r'\sealed_s47\K9-2-1\probe\sa\jobs\k921\TL3_900_s47_SAF_OBS_H3\k92_record.json', True, True),
    ('T14', 'd:/vissim_runs/20261001_V3C3/REPORTS/k8/K92_B1/SEALED_S47/K9-2-0/x/TL3_1500_SAF_OBS_H3/k92_record.json',
     True, False),
    ('T15', K + '/sealed_s47_old/K9-2-0/x.json', True, True),
    ('T16', K + '/sealed_s47x/K9-2-0/x.json', False, False),
    ('T17', K + '/probe/sa/jobs/k92p/TL3_900_s47_SAF_OBS_H3/k92_record.json', True, True),
    ('T18', K + '/probe/sa/jobs/k92p/TL3_1500_SAF_OBS_H3/k92_record.json', False, False),
    ('T19', K + '/commit/K9-2-0/sealed_s47_index.json', True, True),
    ('T20', 'probe/sa/jobs/TL3_1500_SAF_OBS_H3/k92_record.json', False, False),
    ('T21', 'x/TL3_900_s47_SAF_OBS_H3/k92_record.json', True, True),
    ('T22', r'D:\VISSIM_runs/20261001_v3c3\reports/k8/k92_b1\sealed_s47/K9-2-0/x/TL3_1500_SAF_OBS_H3/k92_record.json',
     True, False),
]
BLIND = {'vissim': None, 'vissim_reason': 'k92_blind_s47'}
# amendment 31 section 2.5: synthetic sealed roots (relative path -> record) and the expected counts
SCAN_A = {
    'K9-2-0/probe/sa/jobs/k92p0/TL3_900_s47_SAF_OBS_H3/k92_record.json': dict(BLIND, seed=47),
    'K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3/k92_record.json':
        {'seed': 31, 'vissim': {'m1_T450': 1}, 'vissim_reason': 'k92_vissim_ref'},
    'K9-2-1/probe/sa/jobs/k921/TL3_1050_s43_SAF_OBS_H3/k92_record.json':
        {'seed': 43, 'vissim': None, 'vissim_reason': 'k92_vissim_ref'},
    'K9-2-1/probe/sa/jobs/k921/TL3_2400_s47_SAF_OBS_H3/k92_record.json': dict(BLIND, seed=47),
    'K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1050_s43_SAF_OBS_H3/k92_record.json':
        {'seed': 43, 'vissim': {'x': 2}, 'vissim_reason': 'k92_vissim_ref'},
    'K9-2-2/probe/sa/jobs/k922/TL3_3300_s47_SAF_OBS_H3/k92_record.json': dict(BLIND, seed=47),
    'K9-2-0/probe/sa/jobs/k92p0/TL3_900_s47_SAF_OBS_H3/summary.json': {'ok': True},
    'k92t/logs/f_f_off_jobs.log': None,
}
SCAN_B = {
    'K9-2-0/x/TL3_2700_SAF_OBS_H3/k92_record.json': {'seed': 47, 'vissim': {'m': 1}, 'vissim_reason': 'k92_vissim_ref'},
    'K9-2-0/cap/TL3/000900_s47/SAF/k92_record.json': {'vissim': 3.0, 'vissim_reason': None},
    'K9-2-0/cap/TL3/000900_s47/SAF2/k92_record.json': dict(BLIND),
    'K9-2-3/sealed_s47/inner/k92_record.json': {'seed': 31, 'vissim': None, 'vissim_reason': 'k92_vissim_ref'},
    'K9-2-1/y/TL3_1500_SAF_OBS_H3/k92_record.json': dict(BLIND, seed='47'),
    'K9-2-1/y/TL3_1800_SAF_OBS_H3/k92_record.json': {'seed': 31, 'vissim': {'m': 5}, 'vissim_reason': 'k92_vissim_ref'},
}
SCAN_EXPECT = {'A': {'new': {'files': 6, 's47': 3, 'bad': 0, 'ok': True}, 'base': {'files': 6, 's47': 6, 'bad': 3, 'ok': False}},
               'B': {'new': {'files': 6, 's47': 5, 'bad': 3, 'ok': False}, 'base': {'files': 6, 's47': 6, 'bad': 4, 'ok': False}}}


def wjson(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, default=str, ensure_ascii=False) + '\n')


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ================================================================================================ static
def top_defs(src):
    tree = ast.parse(src)
    out, spans = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            seg = ast.get_source_segment(src, node)
            out[node.name] = seg
            start = node.lineno - 1 - len(node.decorator_list)
            spans.append((start, node.end_lineno))
    lines = src.splitlines()
    rest = [ln for i, ln in enumerate(lines) if not any(a <= i < b for a, b in spans)]
    return out, '\n'.join(rest)


def imports(src):
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or '').split('.')[0])
    return sorted(names)


def cmd_static():
    res = {'schema': 'a31-dry-static/v1', 'when': time.strftime('%Y-%m-%d %H:%M:%S')}
    files = {'driver': DRIVER, 'judge': NEW_JUDGE, 'unit': UNIT, 'dry': Path(__file__).resolve()}
    res['compile'] = {}
    for k, p in files.items():
        try:
            compile(p.read_text(encoding='utf-8'), str(p), 'exec')
            res['compile'][k] = True
        except SyntaxError as exc:
            res['compile'][k] = 'SyntaxError %s' % exc
    res['cr'] = {k: p.read_bytes().count(b'\r') for k, p in files.items()}
    res['base_copy'] = {'base_sha256': sha(BASE_JUDGE), 'a30_sha256': sha(JUDGE30),
                        'equal_pinned': sha(BASE_JUDGE) == sha(JUDGE30) == JUDGE30_SHA}
    bsrc, nsrc = BASE_JUDGE.read_text(encoding='utf-8'), NEW_JUDGE.read_text(encoding='utf-8')
    bdefs, brest = top_defs(bsrc)
    ndefs, nrest = top_defs(nsrc)
    res['judge_defs'] = {'n_base': len(bdefs), 'n_new': len(ndefs), 'same_names': sorted(bdefs) == sorted(ndefs),
                         'changed': sorted(k for k in bdefs if bdefs.get(k) != ndefs.get(k)),
                         'module_text_outside_defs_equal': brest == nrest}
    diff = ''.join(difflib.unified_diff(bsrc.splitlines(keepends=True), nsrc.splitlines(keepends=True),
                                        'a30decl/k92t30_judge.py', 'a31decl/k92t31_judge.py', n=3))
    with open(HERE / 'A31_JUDGE.diff', 'w', encoding='utf-8', newline='\n') as f:
        f.write(diff)
    res['diff'] = {'path': str(HERE / 'A31_JUDGE.diff'), 'sha256': sha(HERE / 'A31_JUDGE.diff'),
                   'lines': len(diff.splitlines()),
                   'hunks': len(re.findall(r'^@@', diff, flags=re.M))}
    res['imports'] = {'unit': imports(UNIT.read_text(encoding='utf-8')),
                      'driver': imports(DRIVER.read_text(encoding='utf-8')),
                      'judge_new_minus_base': sorted(set(imports(nsrc)) - set(imports(bsrc)))}
    res['imports_ok'] = {
        'unit_stdlib_only': set(res['imports']['unit']) <= {'argparse', 'json', 're', 'sys', 'pathlib'},
        'driver_k92lib_and_stdlib': set(res['imports']['driver']) <= {'json', 'os', 're', 'subprocess', 'sys', 'time',
                                                                      'pathlib', 'k92lib'},
        'judge_no_new_import': res['imports']['judge_new_minus_base'] == []}
    res['ok'] = (all(v is True for v in res['compile'].values()) and not any(res['cr'].values())
                 and res['base_copy']['equal_pinned'] and res['judge_defs']['same_names']
                 and res['judge_defs']['changed'] == ['_seed47_path']
                 and res['judge_defs']['module_text_outside_defs_equal'] and res['diff']['hunks'] == 1
                 and all(res['imports_ok'].values()))
    wjson(OUTD / 'dry_a31_static.json', res)
    print('A31_DRY_STATIC ok=%s changed=%s hunks=%s' % (res['ok'], res['judge_defs']['changed'], res['diff']['hunks']))
    return 0 if res['ok'] else 1


# ================================================================================================ truth + scans
def mutant_fns(mod):
    """M1-M8: wrong readings of D-K9-58 that the truth table / scans must catch (each reads mod.SEALED at call)."""
    import os as _os

    def rule(parts):
        return any(p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_') for p in parts)

    def split(s):
        return [p.lower() for p in re.split(r'[\\/]', s)]

    def rel_of(path, strip=True, case=True, sep=True):
        s = str(path)
        if strip and s.startswith('\\\\?\\'):
            s = s[4:]
        full = _os.path.abspath(s)
        root = _os.path.abspath(str(mod.SEALED)).rstrip('\\/')
        if case:
            full, root = _os.path.normcase(full), _os.path.normcase(root)
        if full == root:
            return ''
        if full.startswith(root + (_os.sep if sep else '')):
            return full[len(root) + 1:]
        return None

    def m1(path):                               # amendment-30 function: every piece, the root name included
        return rule(split(str(path)))

    def m2(path):                               # no long-path prefix strip
        r = rel_of(path, strip=False)
        return rule(split(str(path) if r is None else r))

    def m3(path):                               # case-sensitive prefix test
        r = rel_of(path, case=False)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        return rule(split(s if r is None else r))

    def m4(path):                               # prefix test without the separator
        r = rel_of(path, sep=False)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        return rule(split(s if r is None else r))

    def m5(path):                               # piece rule without p == 's47'
        r = rel_of(path)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        parts = split(s if r is None else r)
        return any(p.endswith('_s47') or '_s47_' in p or p.startswith('s47_') for p in parts)

    def m6(path):                               # every piece named sealed_s47 dropped (not only the root)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        return rule([p for p in split(s) if p != 'sealed_s47'])

    def m7(path):                               # only the parent folder name
        r = rel_of(path)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        parts = split(s if r is None else r)
        return rule(parts[-2:-1])

    def m8(path):                               # nothing under the sealed root counts by path
        r = rel_of(path)
        s = str(path)[4:] if str(path).startswith('\\\\?\\') else str(path)
        return False if r is not None else rule(split(s))
    return {'M1': m1, 'M2': m2, 'M3': m3, 'M4': m4, 'M5': m5, 'M6': m6, 'M7': m7, 'M8': m8}


def build_scan_root(name, table):
    root = OUTD / 'synth_scan' / name / 'sealed_s47'
    if root.parent.exists():
        shutil.rmtree(root.parent)
    for rel, rec in table.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rec is None:
            p.write_text('synthetic log line\n', encoding='utf-8')
        else:
            p.write_text(json.dumps(rec), encoding='utf-8')
    return root


def scan_counts(mod, root):
    saved = mod.SEALED
    try:
        mod.SEALED = Path(root)
        r = mod.scan_vissim_blind(sealed=True)
    finally:
        mod.SEALED = saved
    sr = r['sealed_records']
    return {'files': sr['files'], 's47': sr['s47'], 'bad': sr['bad'], 'ok': r['ok']}


def cmd_truth():
    res = {'schema': 'a31-dry-truth/v1', 'when': time.strftime('%Y-%m-%d %H:%M:%S')}
    base = load(BASE_JUDGE, 'k92t30_judge_base')
    new = load(NEW_JUDGE, 'k92t31_judge_new')
    res['sealed_constant'] = {'base': str(base.SEALED), 'new': str(new.SEALED),
                              'is_real': str(new.SEALED).replace('\\', '/') == SEALED_REAL}
    rows = []
    for tid, path, want_b, want_n in TRUTH:
        rows.append({'id': tid, 'path': path, 'base': base._seed47_path(path), 'new': new._seed47_path(path),
                     'want_base': want_b, 'want_new': want_n})
    res['truth'] = rows
    res['truth_ok'] = all(r['base'] == r['want_base'] and r['new'] == r['want_new'] for r in rows)
    roots = {n: build_scan_root(n, t) for n, t in (('A', SCAN_A), ('B', SCAN_B))}
    res['scans'] = {}
    for n, root in roots.items():
        res['scans'][n] = {'base': scan_counts(base, root), 'new': scan_counts(new, root), 'want': SCAN_EXPECT[n]}
    res['scans_ok'] = all(v['base'] == v['want']['base'] and v['new'] == v['want']['new']
                          for v in res['scans'].values())
    # mutants: each must make at least one truth row or one scan count differ from the declared new values
    res['mutants'] = {}
    real = new._seed47_path
    for mname, fn in mutant_fns(new).items():
        bad_rows = [tid for tid, path, _b, want_n in TRUTH if fn(path) != want_n]
        new._seed47_path = fn
        try:
            bad_scans = [n for n, root in roots.items() if scan_counts(new, root) != SCAN_EXPECT[n]['new']]
        finally:
            new._seed47_path = real
        res['mutants'][mname] = {'truth_rows_caught': bad_rows, 'scans_caught': bad_scans,
                                 'caught': bool(bad_rows or bad_scans)}
    res['mutants_ok'] = all(v['caught'] for v in res['mutants'].values())
    # the command line the driver uses (sealedscan --dest D) through the new judge's own main(), SEALED patched to
    # the synthetic roots: return code 0 for root A (ok), 3 for root B (not ok), the file counts as the scans above
    res['cli'] = {}
    saved_argv, saved_root = sys.argv, new.SEALED
    for n, root in roots.items():
        dest = OUTD / ('cli_sealedscan_%s.json' % n)
        try:
            sys.argv = ['k92t31_judge.py', 'sealedscan', '--dest', str(dest)]
            new.SEALED = Path(root)
            rc = new.main()
        finally:
            sys.argv, new.SEALED = saved_argv, saved_root
        out = json.loads(dest.read_text(encoding='utf-8'))
        got = dict(out['sealed_records'])
        got.pop('ran', None)
        got['ok'] = out['ok']
        res['cli'][n] = {'rc': rc, 'counts': got, 'want_rc': 0 if SCAN_EXPECT[n]['new']['ok'] else 3}
    res['cli_ok'] = all(v['rc'] == v['want_rc'] and v['counts'] == SCAN_EXPECT[n]['new'] for n, v in res['cli'].items())
    res['ok'] = (res['truth_ok'] and res['scans_ok'] and res['mutants_ok'] and res['sealed_constant']['is_real']
                 and res['cli_ok'])
    wjson(OUTD / 'dry_a31_truth.json', res)
    print('A31_DRY_TRUTH ok=%s truth=%s scans=%s cli=%s mutants=%s' % (
        res['ok'], res['truth_ok'], res['scans_ok'], res['cli_ok'], {k: v['caught'] for k, v in res['mutants'].items()}))
    return 0 if res['ok'] else 1


# ================================================================================================ unit
UNIT_FILES = ['test_stopline_approach.py', 'test_stopline_wiring.py', 'test_stopline_evidence.py',
              'test_stopline_approach_captured.py']
N31 = 'diagnostics/sdmpc_n31_20260924/tests/'
HEAD_TXT = ('"""Synthetic test file (amendment 31 Declare dry check); no project code."""\n'
            'import unittest\nfrom pathlib import Path\n\nimport pytest\n\nHERE = Path(__file__).resolve().parent\n'
            '_T = {"c": None}\n\n\nclass Base(unittest.TestCase):\n    @pytest.fixture(autouse=True)\n'
            '    def _term(self, capsys):\n        _T["c"] = capsys\n        yield\n        _T["c"] = None\n\n'
            '    def emit(self, line):\n        with _T["c"].disabled():\n            print("\\n" + line, flush=True)\n')


def project(variant):
    """{file name: source} of one synthetic side; variant = set of switches.  Templates use @NAME@ placeholders."""
    v = set(variant)
    approach = HEAD_TXT + (
        '\n\nclass ApproachTests(Base):\n'
        '    def test_pass(self):\n        self.assertEqual(1, @ONE@)\n'
        '    def test_emit(self):\n        self.emit("K8_SA_CAPTURE_PROVENANCE " + HERE.as_posix())\n'
        '    def test_skip(self):\n        raise unittest.SkipTest("no capture under " + str(HERE))\n'
        '    def test_sub(self):\n        for i in range(3):\n            with self.subTest(i=i):\n'
        '                self.assertLess(i, 3)\n').replace('@ONE@', '2' if 'pass_to_fail' in v else '1')
    if 'new_pass' in v:
        approach += '    def test_new_k92(self):\n        self.assertTrue(True)\n'
    if 'new_fail' in v:
        approach += '    def test_new_k92(self):\n        self.assertTrue(False, "new")\n'
    if 'base_only' in v:
        approach += '    def test_gone(self):\n        self.assertTrue(True)\n'
    wiring = HEAD_TXT + (
        '\n\nclass ConfigFlagTests(Base):\n'
        '    def test_default_output_is_byte_identical(self):\n        self.assertEqual(b"a1", @OTHER@)\n'
        '    def test_arms_add_exactly_the_key(self):\n        for arm in ("A", "B", "C"):\n'
        '            with self.subTest(arm):\n'
        '                self.assertNotEqual(arm, @BAD@, "arm " + arm + " under " + str(HERE))\n'
        '    def test_flag_contract(self):\n        self.assertIn("x", "xyz")\n').replace(
        '@OTHER@', 'b"c3"' if 'msg' in v else 'b"b2"').replace('@BAD@', '"C"' if 'sublabel' in v else '"B"')
    if 'random_tmp' in v:
        wiring += ('    def test_tmp(self):\n        import tempfile\n'
                   '        self.fail("tmp " + tempfile.mkdtemp(prefix="_sa_tmp_", dir=HERE))\n')
    evidence = HEAD_TXT + (
        '\n\n@pytest.fixture\ndef td():\n    yield 1\n    raise RuntimeError("teardown broke")\n\n\n'
        'def test_teardown(td):\n    assert td == 1\n\n\n'
        '@pytest.mark.xfail(reason="known")\ndef test_known():\n    assert False\n\n\n'
        'def test_plain():\n    assert True\n')
    captured = HEAD_TXT + (
        '\n\nclass CapturedTests(Base):\n'
        '    def test_rows(self):\n        self.emit("K8_SA_CAPTURE_PROVENANCE tree " + HERE.name)\n'
        '        self.assertTrue(True)\n'
        '    def test_rows_two(self):\n        self.emit("K8_SA_CAPTURE_PROVENANCE T 2700")\n'
        '        self.assertEqual(2, 2)\n')
    return {'test_stopline_approach.py': approach, 'test_stopline_wiring.py': wiring,
            'test_stopline_evidence.py': evidence, 'test_stopline_approach_captured.py': captured}


def run_side(root, variant):
    """Write one synthetic side under root and run the jb_unit command form on it; returns (log text, rc)."""
    if root.exists():
        shutil.rmtree(root)
    tests = root / N31
    tests.mkdir(parents=True)
    for name, src in project(variant).items():
        (tests / name).write_text(src, encoding='utf-8', newline='\n')
    out = root.parent / (root.name + '_out')
    if out.exists():
        shutil.rmtree(out)
    (out / 'tmp').mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(root), K8G_OUT=str(out),
               TMP=str(out / 'tmp'), TEMP=str(out / 'tmp'), NUMBA_NUM_THREADS='1')
    logp = root.parent / (root.name + '.log')
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([PY, '-B', str(RUN_PYTEST_BN), '-v'] + [N31 + n for n in UNIT_FILES], cwd=str(root),
                            env=env, stdout=f, stderr=subprocess.STDOUT, creationflags=0x4000).returncode
    return logp.read_text(encoding='utf-8', errors='replace'), rc, out


SCEN = {  # name: (base variant, new variant, expected verdict)
    'U1_same': ((), (), 'PASS'),
    'U2_pass_to_fail': ((), ('pass_to_fail',), 'FAIL'),
    'U3_new_pass': ((), ('new_pass',), 'PASS'),
    'U4_new_fail': ((), ('new_fail',), 'FAIL'),
    'U5_base_only': (('base_only',), (), 'FAIL'),
    'U6_msg': ((), ('msg',), 'FAIL'),
    'U10_sublabel': ((), ('sublabel',), 'FAIL'),
    'U14_random_tmp': (('random_tmp',), ('random_tmp',), 'FAIL'),
}


def edit_cases(u1):
    """U7-U9, U11-U13 from the U1 logs (text edits / argument changes)."""
    bt, nt, brc, nrc, broot, nroot, roots = u1
    lines = nt.splitlines()
    cut = '\n'.join(lines[:max(i for i, ln in enumerate(lines) if ln.startswith('=') and ' in ' in ln)])
    final = [ln for ln in bt.splitlines() if re.match(r'^=+ .* in [0-9.]+s', ln)][-1]
    m = re.search(r'(\d+) passed', final)
    bumped = bt.replace(final, final.replace(m.group(0), '%d passed' % (int(m.group(1)) + 1)))
    blocks = re.findall(r'^_+ (.+?) _+$', nt, flags=re.M)
    real = [b for b in blocks if b.replace('_', '').strip()]
    swapped = nt
    if len(real) >= 2:
        a, b = real[0], real[1]
        swapped = nt.replace(' %s ' % a, ' @@A@@ ', 1).replace(' %s ' % b, ' %s ' % a, 1).replace(' @@A@@ ', ' %s ' % b, 1)
    return {
        'U7_truncated': ((bt, cut, brc, nrc, broot, nroot, roots), 'INCOMPLETE'),
        'U8_rc': ((bt, nt, brc, 0, broot, nroot, roots), 'INCOMPLETE'),
        'U9_rootdir': ((bt, nt, brc, nrc, str(broot) + '_other', nroot, roots), 'INCOMPLETE'),
        'U11_parse': ((bt, nt, brc, nrc, broot, nroot, roots), 'PASS'),
        'U12_counts': ((bumped, nt, brc, nrc, broot, nroot, roots), 'INCOMPLETE'),
        'U13_block_order': ((bt, swapped, brc, nrc, broot, nroot, roots), 'INCOMPLETE'),
    }


UNIT_MUTANTS = {  # name: (old text, new text) applied once to k92t31_unit.py
    'UM1_rows_only': ("differ = [[t, rb[t], rn[t]] for t in common if rb[t] != rn[t]]",
                      "differ = [[t, rb[t], rn[t]] for t in common if rb[t]['rows'] != rn[t]['rows']]"),
    'UM2_only_base_ignored': ("if not differ and not only_base and not new_bad", "if not differ and not new_bad"),
    'UM3_new_not_checked': ("if rn[t]['rows'] != ['PASSED'] or rn[t]['fails']]", "if False]"),
    'UM4_no_root_norm': ("for r in sorted((re.sub(r'\\\\+', '/', str(x)).rstrip('/') for x in roots if x), key=len, "
                         "reverse=True):", "for r in []:"),
    'UM5_parse_ignored': ("        if not p['ok']:\n            inc.append", "        if False:\n            inc.append"),
    'UM6_rc_ignored': ("if rc not in (0, 1) or bad is None or (rc == 1) != (bad > 0):", "if bad is None:"),
    'UM7_rootdir_ignored': ("        if not _same_root(p['rootdir'], root):", "        if False:"),
    'UM8_lone_word_ignored': ("            m2 = RE_LONE_OUT.match(ln)", "            m2 = None"),
}


def cmd_unit():
    res = {'schema': 'a31-dry-unit/v1', 'when': time.strftime('%Y-%m-%d %H:%M:%S'), 'cases': {}}
    unit = load(UNIT, 'k92t31_unit_dry')
    files = [N31 + n for n in UNIT_FILES]
    base_dir = SYNTH_UNIT                     # short root (Windows path length); scratch trees live under TK
    logs = {}
    for name, (bv, nv, want) in SCEN.items():
        broot = base_dir / name / 'b9side_longer'
        nroot = base_dir / name / 'k92'
        bt, brc, bout = run_side(broot, bv)
        nt, nrc, nout = run_side(nroot, nv)
        roots = [str(broot), str(nroot), str(bout), str(nout)]
        logs[name] = (bt, nt, brc, nrc, broot, nroot, roots)
        r = unit.judge(bt, nt, files, roots, str(broot), str(nroot), brc, nrc)
        res['cases'][name] = {'want': want, 'got': r['verdict'], 'n_common': r['n_common'], 'n_differ': r['n_differ'],
                              'only_base': r['only_base'], 'only_new': r['only_new'], 'new_bad': r['new_bad'],
                              'incomplete': r['incomplete'], 'rc': [brc, nrc], 'counts': r['counts'],
                              'n_non_passed_common': r['n_non_passed_common']}
    for name, (args, want) in edit_cases(logs['U1_same']).items():
        bt, nt, brc, nrc, broot, nroot, roots = args
        r = unit.judge(bt, nt, files, roots, str(broot), str(nroot), brc, nrc)
        res['cases'][name] = {'want': want, 'got': r['verdict'], 'incomplete': r['incomplete'][:3],
                              'n_differ': r['n_differ']}
    u1 = logs['U1_same']
    pb, pn = unit.parse_log(u1[0], files), unit.parse_log(u1[1], files)
    res['u1_parse'] = {side: {'ok': p['ok'], 'problems': p['problems'], 'collected': p['collected'],
                              'words': p['words'], 'counts': p['counts'], 'n_entries': len(p['entries']),
                              'entries': [e[:3] for e in p['entries']],
                              'n_blocks': {k: len(v) for k, v in p['blocks'].items()}}
                       for side, p in (('base', pb), ('new', pn))}
    # the command line the driver uses (k92t31_unit.py judge ..., roots / files as JSON words) on the U1 logs
    bt, nt, brc, nrc, broot, nroot, roots = logs['U1_same']
    cli_dir = OUTD / 'cli_unit'
    cli_dir.mkdir(parents=True, exist_ok=True)
    (cli_dir / 'base.log').write_text(bt, encoding='utf-8')
    (cli_dir / 'new.log').write_text(nt, encoding='utf-8')
    dest = cli_dir / 'unit_judge.json'
    done = subprocess.run([PY, '-B', str(UNIT), 'judge', '--base', str(cli_dir / 'base.log'), '--new',
                           str(cli_dir / 'new.log'), '--base-root', str(broot), '--new-root', str(nroot),
                           '--base-rc', str(brc), '--new-rc', str(nrc), '--roots', json.dumps(roots),
                           '--files', json.dumps(files), '--dest', str(dest)], capture_output=True, text=True,
                          env=dict(os.environ, PYTHONHASHSEED='0'), creationflags=0x4000)
    cli = json.loads(dest.read_text(encoding='utf-8')) if dest.is_file() else {}
    inproc = unit.judge(bt, nt, files, roots, str(broot), str(nroot), brc, nrc)
    res['cli'] = {'rc': done.returncode, 'verdict': cli.get('verdict'), 'same_as_in_process':
                  json.dumps(cli, sort_keys=True) == json.dumps(json.loads(json.dumps(inproc)), sort_keys=True),
                  'stdout': done.stdout.strip()[-300:]}
    res['cases_ok'] = all(v['want'] == v['got'] for v in res['cases'].values())
    res['cli_ok'] = res['cli']['rc'] == 0 and res['cli']['verdict'] == 'PASS' and res['cli']['same_as_in_process']
    # mutants of k92t31_unit.py: each must change the verdict of at least one case
    src = UNIT.read_text(encoding='utf-8')
    mdir = OUTD / 'mutants_unit'
    if mdir.exists():
        shutil.rmtree(mdir)
    mdir.mkdir(parents=True)
    res['mutants'] = {}
    all_cases = dict((n, (logs[n], SCEN[n][2])) for n in SCEN)
    all_cases.update(edit_cases(logs['U1_same']))
    for mname, (old, new_txt) in UNIT_MUTANTS.items():
        n_hits = src.count(old)
        if n_hits != 1:
            res['mutants'][mname] = {'applied': False, 'hits': n_hits, 'caught': False}
            continue
        mp = mdir / ('%s.py' % mname)
        mp.write_text(src.replace(old, new_txt), encoding='utf-8', newline='\n')
        mod = load(mp, 'unit_' + mname)
        flipped = []
        for cname, (args, want) in all_cases.items():
            bt, nt, brc, nrc, broot, nroot, roots = args
            try:
                got = mod.judge(bt, nt, files, roots, str(broot), str(nroot), brc, nrc)['verdict']
            except Exception as exc:  # noqa: BLE001
                got = 'EXC %s' % type(exc).__name__
            if got != want:
                flipped.append([cname, want, got])
        res['mutants'][mname] = {'applied': True, 'caught': bool(flipped), 'cases_changed': flipped}
    res['mutants_ok'] = all(v['caught'] for v in res['mutants'].values())
    res['ok'] = (res['cases_ok'] and res['mutants_ok'] and res['cli_ok'] and res['u1_parse']['base']['ok']
                 and res['u1_parse']['new']['ok'])
    wjson(OUTD / 'dry_a31_unit.json', res)
    print('A31_DRY_UNIT ok=%s cli=%s cases=%s mutants=%s' % (
        res['ok'], res['cli_ok'], {k: (v['want'], v['got']) for k, v in res['cases'].items()},
        {k: v['caught'] for k, v in res['mutants'].items()}))
    return 0 if res['ok'] else 1


# ================================================================================================ drv (synthetic)
DRV = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a31decl/drv')


def rmtree_rw(path):
    """shutil.rmtree that clears the read-only bit first (git object files are read-only on Windows)."""
    import stat

    def onexc(func, p, exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onexc=onexc)


def sgit(repo, *args):
    done = subprocess.run(['git', '-C', str(repo), '-c', 'user.name=a31-synthetic', '-c',
                           'user.email=a31-synthetic@example.invalid', '-c', 'core.autocrlf=false'] + list(args),
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    if done.returncode != 0:
        raise SystemExit('synthetic git %s failed: %s' % (args, done.stderr.strip()[-300:]))
    return done.stdout.strip()


def synth_repo(root, head_variant):
    """A synthetic git repo: commit 'base' (the U1 test files) on branch k8syn, commit 'head' on k92syn (a README
    plus the head_variant test files); the main worktree is left on k92syn, clean."""
    repo = root / 'repo'
    repo.mkdir(parents=True)
    sgit(repo, 'init', '-q', '-b', 'k8syn')
    sgit(repo, 'config', 'core.autocrlf', 'false')
    tests = repo / N31
    tests.mkdir(parents=True)
    for name, src in project(()).items():
        (tests / name).write_text(src, encoding='utf-8', newline='\n')
    sgit(repo, 'add', '-A')
    sgit(repo, 'commit', '-q', '-m', 'base')
    base = sgit(repo, 'rev-parse', 'HEAD')
    sgit(repo, 'checkout', '-q', '-b', 'k92syn')
    for name, src in project(head_variant).items():
        (tests / name).write_text(src, encoding='utf-8', newline='\n')
    (repo / 'README.k92').write_text('synthetic head commit\n', encoding='utf-8', newline='\n')
    sgit(repo, 'add', '-A')
    sgit(repo, 'commit', '-q', '-m', 'head')
    return repo, base, sgit(repo, 'rev-parse', 'HEAD')


def drv_module(root, repo, base, head, tree, jb, cap, log_k92, rc_k92):
    sys.path.insert(0, str(KB / 'impl'))
    drv = load(DRIVER, 'k92t31_drv_%s' % root.name)
    out31 = root / 'out31'
    drv.GWT8, drv.REPO_GITDIR = repo, repo / '.git'
    drv.WT_NAME = 'wt_syn'
    drv.WT, drv.WT_ADMIN = root / 'a31' / 'wt_syn', repo / '.git' / 'worktrees' / 'wt_syn'
    drv.TREE, drv.B9_REF = tree, root / 'b9_ref'
    drv.OUT31, drv.UB = out31, out31 / 'unit_base'
    drv.UNIT_LOG_BASE, drv.UNIT_JUDGE_OUT = out31 / 'unit_base' / 'unit_b9734abe.log', out31 / 'unit_judge.json'
    drv.JB, drv.CAP, drv.UNIT_LOG_K92 = jb, cap, log_k92
    drv.HEAD, drv.K8, drv.BRANCH, drv.K8_BRANCH = head, base, 'k92syn', 'k8syn'
    drv.GIT_DIR_K92 = str(repo / '.git')
    drv.LOG_MD = root / 'LOG.md'
    drv.A31_DOC = root / 'A31_synthetic.md'
    drv.A31_DOC.write_text('synthetic amendment text\n', encoding='utf-8')
    drv.a31_sha = lambda: 'synthetic'
    drv.require_prev = lambda stage: None
    drv.jb_unit_rc = lambda: rc_k92
    return drv


def drv_unit_case(name, head_variant, want):
    root = DRV / name
    if root.exists():
        rmtree_rw(root)
    root.mkdir(parents=True)
    repo, base, head = synth_repo(root, head_variant)
    import k92lib as L
    tree = root / 'tree'
    L.git_archive(head, tree, repo=repo)
    L.git_archive(base, root / 'b9_ref', repo=repo)
    jb, cap = root / 'jb', root / 'jb' / 'sa' / 'cap' / 'k92t'
    cap.mkdir(parents=True)
    (jb / 'tmp').mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(tree), K8G_OUT=str(jb),
               K8_SA_CAPTURE_ROOT=str(cap), K8_SA_BASE_REV='ec063ffa', NUMBA_NUM_THREADS='1',
               GIT_DIR=str(repo / '.git'), TMP=str(jb / 'tmp'), TEMP=str(jb / 'tmp'))
    log_k92 = jb / 'sa' / 'unit_k92t.log'
    log_k92.parent.mkdir(parents=True, exist_ok=True)
    with open(log_k92, 'w', encoding='utf-8', errors='replace') as f:
        rc_k92 = subprocess.run([PY, '-B', str(RUN_PYTEST_BN), '-v'] + [N31 + n for n in UNIT_FILES], cwd=str(tree),
                                env=env, stdout=f, stderr=subprocess.STDOUT, creationflags=0x4000).returncode
    drv = drv_module(root, repo, base, head, tree, jb, cap, log_k92, rc_k92)
    state_before = drv.gwt8_state()
    try:
        drv.stage_unit31()
        exit_code = 0
    except SystemExit as exc:
        exit_code = exc.code
    unit = json.loads((root / 'out31' / 'unit31.json').read_text(encoding='utf-8')) \
        if (root / 'out31' / 'unit31.json').is_file() else {}
    run = json.loads((root / 'out31' / 'unit31_run.json').read_text(encoding='utf-8'))
    wt_list = sgit(repo, 'worktree', 'list', '--porcelain')
    got = {'exit': exit_code, 'verdict': unit.get('verdict'), 'wt_removed': run.get('wt_removed_and_state_same'),
           'wt_dir_absent': not (root / 'a31' / 'wt_syn').exists(),
           'admin_absent': not (repo / '.git' / 'worktrees' / 'wt_syn').exists(),
           'wt_not_listed': 'wt_syn' not in wt_list, 'state_same': drv.gwt8_state() == state_before,
           'wt_head_was_base': run.get('wt_head') == base, 'env_git_dir_is_wt': str(run.get('env', {}).get(
               'GIT_DIR', '')).replace('\\', '/').lower().endswith('/.git/worktrees/wt_syn'),
           'report_wt_vs_b9_ref': {k: v for k, v in (run.get('report_wt_vs_b9_ref') or {}).items()
                                   if k in ('n_changed', 'n_only_wt', 'n_only_b9_ref', 'error')},
           'stop_file': sorted(p.name for p in (root / 'out31').glob('STOP_*.json')), 'k92_rc': rc_k92,
           'base_rc': run.get('base_rc')}
    ok = (got['verdict'] == want and got['wt_removed'] is True and got['wt_dir_absent'] and got['admin_absent']
          and got['wt_not_listed'] and got['state_same'] and got['wt_head_was_base'] and got['env_git_dir_is_wt']
          and ((want == 'PASS' and exit_code == 0 and not got['stop_file'])
               or (want != 'PASS' and exit_code == 3 and got['stop_file'] == ['STOP_a31_unit31.json'])))
    return dict(got, want=want, ok=ok)


def drv_scan_case(name, table, expect_counts, want):
    root = DRV / name
    if root.exists():
        rmtree_rw(root)
    root.mkdir(parents=True)
    sealed = root / 'sealed_s47'
    for rel, rec in table.items():
        p = sealed / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('synthetic log line\n' if rec is None else json.dumps(rec), encoding='utf-8')
    src = NEW_JUDGE.read_text(encoding='utf-8')
    old = "SEALED = OK2 / 'sealed_s47'"
    assert src.count(old) == 1
    judge = root / 'judge_syn.py'
    judge.write_text(src.replace(old, 'SEALED = Path(%r)' % str(sealed)), encoding='utf-8', newline='\n')
    outk = root / 'outk'
    (outk / 'judge').mkdir(parents=True)
    (outk / 'STOP_a30_post.json').write_text('{"synthetic": 1}\n', encoding='utf-8')
    (outk / 'judge' / 'sealed_records.json').write_text('{"synthetic": 2}\n', encoding='utf-8')
    drv = drv_module(root, root, 'x', 'y', root, root, root, root, 1)
    drv.JUDGE31, drv.OUTK = judge, outk
    drv.SCAN_OUT = drv.OUT31 / 'sealed_records_a31.json'
    drv.SCAN_EXPECT = dict(expect_counts, ran=True)
    drv.RECORDED31 = {'STOP_a30_post.json': sha(outk / 'STOP_a30_post.json'),
                      'judge/sealed_records.json': sha(outk / 'judge' / 'sealed_records.json')}
    drv.jf_fixed = lambda: True
    drv.OUT31.mkdir(parents=True)
    try:
        drv.stage_scan31()
        exit_code = 0
    except SystemExit as exc:
        exit_code = exc.code
    rec = json.loads((drv.OUT31 / 'scan31.json').read_text(encoding='utf-8'))
    got = {'exit': exit_code, 'verdict': rec.get('verdict'), 'counts': rec.get('counts'),
           'stop_file': sorted(p.name for p in drv.OUT31.glob('STOP_*.json')),
           'log_md_open_line': 'k92_record.json' in (root / 'LOG.md').read_text(encoding='utf-8')}
    ok = (got['verdict'] == want and got['log_md_open_line']
          and ((want == 'PASS' and exit_code == 0 and not got['stop_file'])
               or (want == 'STOP' and exit_code == 3 and got['stop_file'] == ['STOP_a31_scan31.json'])))
    return dict(got, want=want, ok=ok)


def cmd_drv():
    res = {'schema': 'a31-dry-drv/v1', 'when': time.strftime('%Y-%m-%d %H:%M:%S'),
           'note': 'synthetic git repos and sealed roots under %s; driver constants patched in memory' % DRV}
    want_a = dict(SCAN_EXPECT['A']['new'])
    want_a.pop('ok')
    res['scan_A'] = drv_scan_case('scan_A', SCAN_A, want_a, 'PASS')
    res['scan_A_wrong_count'] = drv_scan_case('scan_A2', SCAN_A, dict(want_a, files=7), 'STOP')
    want_b = dict(SCAN_EXPECT['B']['new'])
    want_b.pop('ok')
    res['scan_B'] = drv_scan_case('scan_B', SCAN_B, want_b, 'STOP')
    res['unit_same'] = drv_unit_case('unit_same', (), 'PASS')
    res['unit_changed'] = drv_unit_case('unit_changed', ('pass_to_fail',), 'FAIL')
    res['ok'] = all(v['ok'] for k, v in res.items() if isinstance(v, dict) and 'ok' in v)
    wjson(OUTD / 'dry_a31_drv.json', res)
    print('A31_DRY_DRV ok=%s %s' % (res['ok'], {k: (v.get('want'), v.get('verdict'), v.get('ok'))
                                               for k, v in res.items() if isinstance(v, dict) and 'ok' in v}))
    return 0 if res['ok'] else 1


# ================================================================================================ drive
def cmd_drive():
    dest = OUTD / 'check31_decl.json'
    logp = OUTD / 'check31_decl.log'
    with open(logp, 'w', encoding='utf-8') as f:
        rc = subprocess.run([PY, '-B', str(DRIVER), 'check31', '--mode', 'decl', '--dest', str(dest)],
                            cwd=str(HERE), stdout=f, stderr=subprocess.STDOUT, creationflags=0x4000,
                            env=dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')).returncode
    rec = json.loads(dest.read_text(encoding='utf-8')) if dest.is_file() else {}
    res = {'schema': 'a31-dry-drive/v1', 'rc': rc, 'check31_ok': rec.get('ok'),
           'false_checks': sorted(k for k, v in (rec.get('checks') or {}).items() if not v),
           'check31_sha256': sha(dest) if dest.is_file() else None, 'when': time.strftime('%Y-%m-%d %H:%M:%S')}
    res['ok'] = rc == 0 and rec.get('ok') is True
    wjson(OUTD / 'dry_a31_drive.json', res)
    print('A31_DRY_DRIVE ok=%s rc=%s false=%s' % (res['ok'], rc, res['false_checks']))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    fn = {'static': cmd_static, 'truth': cmd_truth, 'unit': cmd_unit, 'drv': cmd_drv, 'drive': cmd_drive}.get(cmd)
    if fn is None:
        raise SystemExit(__doc__)
    raise SystemExit(fn())
