"""VerifyGates 3: synthetic self-test of the V1-V4 tools and the driver BEFORE they are pinned (amendment 31 section 4.3:
tests before the pin use synthetic inputs only).  Every input here is made up under VG4/syn; nothing real is read
except the amendment-31 truth-table path strings (pure strings, no file access).

    python -B vg4_synth.py      -> VG4/out/synth.json, exit 0 when every case meets its expectation
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vg4lib as V  # noqa: E402
import vg4_scan as S  # noqa: E402
import vg4_unit as U  # noqa: E402
import vg4_gk4 as G  # noqa: E402
import vg4_keep as K  # noqa: E402
import vg4_run as R  # noqa: E402

PY = r'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
RUN_PYTEST_BN = V.SP / 'k8b_impl' / 'run_pytest_bn.py'
SYN = HERE / 'syn'
RESULTS = []


def case(name, got, want):
    RESULTS.append({'case': name, 'got': got, 'want': want, 'ok': got == want})


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def wjson(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1), encoding='utf-8', newline='\n')


# ------------------------------------------------------------------------------------------------ V2 truth table
def t_truth():
    K_ = r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1'
    root = K_ + '/sealed_s47'
    LP = '\\\\?\\D:\\VISSIM_runs\\20261001_v3c3\\reports\\k8\\k92_b1\\sealed_s47'
    rows = [
        ('T1', K_ + '/sealed_s47', False),
        ('T2', K_ + '/sealed_s47/K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3/k92_record.json', False),
        ('T3', K_ + '/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_1050_s43_SAF_OBS_H3/k92_record.json', False),
        ('T4', K_ + '/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_900_s47_SAF_OBS_H3/k92_record.json', True),
        ('T5', K_ + '/sealed_s47/K9-2-2/probe/sa/cap/k922/TL3/000900_s47/SAF/capture.json', True),
        ('T6', K_ + '/sealed_s47/K9-2-0/s47/x/k92_record.json', True),
        ('T7', K_ + '/sealed_s47/K9-2-0/s47_extra/k92_record.json', True),
        ('T8', K_ + '/sealed_s47/K9-2-0/v3c3-s47/k92_record.json', False),
        ('T9', K_ + '/sealed_s47/K9-2-0/s470/k92_record.json', False),
        ('T10', K_ + '/sealed_s47/K9-2-3/sealed_s47/k92_record.json', True),
        ('T11', K_ + '/sealed_s47/k92t/logs/f_f_off_jobs.log', False),
        ('T12', LP + '\\K9-2-0\\probe\\sa\\jobs\\k92p0\\TL3_1500_SAF_OBS_H3\\k92_record.json', False),
        ('T13', LP + '\\K9-2-1\\probe\\sa\\jobs\\k921\\TL3_900_s47_SAF_OBS_H3\\k92_record.json', True),
        ('T14', 'd:/vissim_runs/20261001_V3C3/REPORTS/k8/K92_B1/SEALED_S47/K9-2-0/x/TL3_1500_SAF_OBS_H3/'
                'k92_record.json', False),
        ('T15', K_ + '/sealed_s47_old/K9-2-0/x.json', True),
        ('T16', K_ + '/sealed_s47x/K9-2-0/x.json', False),
        ('T17', K_ + '/probe/sa/jobs/k92p/TL3_900_s47_SAF_OBS_H3/k92_record.json', True),
        ('T18', K_ + '/probe/sa/jobs/k92p/TL3_1500_SAF_OBS_H3/k92_record.json', False),
        ('T19', K_ + '/commit/K9-2-0/sealed_s47_index.json', True),
        ('T20', 'probe/sa/jobs/TL3_1500_SAF_OBS_H3/k92_record.json', False),
        ('T21', 'x/TL3_900_s47_SAF_OBS_H3/k92_record.json', True),
        ('T22', 'D:\\VISSIM_runs/20261001_v3c3\\reports/k8/k92_b1\\sealed_s47/K9-2-0/x/TL3_1500_SAF_OBS_H3/'
                'k92_record.json', False),
    ]
    for tag, p, want in rows:
        case('truth_' + tag, S.path_is_s47(p, root), want)


# ------------------------------------------------------------------------------------------------ V2 synthetic root
def make_sealed(root, variant):
    if root.exists():
        shutil.rmtree(root)
    recs = [
        ('K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3', {'seed': 31, 'vissim': {'m1': 1.0},
                                                            'vissim_reason': 'k92_vissim_ref'}),
        ('K9-2-1/probe/sa/jobs/k921/TL3_1050_s43_SAF_OBS_H3', {'seed': 43, 'vissim': {'m1': 2.0},
                                                               'vissim_reason': 'k92_vissim_ref'}),
        ('K9-2-1/probe/sa/jobs/k921/TL3_900_s47_SAF_OBS_H3', {'seed': 47, 'vissim': None,
                                                              'vissim_reason': 'k92_blind_s47'}),
        ('K9-2-2/probe/sa/cap/k922/TL3/000900_s47/SAF', {'seed': '47', 'vissim': None,
                                                         'vissim_reason': 'k92_blind_s47'}),
    ]
    if variant == 'bad':
        recs += [
            ('K9-2-2/x/v3c3-run', {'seed': 47, 'vissim': None, 'vissim_reason': 'k92_blind_s47'}),     # disagree
            ('K9-2-3/y/TL3_600_s47_SAF', {'seed': 31, 'vissim': {'m': 1}, 'vissim_reason': 'k92_vissim_ref'}),
            ('K9-2-3/z/s47', {'seed': 47, 'vissim_reason': 'k92_blind_s47'}),                     # vissim key missing
            ('K9-2-3/sealed_s47/w', {'seed': 31, 'vissim': None, 'vissim_reason': 'k92_vissim_ref'}),  # deep root name
        ]
    for rel, doc in recs:
        wjson(root / rel / 'k92_record.json', doc)
    wjson(root / 'K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3/k91_record.json', {'seed': 47, 'vissim': 1})
    if variant == 'bad':
        p = root / 'K9-2-3/q/TL3_300_s47_X/k92_record.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{not json', encoding='utf-8')


def t_scan():
    root = SYN / 'scan' / 'sealed_s47'
    make_sealed(root, 'good')
    r = S.scan(root)
    case('scan_good_counts', [r['files'], r['s47'], r['bad']], [4, 2, 0])
    case('scan_good_seeds', r['seed_values'], {'31': 1, '43': 1, '47': 2})
    case('scan_good_disagree', r['disagree_seed_vs_path'], 0)
    case('scan_good_twoway', r['two_way_piece_mismatch'], 0)
    make_sealed(root, 'bad')
    r = S.scan(root)
    # bad: + disagree (seed 47 no piece) + s47 folder with seed 31 VISSIM (bad) + key missing (bad) + deep sealed_s47
    # folder seed 31 vissim null reason vissim_ref (s47 by path -> bad) + unreadable in s47 folder (bad)
    case('scan_bad_counts', [r['files'], r['s47'], r['bad'], r['unreadable']], [9, 7, 4, 1])
    case('scan_bad_disagree', r['disagree_seed_vs_path'], 3)
    case('scan_bad_keymissing', r['vissim_key_missing_in_s47'], 1)
    shutil.rmtree(SYN / 'scan')


# ------------------------------------------------------------------------------------------------ V3 synthetic logs
T_APPROACH = '''import unittest, os, pytest

class A(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)

    def test_sub(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertEqual(i, i)

    def test_sub_fail(self):
        for i in range(3):
            with self.subTest(i=i, tag='t'):
                self.assertEqual(i, 0, 'root=' + os.getcwd())

    @unittest.skip('why')
    def test_skip(self):
        pass

def test_xfail():
    pytest.xfail('known')

@pytest.fixture
def broken():
    yield 1
    raise RuntimeError('teardown boom 0x7ffde1234 at ' + os.getcwd())

def test_teardown_error(broken):
    assert broken == 1
'''
T_WIRING = '''import unittest

class ConfigFlagTests(unittest.TestCase):
    def test_default_output_is_byte_identical(self):
        a = b'{\\n  "a": 1,\\n  "network": {"x": 1}\\n}\\n' * 20
        b = b'{\\n  "a": 1,\\n  "network": {"x": 2}\\n}\\n' * 20
        self.assertEqual(a, b)

    def test_arms_add_exactly_the_key(self):
        self.assertEqual({'a': 1}, {'a': 1, 'b': 2})

    def test_ok(self):
        self.assertEqual(1, 1)

    def test_label_sub(self):
        with self.subTest('B'):
            self.assertEqual(1, 2)
'''
T_EVIDENCE = '''def test_e1():
    assert 1 == 1
def test_e2():
    assert 2 == 2
'''
T_CAPTURED = '''import json, unittest, pytest
TAG = 'K8_SA_CAPTURE_PROVENANCE'
_T = {'capsys': None}

class Base(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _k8_terminal(self, capsys):
        _T['capsys'] = capsys
        yield
        _T['capsys'] = None

def emit(line):
    c = _T['capsys']
    with c.disabled():
        print('\\n' + line, flush=True)

class Rows(Base):
    def test_row1(self):
        emit(TAG + ' ' + json.dumps({'root': 'x', 'T': 2700}))
        self.assertTrue(True)

    def test_row2(self):
        emit(TAG + ' ' + json.dumps({'root': 'y', 'T': 2700}))
        for i in range(2):
            with self.subTest(i=i):
                self.assertTrue(True)
'''
FILES = R.UNIT_FILES


def make_tree(root, mods=None):
    if root.exists():
        shutil.rmtree(root)
    texts = [T_APPROACH, T_WIRING, T_EVIDENCE, T_CAPTURED]
    for i, (f, t) in enumerate(zip(FILES, texts)):
        for a, b in (mods or {}).get(i, []):
            assert a in t, (i, a)
            t = t.replace(a, b)
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding='utf-8', newline='\n')


def run_pytest(root, log):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    tmp = root.parent / (root.name + '_tmp')
    tmp.mkdir(parents=True, exist_ok=True)
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', TMP=str(tmp), TEMP=str(tmp))
    with open(log, 'wb') as f:
        r = subprocess.run([PY, '-B', str(RUN_PYTEST_BN), '-v'] + FILES, cwd=str(root), env=env, stdout=f,
                           stderr=subprocess.STDOUT, timeout=600)
    return r.returncode


def t_unit():
    base = SYN / 'u' / 'rootA'
    make_tree(base)
    blog = SYN / 'u' / 'base.log'
    brc = run_pytest(base, blog)
    btext = V.read_text(blog)
    variants = {
        'same': ({}, 'PASS'),
        'pass_now_fails': ({2: [('assert 2 == 2', 'assert 2 == 3')]}, 'FAIL'),
        'new_test_pass': ({2: [('def test_e2():', 'def test_e3():\n    assert 1\ndef test_e2():')]}, 'PASS'),
        'new_test_fail': ({2: [('def test_e2():', 'def test_e3():\n    assert 0\ndef test_e2():')]}, 'FAIL'),
        'base_only': ({2: [('def test_e1():\n    assert 1 == 1\n', '')]}, 'FAIL'),
        'other_message': ({1: [("{'a': 1, 'b': 2}", "{'a': 1, 'c': 2}")]}, 'FAIL'),
        'other_label': ({1: [("self.subTest('B')", "self.subTest('C')")]}, 'FAIL'),
    }
    roots_all = [str(base)]
    out = {}
    for name, (mods, want) in variants.items():
        newr = SYN / 'u' / ('root_longer_name_%s' % name)
        make_tree(newr, mods)
        nlog = SYN / 'u' / ('new_%s.log' % name)
        nrc = run_pytest(newr, nlog)
        ntext = V.read_text(nlog)
        res = U.judge(btext, ntext, FILES, roots_all + [str(newr)], str(base), str(newr), brc, nrc)
        case('unit_' + name, res['verdict'], want)
        out[name] = (newr, ntext, nrc, res)
    # parse facts of the 'same' log
    newr, ntext, nrc, res = out['same']
    case('unit_same_rcs', [brc, nrc], [1, 1])
    case('unit_same_counts', [res['n_common'], res['n_differ'], len(res['only_base']), len(res['only_new']),
                              res['n_non_passed_common']], [14, 0, 0, 0, 7])
    np_ids = [t for t, _ in res['non_passed_common']]
    case('unit_same_nonpassed_ids', sorted(x.split('::', 1)[1] for x in np_ids),
         sorted(['A::test_skip', 'A::test_sub_fail', 'test_xfail', 'test_teardown_error',
                 'ConfigFlagTests::test_default_output_is_byte_identical',
                 'ConfigFlagTests::test_arms_add_exactly_the_key', 'ConfigFlagTests::test_label_sub']))
    d = dict(res['non_passed_common'])
    k_sub = FILES[0] + '::A::test_sub_fail'
    case('unit_same_subfail_rows', d.get(k_sub, {}).get('rows'), ['PASSED'])
    case('unit_same_subfail_fails', [x[:2] for x in d.get(k_sub, {}).get('fails', [])],
         [['SUBFAILED', "(i=1, tag='t')"], ['SUBFAILED', "(i=2, tag='t')"]])
    case('unit_same_subfail_msg_root', all('<root>' in x[2] for x in d.get(k_sub, {}).get('fails', [])), True)
    k_td = FILES[0] + '::test_teardown_error'
    case('unit_same_teardown_rows', d.get(k_td, {}).get('rows'), ['PASSED', 'ERROR'])
    case('unit_same_teardown_msg', (d.get(k_td, {}).get('fails') or [[None, None, '']])[0][2],
         'RuntimeError: teardown boom 0x? at <root>')
    case('unit_same_checks_true', all(res['checks']['base'].values()) and all(res['checks']['new'].values()), True)
    case('unit_same_capt_rows', U.results(U.parse(ntext, FILES), [])[FILES[3] + '::Rows::test_row1']['rows'],
         ['PASSED'])
    # edited logs -> INCOMPLETE
    lines = ntext.splitlines()
    fin = [i for i, ln in enumerate(lines) if U.RE_FINAL.match(ln)][-1]
    trunc = '\n'.join(lines[:fin]) + '\n'
    case('unit_truncated', U.judge(btext, trunc, FILES, roots_all + [str(newr)], str(base), str(newr), brc,
                                   nrc)['verdict'], 'INCOMPLETE')
    case('unit_rc_mismatch', U.judge(btext, ntext, FILES, roots_all + [str(newr)], str(base), str(newr), brc,
                                     0)['verdict'], 'INCOMPLETE')
    case('unit_rc_none', U.judge(btext, ntext, FILES, roots_all + [str(newr)], str(base), str(newr), None,
                                 nrc)['verdict'], 'INCOMPLETE')
    case('unit_wrong_root', U.judge(btext, ntext, FILES, roots_all + [str(newr)], str(base), str(base), brc,
                                    nrc)['verdict'], 'INCOMPLETE')
    import re
    plus = re.sub(r'(\d+) passed', lambda m: '%d passed' % (int(m.group(1)) + 1), lines[fin], count=1)
    edited = '\n'.join(lines[:fin] + [plus] + lines[fin + 1:]) + '\n'
    case('unit_count_edit', U.judge(btext, edited, FILES, roots_all + [str(newr)], str(base), str(newr), brc,
                                    nrc)['verdict'], 'INCOMPLETE')
    titles = [i for i, ln in enumerate(lines) if U.RE_TITLE.match(ln) and U.RE_TITLE.match(ln).group(1)
              .replace('_', '').strip()]
    sw = list(lines)
    fstart = [i for i, ln in enumerate(lines) if U.RE_SECTION.match(ln) and 'FAILURES' in ln][0]
    ft = [i for i in titles if i > fstart]
    sw[ft[0]], sw[ft[-1]] = lines[ft[-1]], lines[ft[0]]
    case('unit_swapped_titles', U.judge(btext, '\n'.join(sw) + '\n', FILES, roots_all + [str(newr)], str(base),
                                        str(newr), brc, nrc)['verdict'], 'INCOMPLETE')
    plat = ntext.replace('platform win32', 'platform linux', 1)
    case('unit_platform', U.judge(btext, plat, FILES, roots_all + [str(newr)], str(base), str(newr), brc,
                                  nrc)['verdict'], 'INCOMPLETE')
    lone = ntext.replace(FILES[3] + '::Rows::test_row1 \n', '', 1).replace(FILES[3] + '::Rows::test_row1 \r\n', '', 1)
    case('unit_lone_without_bare', U.judge(btext, lone, FILES, roots_all + [str(newr)], str(base), str(newr), brc,
                                           nrc)['verdict'], 'INCOMPLETE')
    # no root normalisation -> the sub-test messages differ
    case('unit_no_roots', U.judge(btext, ntext, FILES, [], str(base), str(newr), brc, nrc)['verdict'], 'FAIL')
    # compare_record plumbing: a record in the apply format made from my result
    rec = {'verdict': res['verdict'], 'incomplete': [], 'n_base': res['n_base'], 'n_new': res['n_new'],
           'n_common': res['n_common'], 'differ': [], 'n_differ': 0, 'only_base': [], 'only_new': [],
           'new_bad': [], 'non_passed_common_base': copy.deepcopy(res['non_passed_common']),
           'n_non_passed_common': res['n_non_passed_common'], 'rc': {'base': brc, 'new': nrc}}
    rows, _ = U.compare_record(res, rec)
    case('unit_record_same', all(rows.values()), True)
    rec2 = copy.deepcopy(rec)
    rec2['non_passed_common_base'][0][1]['fails'] = [['FAILED', '', 'other']]
    rows, _ = U.compare_record(res, rec2)
    case('unit_record_detail_differs', rows['non_passed_detail_equal'], False)
    return {'base': base, 'btext': btext, 'brc': brc, 'new': out['same']}


# ------------------------------------------------------------------------------------------------ V1 G5 rule
def t_g5():
    roots = [r'D:\X\probe', r'D:/Y/new']
    a = {'ok': True, 'blocks': [{'x': 1.0, 'n': 3, 'wall_sec': 5.0, 'k8b0': {'c': 1}}], 'tuning_sha256': 'aa',
         'job_dir': r'D:\X\probe\jobs\a', 'note': r'D:\X\probe\jobs\a\f.json', 'name': 'TL3', 'flag': None,
         'cap': 'x' * 3}
    b = copy.deepcopy(a)
    b['blocks'][0]['wall_sec'] = 9.0
    b['tuning_sha256'] = 'bb'
    b['job_dir'] = r'D:/Y/new/jobs/b'
    b['note'] = r'D:/Y/new/jobs/b/f.json'
    case('g5_pass_with_exempt', G.compare(a, b, roots)['verdict'], 'PASS')
    c = copy.deepcopy(a)
    c['blocks'][0]['x'] = 1.0 + 1e-13
    case('g5_explain', G.compare(a, c, roots)['verdict'], 'EXPLAIN')
    c = copy.deepcopy(a)
    c['blocks'][0]['x'] = 1.001
    case('g5_fail_num', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['name'] = 'TL4'
    case('g5_fail_str', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['extra'] = 1
    case('g5_fail_onesided', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['extra_time'] = 1
    case('g5_onesided_excluded', G.compare(a, c, roots)['verdict'], 'PASS')
    c = copy.deepcopy(a)
    c['blocks'][0]['k8b0']['c'] = 2
    case('g5_k8b0_compared', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['blocks'][0]['n'] = '3'
    case('g5_kind_clash', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['ok'] = False
    r = G.compare(a, c, roots)
    case('g5_bool_report_only', [r['verdict'], r['other_differ']], ['PASS', 1])
    c = copy.deepcopy(a)
    c['blocks'][0]['x'] = float('nan')
    d = copy.deepcopy(c)
    case('g5_nan_equal', G.compare(c, d, roots)['verdict'], 'PASS')
    c = copy.deepcopy(a)
    c['flag'] = 2.0
    case('g5_null_vs_num', G.compare(a, c, roots)['verdict'], 'FAIL')
    c = copy.deepcopy(a)
    c['share'] = 'p'
    d = copy.deepcopy(a)
    d['share'] = 'q'
    case('g5_share_not_hash', G.compare(c, d, roots)['verdict'], 'FAIL')
    c['hash_x'] = 'p'
    d['hash_x'] = 'q'
    d['share'] = 'p'
    case('g5_hash_key', G.compare(c, d, roots)['verdict'], 'PASS')


# ------------------------------------------------------------------------------------------------ V4 CAP
def make_cap(cap, manifest_path):
    if cap.exists():
        shutil.rmtree(cap)
    for rel, data in (('TL3/002700/SAF/capture.json', b'{"a": 1}'), ('TL3/002700/SAF/template.pickle', b'\x00\x01'),
                      ('T9C/002700/BASE/capture.json', b'{}')):
        p = cap / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    files = {}
    for base, dirs, names in os.walk(cap):
        for n in names:
            full = os.path.join(base, n)
            rel = os.path.relpath(full, cap).replace('\\', '/')
            files[rel] = [os.path.getsize(full), V.sha256_file(full)]
    listing = '\n'.join('%s\t%d\t%s' % (k, v[0], v[1]) for k, v in sorted(files.items())) + '\n'
    man = {'schema': 'rv31-cap-manifest/v1', 'n_files': len(files), 'n_bytes': sum(v[0] for v in files.values()),
           'listing_sha256': sha_bytes(listing.encode()), 'files': files}
    wjson(manifest_path, man)
    return man


def t_cap():
    cap = SYN / 'cap' / 'k92t'
    man = make_cap(cap, SYN / 'cap' / 'cap_manifest.json')
    saved = (V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256)
    V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256 = man['n_files'], man['n_bytes'], man['listing_sha256']
    try:
        P = dict(V.P, CAP=cap)
        case('cap_same', K.check_cap(P, man)['ok'], True)
        (cap / 'TL3/002700/SAF/capture.json').write_bytes(b'{"a": 2}')
        r = K.check_cap(P, man)
        case('cap_byte_change', [r['ok'], r['n_sha_differ']], [False, 1])
        make_cap(cap, SYN / 'cap' / 'cap_manifest.json')
        (cap / 'extra.txt').write_bytes(b'x')
        r = K.check_cap(P, man)
        case('cap_extra_file', [r['ok'], r['n_only_now']], [False, 1])
    finally:
        V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256 = saved
    shutil.rmtree(SYN / 'cap')


# ------------------------------------------------------------------------------------------------ driver end to end
def build_layout(top, unit):
    """A whole fake layout: P dict + expected constants, records shaped like the apply records."""
    if top.exists():
        shutil.rmtree(top)
    ok2 = top / 'ok2'
    tk = top / 'tk'
    P = dict(V.P)
    P.update({'KB': top / 'kb', 'LOG': top / 'kb' / 'LOG.md', 'A31': top / 'sp' / 'A31.md',
              'A31_SHA': top / 'sp' / 'A31.md.sha256', 'FIXED31': top / 'kb' / 'FIXED31.md',
              'A31_PINS': top / 'kb' / 'a31_pins.sha256', 'OK2': ok2, 'OUTK': ok2 / 'k92t', 'OUT30': ok2 / 'a30',
              'OUT31': ok2 / 'a31', 'SEALED': ok2 / 'sealed_s47', 'OK2A': ok2 / 'probe_a25',
              'RJG4': ok2 / 'a27' / 'judge' / 'rjg4.json', 'CAP': ok2 / 'k92t' / 'jb' / 'sa' / 'cap' / 'k92t',
              'CAP_MANIFEST': top / 'kb' / 'cap_manifest.json', 'JB': ok2 / 'k92t' / 'jb',
              'UNIT_LOG_NEW': ok2 / 'k92t' / 'jb' / 'sa' / 'unit_k92t.log', 'UB': ok2 / 'a31' / 'unit_base',
              'UNIT_LOG_BASE': ok2 / 'a31' / 'unit_base' / 'unit_b9734abe.log', 'TK': tk, 'TKA': tk / 'a25',
              'TREE': unit['new'][0], 'WT': unit['base'], 'WT_ADMIN': top / 'repo' / 'worktrees' / 'wt',
              'GIT_DIR_K92': top / 'repo' / 'worktrees' / 'gwt8', 'GWT8': top / 'gwt8', 'OUT': top / 'out'})
    for k in ('KB', 'OUT'):
        Path(P[k]).mkdir(parents=True, exist_ok=True)
    # amendment, fixation
    Path(P['A31']).parent.mkdir(parents=True, exist_ok=True)
    Path(P['A31']).write_text('amendment 31 synthetic\n', encoding='utf-8', newline='\n')
    a31 = V.sha256_file(P['A31'])
    Path(P['A31_SHA']).write_text(a31 + ' *A31.md\n', encoding='utf-8', newline='\n')
    Path(P['FIXED31']).write_text('fixed: %s\n' % a31, encoding='utf-8', newline='\n')
    # OUTK
    outk = Path(P['OUTK'])
    for n in K.STOPS:
        wjson(outk / n, {'stop': n})
    for n in K.STAGES:
        wjson(outk / 'stages' / n, {'ok': True})
    for n in K.JUDGES:
        wjson(outk / 'judge' / n, {'judge': n})
    steps = [json.dumps({'name': 'step%d' % i, 'rc': 0}) for i in range(101)]
    steps.insert(78, json.dumps({'name': 'jb_unit', 'rc': unit['new'][2]}))
    (outk / 'steps.jsonl').write_text('\n'.join(steps) + '\n', encoding='utf-8', newline='\n')
    Path(P['UNIT_LOG_NEW']).parent.mkdir(parents=True, exist_ok=True)
    Path(P['UNIT_LOG_NEW']).write_text(unit['new'][1], encoding='utf-8', newline='\n')
    more = ['k92_judging_stage.json', 'start/scans.json', 'jb_copies.json', 'driver.log',
            'f_vref/sa/k92_vissim_ref.json', 'f_persist30/sa/k92_vissim_ref.json', 'jb/sa/gates/gates_k92t.json',
            'jb/sa/unit_k92t.meta.txt']
    for n in more:
        wjson(outk / n, {'f': n})
    outk_files = sorted(str(p) for p in outk.rglob('*') if p.is_file())
    # OUT30 + chain
    for n in ('check30.json', 'sealed_k92t_index.json'):
        wjson(Path(P['OUT30']) / n, {'f': n})
    wjson(ok2 / 'logs' / 'k92t30_chain.txt', {'f': 'chain'})
    extra = [str(Path(P['OUT30']) / 'check30.json'), str(Path(P['OUT30']) / 'sealed_k92t_index.json'),
             str(ok2 / 'logs' / 'k92t30_chain.txt')]
    # sealed root: six tops, logs with sizes, records
    sealed = Path(P['SEALED'])
    for t in K.SEALED_TOPS:
        (sealed / t).mkdir(parents=True, exist_ok=True)
    for n, size in K.SEALED_K92T_LOGS.items():
        p = sealed / 'k92t' / 'logs' / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'x' * size)
    recs = []
    for i in range(3):
        recs.append(('K9-2-0/probe/sa/jobs/k92p0/TL3_%d_SAF_OBS_H3' % (1500 + i), 31))
        recs.append(('K9-2-1/probe/sa/jobs/k921/TL3_%d_s43_SAF_OBS_H3' % (1050 + i), 43))
        recs.append(('K9-2-2/probe/sa/jobs/k922/TL3_%d_s47_SAF_OBS_H3' % (900 + i), 47))
    for rel, seed in recs:
        doc = ({'seed': seed, 'vissim': None, 'vissim_reason': 'k92_blind_s47'} if seed == 47 else
               {'seed': seed, 'vissim': {'m1': 1.0}, 'vissim_reason': 'k92_vissim_ref'})
        wjson(sealed / rel / 'k92_record.json', doc)
    # G-K4 rows
    rows_rec = {}
    for commit, arm, lab in G.ROWS:
        for job in G.JOBS:
            old = Path(P['OK2A']) / 'plant' / 'sa' / 'jobs' / ('k92p' + arm) / job
            new = sealed / commit / 'plant' / 'new' / 'sa' / 'jobs' / (lab + 'g4' + arm) / job
            for side, root in ((old, Path(P['OK2A']) / 'plant'), (new, sealed / commit / 'plant' / 'new')):
                wjson(side / 'summary.json', {'ok': True, 'blocks': [{'x': 1.5, 'wall_sec': os.urandom(1)[0]}],
                                              'out': str(side), 'template_sha256': sha_bytes(str(side).encode())})
                wjson(side / 'k92_record.json', {'seed': 31 if '1500' in job else 43, 'model': {'m1': 2.0},
                                                 'vissim': None, 'vissim_reason': 'k92_vissim_ref'})
            rows_rec['plant_%s_%s' % (commit, job)] = {
                'verdict': 'PASS', 'status': 'PASS',
                'parts': {'summary.json': {'verdict': 'PASS'}, 'k92_record.json': {'verdict': 'PASS'}}}
    for k in range(8):
        rows_rec['dec_%d' % k] = {'verdict': 'PASS'}
    wjson(P['RJG4'], {'rows': rows_rec, 'n': 12, 'verdicts': ['PASS'] * 12, 'verdict': 'PASS'})
    # CAP + manifest
    man = make_cap(Path(P['CAP']), Path(P['CAP_MANIFEST']))
    # OUT31 records
    out31 = Path(P['OUT31'])
    sr = {'ok': True, 'bad': [], 'n_bad': 0, 'notes': {}, 'sealed_records': {'files': 13, 's47': 3, 'bad': 0,
                                                                              'ran': True}}
    wjson(out31 / 'sealed_records_a31.json', sr)
    wjson(out31 / 'scan31.json', {'verdict': 'PASS', 'rc': 0, 'ok': True, 'n_bad': 0,
                                  'counts': {'files': 13, 's47': 3, 'bad': 0, 'ran': True},
                                  'expected_counts': {'files': 13, 's47': 3, 'bad': 0, 'ran': True},
                                  'archive_unchanged': True,
                                  'output_sha256': V.sha256_file(out31 / 'sealed_records_a31.json')})
    Path(P['UB']).mkdir(parents=True, exist_ok=True)
    Path(P['UNIT_LOG_BASE']).write_text(unit['btext'], encoding='utf-8', newline='\n')
    (Path(P['UB']) / 'unit_b9734abe.meta.txt').write_text('ROOT x\nrc=%d\n' % unit['brc'], encoding='utf-8')
    (out31 / 'steps31.jsonl').write_text(json.dumps({'name': 'unit31_pytest', 'rc': unit['brc']}) + '\n',
                                         encoding='utf-8', newline='\n')
    wjson(out31 / 'unit31_run.json', {'base_rc': unit['brc'], 'selection': R.UNIT_FILES, 'wt_head': V.K8,
                                      'wt_git_dir': str(P['WT_ADMIN']), 'wt_removed_and_state_same': True})
    res = unit['new'][3]
    wjson(out31 / 'unit_judge.json', {
        'verdict': res['verdict'], 'incomplete': [], 'n_base': res['n_base'], 'n_new': res['n_new'],
        'n_common': res['n_common'], 'differ': [], 'n_differ': 0, 'only_base': [], 'only_new': [], 'new_bad': [],
        'non_passed_common_base': res['non_passed_common'], 'n_non_passed_common': res['n_non_passed_common'],
        'rc': {'base': unit['brc'], 'new': unit['new'][2]}})
    for n in ('check31.json', 'unit31.json', 'chain31.json'):
        wjson(out31 / n, {'f': n})
    prefixes = {rel: V.sha256_file(out31 / rel)[:8] for rel in R.OUT31_PREFIX}
    # pins file: the OUTK files + the three others + one unrelated
    unrelated = top / 'kb' / 'other.txt'
    unrelated.write_text('x', encoding='utf-8')
    lines = ['%s *%s' % (V.sha256_file(p), str(p).replace('\\', '/')) for p in outk_files + extra + [str(unrelated)]]
    Path(P['A31_PINS']).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    E = R.expected()
    E.update({'a31': a31, 'fixed31': V.sha256_file(P['FIXED31']), 'pins': V.sha256_file(P['A31_PINS']),
              'rjg4': V.sha256_file(P['RJG4']), 'cap_manifest': V.sha256_file(P['CAP_MANIFEST']),
              'out31_prefix': prefixes, 'scope_n': len(outk_files) + 3, 'scope_outk_n': len(outk_files)})
    return P, E, man


def t_driver(unit):
    top = SYN / 'drv'
    P, E, man = build_layout(top, unit)
    saved = dict(P=V.P, JF=V.JF_SHA256, CAP=(V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256),
                 EXP=S.EXPECT, SEEDS=S.EXPECT_SEEDS)
    try:
        V.P = P
        V.JF_SHA256 = {rel: V.sha256_file(Path(P['OUTK']) / rel) for rel in ('judge/f.json', 'judge/jb.json')}
        V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256 = man['n_files'], man['n_bytes'], man['listing_sha256']
        S.EXPECT = {'files': 13, 's47': 3, 'bad': 0}           # 9 probe-like records + 4 G-K4 new-side records
        S.EXPECT_SEEDS = {'31': 5, '43': 5, '47': 3}
        tools = [HERE / n for n in ('vg4lib.py', 'vg4_scan.py', 'vg4_unit.py', 'vg4_gk4.py', 'vg4_keep.py',
                                    'vg4_run.py', 'vg4launch.ps1')]
        git_ok = (lambda _P: {'ok': True, 'stub': True})
        snap_ok = (lambda name, _P: {'same_as_s02': True, 'stub': name})
        opts = {'git': git_ok, 'snap': snap_ok, 'log_result': True}
        # 1) tools not in the synthetic LOG -> guard stop, no data read
        Path(P['LOG']).write_text('# synthetic log\n', encoding='utf-8', newline='\n')
        case('drv_guard_tools', R.run(P, E, dict(opts, result_name='g1.json'), tools), 4)
        # 2) LOG with the tools and the J / F sha -> PASS
        txt = '# synthetic log\n' + '\n'.join(V.sha256_file(t) for t in tools) + '\n' + '\n'.join(
            V.JF_SHA256.values()) + '\n'
        Path(P['LOG']).write_text(txt, encoding='utf-8', newline='\n')
        rc = R.run(P, E, dict(opts, result_name='pass.json'), tools)
        doc = V.read_json(Path(P['OUT']) / 'pass.json')
        case('drv_pass', [rc, doc['verdict'], doc['oks']], [0, 'PASS', {
            'V4': True, 'V2': True, 'V3': True, 'V1': True, 'out31_unchanged': True, 'snap_before_same': True,
            'snap_after_same': True}])
        case('drv_log_lines', sum(1 for ln in Path(P['LOG']).read_text(encoding='utf-8').splitlines()
                                  if '열람 기록' in ln), 4)
        # 3) a recorded G-K4 plant verdict changed -> V1 false -> STOP
        rj = V.read_json(P['RJG4'])
        rj['rows']['plant_K9-2-1_TL3_1500_SAF_OBS_H3']['parts']['summary.json']['verdict'] = 'EXPLAIN'
        wjson(P['RJG4'], rj)
        E2 = dict(E, rjg4=V.sha256_file(P['RJG4']))
        rc = R.run(P, E2, dict(opts, result_name='v1bad.json'), tools)
        doc = V.read_json(Path(P['OUT']) / 'v1bad.json')
        case('drv_v1_bad', [rc, doc['verdict'], doc['oks']['V1'], doc['oks']['V2']], [3, 'STOP', False, True])
        # 4) a new-side numeric leaf changed -> my row FAIL -> V1 false
        p = Path(P['SEALED']) / 'K9-2-2/plant/new/sa/jobs/k922g4B1/TL3_1050_s43_SAF_OBS_H3/k92_record.json'
        d = V.read_json(p)
        d['model']['m1'] = 2.5
        wjson(p, d)
        rc = R.run(P, E, dict(opts, result_name='v1num.json'), tools)
        doc = V.read_json(Path(P['OUT']) / 'v1num.json')
        case('drv_v1_numeric', [rc, doc['V1']['rows']['plant_K9-2-2_TL3_1050_s43_SAF_OBS_H3']['verdict']],
             [3, 'FAIL'])
        # 5) a CAP byte changed -> V4 false
        cf = sorted(Path(P['CAP']).rglob('*.json'))[0]
        cf.write_bytes(cf.read_bytes() + b' ')
        rc = R.run(P, E, dict(opts, result_name='v4bad.json'), tools)
        doc = V.read_json(Path(P['OUT']) / 'v4bad.json')
        case('drv_v4_cap', [rc, doc['oks']['V4'], doc['V4']['cap']['n_sha_differ']], [3, False, 1])
        # 6) an s47 sealed record made non-blind -> V2 false
        q = Path(P['SEALED']) / 'K9-2-2/probe/sa/jobs/k922/TL3_900_s47_SAF_OBS_H3/k92_record.json'
        wjson(q, {'seed': 47, 'vissim': {'m1': 1}, 'vissim_reason': 'k92_vissim_ref'})
        rc = R.run(P, E, dict(opts, result_name='v2bad.json'), tools)
        doc = V.read_json(Path(P['OUT']) / 'v2bad.json')
        case('drv_v2_bad', [rc, doc['oks']['V2'], doc['V2']['counts']], [3, False, {'files': 13, 's47': 3, 'bad': 1}])
    finally:
        V.P, V.JF_SHA256 = saved['P'], saved['JF']
        V.CAP_N_FILES, V.CAP_N_BYTES, V.CAP_LISTING_SHA256 = saved['CAP']
        S.EXPECT, S.EXPECT_SEEDS = saved['EXP'], saved['SEEDS']


def main():
    SYN.mkdir(parents=True, exist_ok=True)
    t_truth()
    t_scan()
    t_g5()
    t_cap()
    unit = t_unit()
    t_driver(unit)
    bad = [r for r in RESULTS if not r['ok']]
    out = {'n': len(RESULTS), 'n_ok': len(RESULTS) - len(bad), 'bad': bad, 'cases': [r['case'] for r in RESULTS]}
    V.write_json(HERE / 'out' / 'synth.json', out)
    print('VG4_SYNTH %d/%d' % (out['n_ok'], out['n']))
    for r in bad:
        print('BAD', r['case'], json.dumps(r['got'])[:300], json.dumps(r['want'])[:300])
    return 0 if not bad else 1


if __name__ == '__main__':
    raise SystemExit(main())
